# Async Runs — Improvement Plan

## Review Summary

The branch successfully converts synchronous ingestion/LLM operations to async background jobs. The core architecture is sound: `asyncio.to_thread` for background dispatch, in-memory concurrency guards, separate DB sessions for background threads, stale-run cleanup on startup, and TanStack Query polling on the frontend. The Sync button flow works end-to-end — it disables, shows "Syncing...", polls every 2.5s, and re-enables on completion with the proposal count updating.

However, user testing revealed several bugs and UX issues, primarily around the "propose tasks" flow and cache invalidation.

---

## Bugs

### Bug 1: "Propose tasks" has no loading indicator during LLM work

**Severity:** High — user has no idea the LLM is running

**What happens:** Clicking "propose tasks" immediately deletes existing proposals (via `propose_job.py` line 50-55), then shows "no proposals yet — click propose tasks to generate" with no spinner. The mutation's `isPending` is only `true` during the brief POST request (~100ms), not during the 15-30s LLM call.

**Root cause:** `useProposeTasksForRun()` computes `isProposing` internally but does NOT expose it. The hook only returns the standard `useMutation` return value. `Ingestion.tsx` passes `isPending={proposeTasks.isPending}` to `RunProposalsTab`, which is the mutation pending state, not the background job state.

**Fix:**
- `useProposeTasksForRun()` should return `isProposing` (derived from the polled run status) alongside the mutation return value. Either return a combined object `{ mutation, isProposing }` or attach `isProposing` to the return.
- `RunProposalsTab` should use `isProposing` instead of `proposeTasks.isPending`.
- Show a "generating proposals..." message with spinner while `isProposing` is true.

### Bug 2: Run header proposal count is stale after propose completes

**Severity:** Medium — confusing but not blocking

**What happens:** After re-proposing on a run that had 4 proposals, the LLM generates 3 new proposals. The proposals tab shows 3, but the run header in the list still says "4 proposals".

**Root cause:** `useProposeTasksForRun()` invalidates `["ingestion-run-proposals", runId]` and `["proposals"]` on completion, but does NOT invalidate `["ingestion-runs"]` (the list query that provides `proposal_count`).

**Fix:** Add `qc.invalidateQueries({ queryKey: ["ingestion-runs"] })` to the completion effect in `useProposeTasksForRun()` (`useIngestion.ts` around line 335).

### Bug 3: Run row doesn't show "running" status during propose

**Severity:** Medium — user can't tell which run is being processed

**What happens:** The `getDisplayStatus()` function in `Ingestion.tsx` uses `proposeTasks.isPending` (the mutation pending state) to determine if a run should display as "running". Since the mutation completes in ~100ms, the run row never visually transitions to a "running" badge during the 15-30s LLM call.

**Root cause:** Same as Bug 1 — `isPending` is not the right signal for the background job state.

**Fix:** Use the `isProposing` state from Bug 1's fix. Pass it to `getDisplayStatus()` instead of `proposeTasks.isPending`.

### Bug 4: `tokenCount` hardcoded to `null`

**Severity:** Low — lost feature

**What happens:** `RunRow` in `Ingestion.tsx` line 532 sets `const tokenCount = null;`. The old synchronous flow would show input/output token counts from the propose result. Now this info is never displayed.

**Fix:** Either:
- (a) Add `input_tokens` and `output_tokens` fields to the `IngestionRunDetail` API response (populated by the background job when it finishes), or
- (b) Remove the `tokenCount` variable and any associated UI that references it since it's always null. Accept that token usage info is no longer displayed inline.

Option (b) is simpler and avoids a schema change. Option (a) is better for observability.

### Bug 5: Inconsistent 409 guard between `/sync` and `/runs` endpoints

**Severity:** Low — narrow race window

**What happens:** `/sync` checks the DB for `status=running` AND uses `run_full_pipeline_async` which calls `claim_run()`. `/runs` only checks `has_active_run()` (in-memory). After a server restart, the in-memory set is empty even though a stale `running` run might exist in the DB (between process start and `_reset_stale_runs` completing).

**Fix:** Make `/runs` and `/runs/{id}/rerun` also check the DB for `status=running` runs, consistent with `/sync`. Or, since `_reset_stale_runs` runs before any requests are served (it's in the lifespan startup), just document that the in-memory check is sufficient after startup.

### Bug 6: `claim_run` return value ignored in `run_full_pipeline_async`

**Severity:** Low — defensive programming

**What happens:** `ingestion_job.py` line 170 calls `claim_run(run.id)` without checking the return value.

**Fix:** Either assert the return value is True (it should always be for a just-created run), or remove the call from `run_full_pipeline_async` and have callers handle claiming (which `/runs` and `/runs/{id}/rerun` already do).

---

## UX Improvements

### UX 1: Show granular progress during sync

**Priority:** Nice-to-have

The sync takes 60+ seconds with only a "Syncing..." spinner. Consider adding a status field to `IngestionRun` that the background job updates as it progresses (e.g., "fetching github...", "fetching slack...", "running LLM...") and display this in the Topbar or as a tooltip. This requires a new column or repurposing `error_summary` temporarily.

### UX 2: Don't delete proposals before LLM completes

**Priority:** Medium

Currently `propose_job.py` deletes existing proposals (lines 50-55) before calling the LLM. If the LLM fails, the user loses their old proposals entirely. Consider:
- (a) Only delete old proposals after the new ones are successfully generated (swap atomically), or
- (b) Keep old proposals visible until new ones are committed

### UX 3: Sync success message auto-dismisses too quickly

**Priority:** Low

The "+N proposals" success message in the Topbar auto-dismisses after 4 seconds. After a 60+ second wait, the user might not notice the brief flash. Consider keeping it visible until the next user interaction or extending the timeout.

---

## Implementation Order

1. **Bug 1 + Bug 3** — Expose `isProposing` from `useProposeTasksForRun` and wire it through `Ingestion.tsx`. These are the same root cause.
2. **Bug 2** — Add `["ingestion-runs"]` invalidation to propose completion effect. One-line fix.
3. **UX 2** — Move proposal deletion to after LLM success in `propose_job.py`.
4. **Bug 4** — Decide on token count display approach and implement.
5. **Bug 5 + Bug 6** — Minor backend consistency fixes.
6. **UX 1 + UX 3** — Optional polish.
