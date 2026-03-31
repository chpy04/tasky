# Async Runs

## Problem

Every operation that calls connectors or the LLM runs synchronously on the FastAPI request thread. A full sync can take 30–90 seconds; the HTTP connection stays open the entire time, the browser spinner blocks the UI, and any network hiccup kills the request. The fix is to dispatch these jobs to a background thread immediately, return a run ID, and let the frontend poll for status.

Operations to make async:
- `POST /ingestion/sync` — full pipeline (connectors + LLM)
- `POST /ingestion/runs` — connector-only run
- `POST /ingestion/runs/{id}/rerun` — re-run connectors
- `POST /ingestion/runs/{id}/propose` — LLM proposal generation for an existing run

## Acceptance Criteria

- [ ] `POST /ingestion/sync` returns `{"run_id": N, "status": "running"}` immediately (< 200 ms)
- [ ] `POST /ingestion/runs` returns the new run record with `status: "running"` immediately
- [ ] `POST /ingestion/runs/{id}/rerun` returns the run with `status: "running"` immediately
- [ ] `POST /ingestion/runs/{id}/propose` returns `{"run_id": N, "status": "running"}` immediately
- [ ] `GET /ingestion/runs/{id}` reflects live status (`running` → `completed`/`failed`) as the job progresses
- [ ] A second `POST /ingestion/sync` while one is already running returns HTTP 409
- [ ] A second `POST /ingestion/runs/{id}/propose` while one is proposing for the same run returns HTTP 409
- [ ] Topbar "Sync" button stays in a loading/spinning state while the run is `running`, then shows the proposal count on completion
- [ ] Topbar "Sync" button shows an error state if the run ends with `failed`
- [ ] No HTTP request times out due to a long-running connector or LLM call

## Out of Scope

- SSE / WebSockets (polling is sufficient)
- Per-connector granular progress (batch-level status ticks)
- Persistent task queue (Celery, RQ, etc.) — in-process `asyncio.to_thread` is sufficient
- Retry logic for failed connector calls

## Design Decisions

**In-process background tasks via `asyncio.to_thread`**
The app already uses `asyncio.to_thread` for the scheduler loop. We follow the same pattern: the endpoint creates (or resets) the `IngestionRun` record synchronously, sets `status=running`, commits, then calls `asyncio.create_task(asyncio.to_thread(...))` and returns the partial run. No external worker needed.

**Concurrency guard via in-memory set + DB check**
A module-level `set[int]` in `app/jobs/run_tracker.py` tracks in-flight run IDs. For the full-pipeline 409, we also check the DB for any `status=running` run (handles server restarts). The set is the fast path; the DB query is the safety net.

**`propose` tracks in-flight per-run-ID**
A separate module-level `set[int]` in the same tracker tracks which run IDs have an LLM call in flight. `POST /runs/{id}/propose` rejects with 409 if that run ID is already in the set.

**`IngestionRun.status` is the polling primitive**
The frontend polls `GET /ingestion/runs/{id}` every 2–3 s. The run transitions: `running` → `completed` | `failed`. No new columns needed.

**Background task error handling**
If the background function raises, it catches the exception, sets `run.status = RunStatus.failed` and `run.error_summary`, commits, then re-raises into the log. The frontend sees `failed` on next poll.

**Stale `running` runs on startup**
When the FastAPI app starts, any `IngestionRun` still stuck in `running` from a prior crash is reset to `failed` with `error_summary = "server restarted while run was in progress"`. This prevents the concurrency guard from permanently blocking after a crash.

## Implementation Tasks

- [x] **Task 1:** Add `run_tracker.py` — in-memory concurrency guard (independent)
  - **Read:** `backend/app/main.py` (lifespan pattern)
  - **Modify:** create `backend/app/jobs/run_tracker.py`
  - **What:** A small module with two module-level sets and their guard helpers:
    ```python
    # backend/app/jobs/run_tracker.py
    _active_runs: set[int] = set()      # full pipeline / connector runs in flight
    _active_proposes: set[int] = set()  # per-run LLM propose calls in flight

    def claim_run(run_id: int) -> bool:
        """Returns True if successfully claimed (not already active)."""
        ...

    def release_run(run_id: int) -> None: ...

    def claim_propose(run_id: int) -> bool: ...
    def release_propose(run_id: int) -> None: ...
    ```
    Thread-safe because CPython GIL protects `set.add` / `set.discard`; no lock needed for this use case.
  - **Verify:** Import the module from a Python shell; call claim/release and assert the set state.

- [x] **Task 2:** Mark stale runs as failed on startup (independent)
  - **Read:** `backend/app/main.py` (lifespan), `backend/app/models/ingestion_run.py`
  - **Modify:** `backend/app/main.py`
  - **What:** Inside the `lifespan` async context manager, before `yield`, add a startup hook that opens a DB session and updates any `IngestionRun` with `status=running` to `status=failed, error_summary="server restarted while run was in progress"`. This prevents the concurrency guard from being stuck after a server crash.
    ```python
    async def _reset_stale_runs() -> None:
        from app.db.session import SessionLocal
        from app.models.ingestion_run import IngestionRun, RunStatus
        db = SessionLocal()
        try:
            stale = db.query(IngestionRun).filter(IngestionRun.status == RunStatus.running).all()
            for run in stale:
                run.status = RunStatus.failed
                run.error_summary = "server restarted while run was in progress"
            if stale:
                db.commit()
                logger.warning("Reset %d stale running runs to failed", len(stale))
        finally:
            db.close()
    ```
    Call `await _reset_stale_runs()` at the top of the lifespan block (before starting the scheduler task).
  - **Verify:** Manually set a run to `running` in the DB, restart the server, confirm the run is now `failed`.

- [x] **Task 3:** Make `run_full_pipeline` background-safe (depends on Task 1)
  - **Read:** `backend/app/jobs/ingestion_job.py`, `backend/app/jobs/run_tracker.py`
  - **Modify:** `backend/app/jobs/ingestion_job.py`
  - **What:** Extract the body of `run_full_pipeline` into `_run_full_pipeline_inner(run_id, db)` that is called in the background. The new `run_full_pipeline` should only be used by the scheduler (it still runs synchronously in a thread pool). Create a new `run_full_pipeline_async(db, triggered_by)` function that:
    1. Checks the DB for any `status=running` run — returns `None` if one exists (caller raises 409).
    2. Creates the `IngestionRun` record with `status=running`, commits.
    3. Claims the run via `run_tracker.claim_run(run.id)`.
    4. Returns the run object immediately (the route handler will dispatch the rest).

    Create `_run_full_pipeline_bg(run_id: int)` — a standalone function (no DB session argument, opens its own session via `SessionLocal`) that:
    1. Runs the connector phase via `IngestionService._run_connectors`.
    2. Runs the LLM proposal phase.
    3. On completion or error: sets run status, commits, calls `run_tracker.release_run(run_id)`.
  - **Context:** The background function must open its own `SessionLocal` session because the session from the HTTP request is closed when the response is sent. The `asyncio.to_thread` call in the endpoint receives no session argument.
  - **Verify:** Confirm the function signature compiles; the scheduler path still calls the old synchronous `run_full_pipeline` (no change there).

- [x] **Task 4:** Make `propose` background-safe (depends on Task 1)
  - **Read:** `backend/app/api/ingestion.py` (the `propose_tasks` endpoint), `backend/app/jobs/run_tracker.py`
  - **Modify:** create `backend/app/jobs/propose_job.py`
  - **What:** Extract the LLM proposal logic from the `propose_tasks` endpoint into `run_propose_bg(run_id: int)` — a standalone function that opens its own `SessionLocal`, does the LLM call, saves proposals, updates run status if needed, and calls `run_tracker.release_propose(run_id)` in a `finally` block.
  - **Verify:** Confirm the function is importable; no circular imports.

- [x] **Task 5:** Update API endpoints to be non-blocking (depends on Tasks 1, 3, 4)
  - **Read:** `backend/app/api/ingestion.py`
  - **Modify:** `backend/app/api/ingestion.py`
  - **What:** Four endpoints change:

    **`POST /ingestion/sync`**
    ```python
    @router.post("/sync")
    async def sync(request: Request, db: Session = Depends(get_db)):
        from app.jobs.ingestion_job import run_full_pipeline_async
        from app.models.ingestion_run import TriggeredBy, RunStatus
        # 409 guard: check DB for running run
        existing = db.query(IngestionRun).filter(
            IngestionRun.status == RunStatus.running
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="A run is already in progress")
        run = run_full_pipeline_async(db, triggered_by=TriggeredBy.manual)
        asyncio.create_task(asyncio.to_thread(_run_full_pipeline_bg, run.id))
        return {"run_id": run.id, "status": "running"}
    ```
    The endpoint must be `async def` to call `asyncio.create_task`.

    **`POST /ingestion/runs`**
    Change `create_run` to `async def`. After `svc.trigger_run_async(...)` creates the run record and returns (without running connectors), dispatch `asyncio.create_task(asyncio.to_thread(_run_full_pipeline_bg, run.id))` and return `_run_to_summary(run)` immediately.

    **`POST /ingestion/runs/{id}/rerun`**
    Change `rerun` to `async def`. After the run record is reset to `status=running`, dispatch the background task.

    **`POST /ingestion/runs/{id}/propose`**
    ```python
    @router.post("/runs/{run_id}/propose")
    async def propose_tasks(run_id: int, db: Session = Depends(get_db)):
        from app.jobs.run_tracker import claim_propose
        from app.jobs.propose_job import run_propose_bg
        ...
        if not claim_propose(run_id):
            raise HTTPException(status_code=409, detail="Proposal already in progress for this run")
        asyncio.create_task(asyncio.to_thread(run_propose_bg, run_id))
        return {"run_id": run_id, "status": "running"}
    ```

  - **Context:** `asyncio.create_task` only works inside an async context. All four endpoints must be `async def`. The `asyncio` module must be imported at the top of `ingestion.py`.
  - **Verify:** `POST /sync` responds in under 500 ms. `GET /runs/{id}` shows `running`, then updates to `completed` within the expected time.

- [x] **Task 6:** Split `IngestionService.trigger_run` into two steps (depends on Task 5)
  - **Read:** `backend/app/services/ingestion_service.py`
  - **Modify:** `backend/app/services/ingestion_service.py`
  - **What:** Add `create_run(range_start, range_end, triggered_by)` that only creates the `IngestionRun` record with `status=running` and flushes (no connectors). Rename existing `trigger_run` to keep it working for the scheduler's synchronous path (it calls `create_run` then `_run_connectors`). This clean split means Task 3's async path calls `create_run`, gets the `run.id`, then dispatches the background job.
  - **Verify:** Unit-test that `create_run` returns a run with `status=running` and no batches.

- [x] **Task 7:** Frontend — update `useSyncPipeline` to poll (depends on Task 5)
  - **Read:** `frontend/src/api/useIngestion.ts`
  - **Modify:** `frontend/src/api/useIngestion.ts`
  - **What:** `useSyncPipeline` currently fires-and-forgets one mutation. Change it so:
    1. The mutation calls `POST /sync`, receives `{run_id, status: "running"}`, stores `run_id` in component state (returned via `mutationFn` return value).
    2. A polling query `useQuery` with `refetchInterval: 2500` fetches `GET /ingestion/runs/{run_id}` while `run_id !== null && run.status === "running"`.
    3. Once status is `completed` or `failed`, stop polling, invalidate `["ingestion-runs"]` and `["proposals"]`.

    Export a new `useSyncPipelineWithPolling()` hook that encapsulates this: returns `{ trigger, isRunning, run, error }`.

    Update `SyncResult` type:
    ```typescript
    export interface SyncResult {
      run_id: number;
      status: "running";
    }
    ```
  - **Verify:** Trigger sync in dev; network tab shows `POST /sync` complete in < 1 s, then `GET /runs/{id}` requests every 2.5 s until status changes.

- [x] **Task 8:** Frontend — update `useCreateIngestionRun` and `useRerunIngestionRun` to poll (depends on Task 5)
  - **Read:** `frontend/src/api/useIngestion.ts`
  - **Modify:** `frontend/src/api/useIngestion.ts`
  - **What:** Both mutations now return `IngestionRunSummary` with `status: "running"`. The existing optimistic-update in `useCreateIngestionRun` should keep working since the placeholder already uses `status: "running"`. After `onSuccess`, start polling `GET /ingestion/runs/{id}` at 2.5 s intervals until the run is no longer `running`. On completion invalidate `["ingestion-runs"]`.

    Add a helper `useRunStatusPoller(runId: number | null)` inside `useIngestion.ts` that:
    ```typescript
    useQuery({
      queryKey: ["ingestion-run", runId],
      queryFn: () => fetchRun(runId!),
      enabled: runId !== null,
      refetchInterval: (data) =>
        data?.status === "running" ? 2500 : false,
    })
    ```
    Both `useCreateIngestionRun` and `useRerunIngestionRun` can use this hook internally via a shared `activeRunId` ref.
  - **Verify:** Create a run in the Ingestion page; the row shows "running" badge, then flips to "completed"/"failed" without a manual refresh.

- [x] **Task 9:** Frontend — update Topbar to handle async sync (depends on Task 7)
  - **Read:** `frontend/src/components/layout/Topbar.tsx`
  - **Modify:** `frontend/src/components/layout/Topbar.tsx`
  - **What:** Replace `useSyncPipeline` with `useSyncPipelineWithPolling`. Update `handleSync`:
    - Show spinner while `isRunning === true`
    - On completion: show `+N proposals` message from `run.proposal_count`
    - On failure: show "sync failed" message
    - The sync button remains disabled while `isRunning`
  - **Verify:** Click sync in the topbar; spinner persists until the run completes, then shows the proposal count.

- [x] **Task 10:** Frontend — update `useProposeTasksForRun` for async response (depends on Task 5)
  - **Read:** `frontend/src/api/useIngestion.ts`, `frontend/src/pages/Ingestion.tsx` (RunProposalsTab)
  - **Modify:** `frontend/src/api/useIngestion.ts`
  - **What:** The `propose` endpoint now returns `{run_id, status: "running"}`. The mutation can no longer immediately display `proposals_saved`. Instead, after receiving the async response, poll `GET /ingestion/runs/{run_id}/proposals` (the existing `useRunProposals` hook) at 2.5 s until new proposals appear or the run is `completed`. The `RunProposalsTab` already uses `useRunProposals`; ensure it auto-refreshes by setting `refetchInterval` on that query while the propose mutation is in-flight.

    Update `ProposeResult`:
    ```typescript
    export interface ProposeResult {
      run_id: number;
      status: "running";
    }
    ```
  - **Verify:** Click "propose tasks" on a run; the proposals tab shows "running LLM…" then populates proposals without a manual refresh.
