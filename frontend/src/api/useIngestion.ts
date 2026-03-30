// src/api/useIngestion.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

export type SourceId = "github" | "gmail" | "slack" | "canvas";

export interface IngestionBatch {
  source_type: string;
  payload: string; // serialised JSON string
  metadata: {
    fetched_at: string;
    since: string;
    count: number;
    kind: string;
    [key: string]: unknown;
  };
}

export interface IngestionPreviewResult {
  success: boolean;
  found_new_content: boolean;
  item_count: number;
  api_calls: number;
  llm_cost: number;
  duration_ms: number;
  batches: IngestionBatch[];
  fetched_at: string;
}

async function fetchPreview(source: SourceId): Promise<IngestionPreviewResult> {
  const res = await fetch(`/api/ingestion/preview/${source}`);
  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText);
    throw new Error(`${source} fetch failed (${res.status}): ${body}`);
  }
  return res.json();
}

export function usePreview(source: SourceId) {
  return useMutation({ mutationFn: () => fetchPreview(source) });
}

// ── Run types ─────────────────────────────────────────────────────────────────

export interface IngestionBatchDetail {
  id: number;
  source_type: string;
  raw_payload: string;
  created_at: string;
  status: string;
  item_count: number | null;
  api_calls: number | null;
  duration_ms: number | null;
  llm_cost: number | null;
  found_new_content: boolean | null;
  success: boolean | null;
  connector_metadata: string | null;
  payload_chars: number;
}

export interface IngestionRunSummary {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: string;
  triggered_by: string;
  range_start: string | null;
  range_end: string | null;
  error_summary: string | null;
  batch_count: number;
  total_chars: number;
  proposal_count: number;
}

export interface IngestionRunDetail extends IngestionRunSummary {
  batches: IngestionBatchDetail[];
}

async function fetchRun(runId: number): Promise<IngestionRunDetail> {
  const res = await fetch(`/api/ingestion/runs/${runId}`);
  if (!res.ok) throw new Error("Failed to fetch run");
  return res.json();
}

export function useIngestionRuns() {
  return useQuery<IngestionRunSummary[]>({
    queryKey: ["ingestion-runs"],
    queryFn: async () => {
      const res = await fetch("/api/ingestion/runs");
      if (!res.ok) throw new Error("Failed to fetch runs");
      return res.json();
    },
  });
}

export function useIngestionRun(id: number | null) {
  return useQuery<IngestionRunDetail>({
    queryKey: ["ingestion-run", id],
    queryFn: async () => {
      const res = await fetch(`/api/ingestion/runs/${id}`);
      if (!res.ok) throw new Error("Failed to fetch run");
      return res.json();
    },
    enabled: id !== null,
  });
}

// ── Run status poller ──────────────────────────────────────────────────────────

/**
 * Polls GET /ingestion/runs/{runId} every 2.5 s while the run is in "running"
 * status. Stops polling automatically once the status transitions.
 */
function useRunStatusPoller(runId: number | null) {
  return useQuery<IngestionRunDetail>({
    queryKey: ["ingestion-run", runId],
    queryFn: () => fetchRun(runId!),
    enabled: runId !== null,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 2500 : false),
  });
}

export function useCreateIngestionRun() {
  const qc = useQueryClient();
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const invalidatedForRef = useRef<number | null>(null);

  const polled = useRunStatusPoller(activeRunId);

  // When the polled run transitions out of "running", invalidate caches (once per run).
  useEffect(() => {
    if (
      activeRunId !== null &&
      polled.data &&
      polled.data.status !== "running" &&
      invalidatedForRef.current !== activeRunId
    ) {
      invalidatedForRef.current = activeRunId;
      qc.invalidateQueries({ queryKey: ["ingestion-runs"] });
    }
  }, [activeRunId, polled.data, qc]);

  return useMutation({
    mutationFn: async (params: { start_date: string; end_date?: string }) => {
      const res = await fetch("/api/ingestion/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Create run failed (${res.status}): ${body}`);
      }
      return res.json() as Promise<IngestionRunSummary>;
    },
    onMutate: async (params) => {
      await qc.cancelQueries({ queryKey: ["ingestion-runs"] });
      const previous = qc.getQueryData<IngestionRunSummary[]>(["ingestion-runs"]);
      const placeholder: IngestionRunSummary = {
        id: -1,
        started_at: new Date().toISOString(),
        finished_at: null,
        status: "running",
        triggered_by: "manual",
        range_start: params.start_date,
        range_end: params.end_date ?? null,
        error_summary: null,
        batch_count: 0,
        total_chars: 0,
        proposal_count: 0,
      };
      qc.setQueryData<IngestionRunSummary[]>(["ingestion-runs"], (old) => [
        placeholder,
        ...(old ?? []),
      ]);
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        qc.setQueryData(["ingestion-runs"], context.previous);
      }
    },
    onSuccess: (data) => {
      setActiveRunId(data.id);
      qc.invalidateQueries({ queryKey: ["ingestion-runs"] });
    },
  });
}

export function useRerunIngestionRun() {
  const qc = useQueryClient();
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const invalidatedForRef = useRef<number | null>(null);

  const polled = useRunStatusPoller(activeRunId);

  // When the polled run transitions out of "running", invalidate caches (once per run).
  useEffect(() => {
    if (
      activeRunId !== null &&
      polled.data &&
      polled.data.status !== "running" &&
      invalidatedForRef.current !== activeRunId
    ) {
      invalidatedForRef.current = activeRunId;
      qc.invalidateQueries({ queryKey: ["ingestion-runs"] });
    }
  }, [activeRunId, polled.data, qc]);

  return useMutation({
    mutationFn: async (runId: number) => {
      const res = await fetch(`/api/ingestion/runs/${runId}/rerun`, {
        method: "POST",
      });
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Rerun failed (${res.status}): ${body}`);
      }
      return res.json() as Promise<IngestionRunSummary>;
    },
    onSuccess: (data, runId) => {
      setActiveRunId(data.id);
      qc.invalidateQueries({ queryKey: ["ingestion-runs"] });
      qc.invalidateQueries({ queryKey: ["ingestion-run", runId] });
    },
  });
}

export function useDeleteIngestionRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (runId: number) => {
      const res = await fetch(`/api/ingestion/runs/${runId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Delete failed (${res.status}): ${body}`);
      }
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ingestion-runs"] });
    },
  });
}

// ── Per-run proposals ─────────────────────────────────────────────────────────

export interface RunProposal {
  id: number;
  proposal_type: string;
  status: string;
  task_id: number | null;
  proposed_title: string | null;
  proposed_description: string | null;
  proposed_status: string | null;
  proposed_due_at: string | null;
  proposed_external_ref: string | null;
  reason_summary: string | null;
  created_at: string;
}

export interface ProposeResult {
  run_id: number;
  status: "running";
}

export function useRunProposals(runId: number | null, refetchWhileProposing = false) {
  return useQuery<RunProposal[]>({
    queryKey: ["ingestion-run-proposals", runId],
    queryFn: async () => {
      const res = await fetch(`/api/ingestion/runs/${runId}/proposals`);
      if (!res.ok) throw new Error("Failed to fetch proposals");
      return res.json();
    },
    enabled: runId !== null,
    refetchInterval: refetchWhileProposing ? 2500 : false,
  });
}

export function useRunPrompt(runId: number | null) {
  return useQuery<PromptPreviewResult>({
    queryKey: ["ingestion-run-prompt", runId],
    queryFn: async () => {
      const res = await fetch(`/api/ingestion/runs/${runId}/prompt-preview`);
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Prompt preview failed (${res.status}): ${body}`);
      }
      return res.json();
    },
    enabled: runId !== null,
  });
}

export function useProposeTasksForRun() {
  const qc = useQueryClient();
  const [proposingRunId, setProposingRunId] = useState<number | null>(null);
  const invalidatedForRef = useRef<number | null>(null);

  // Also poll the run itself so we can detect completion / failure.
  const polledRun = useQuery<IngestionRunDetail>({
    queryKey: ["ingestion-run", proposingRunId],
    queryFn: () => fetchRun(proposingRunId!),
    enabled: proposingRunId !== null,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 2500 : false),
  });

  // Derive proposing state from run data.
  const isProposing =
    proposingRunId !== null && (!polledRun.data || polledRun.data.status === "running");

  // Poll the proposals list while a propose job is in flight.
  useQuery<RunProposal[]>({
    queryKey: ["ingestion-run-proposals", proposingRunId],
    queryFn: async () => {
      const res = await fetch(`/api/ingestion/runs/${proposingRunId}/proposals`);
      if (!res.ok) throw new Error("Failed to fetch proposals");
      return res.json();
    },
    enabled: proposingRunId !== null && isProposing,
    refetchInterval: isProposing ? 2500 : false,
  });

  // When the run is no longer running, invalidate caches (once per run).
  useEffect(() => {
    if (
      proposingRunId !== null &&
      polledRun.data &&
      polledRun.data.status !== "running" &&
      invalidatedForRef.current !== proposingRunId
    ) {
      invalidatedForRef.current = proposingRunId;
      qc.invalidateQueries({ queryKey: ["ingestion-run-proposals", proposingRunId] });
      qc.invalidateQueries({ queryKey: ["proposals"] });
      qc.invalidateQueries({ queryKey: ["ingestion-runs"] });
    }
  }, [proposingRunId, polledRun.data, qc]);

  const mutation = useMutation({
    mutationFn: async (runId: number): Promise<ProposeResult> => {
      const res = await fetch(`/api/ingestion/runs/${runId}/propose`, { method: "POST" });
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Propose failed (${res.status}): ${body}`);
      }
      return res.json();
    },
    onSuccess: (_data, runId) => {
      invalidatedForRef.current = null;
      setProposingRunId(runId);
      // Immediately invalidate so the run list shows "running" status.
      qc.invalidateQueries({ queryKey: ["ingestion-runs"] });
    },
    onError: () => {
      setProposingRunId(null);
    },
  });

  return { mutation, isProposing };
}

// ── Prompt & LLM preview types ───────────────────────────────────────────────

export interface PromptPreviewResult {
  run_id: number;
  system_prompt: string;
  user_prompt: string;
  token_count: number;
}

export interface LLMPreviewResult {
  run_id: number;
  model: string;
  proposals: Array<Record<string, unknown>>;
  content: string | null;
  input_tokens: number;
  output_tokens: number;
  duration_ms: number;
}

export function usePromptPreview() {
  return useMutation({
    mutationFn: async (runId: number) => {
      const res = await fetch(`/api/ingestion/runs/${runId}/prompt-preview`);
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Prompt preview failed (${res.status}): ${body}`);
      }
      return res.json() as Promise<PromptPreviewResult>;
    },
  });
}

export function useLLMPreview() {
  return useMutation({
    mutationFn: async (runId: number) => {
      const res = await fetch(`/api/ingestion/runs/${runId}/llm-preview`, {
        method: "POST",
      });
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`LLM preview failed (${res.status}): ${body}`);
      }
      return res.json() as Promise<LLMPreviewResult>;
    },
  });
}

// ── Sync (full pipeline) ─────────────────────────────────────────────────────

export interface SyncResult {
  run_id: number;
  status: "running";
}

export function useSyncPipeline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<SyncResult> => {
      const res = await fetch("/api/ingestion/sync", { method: "POST" });
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Sync failed (${res.status}): ${body}`);
      }
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ingestion-runs"] });
      qc.invalidateQueries({ queryKey: ["proposals"] });
    },
  });
}

/**
 * Full-pipeline sync with async polling support.
 *
 * Fires POST /sync → receives {run_id, status: "running"} → polls
 * GET /ingestion/runs/{run_id} every 2.5 s until the run is no longer
 * "running", then invalidates ingestion-runs and proposals caches.
 *
 * Returns { trigger, isRunning, run, error }.
 */
export function useSyncPipelineWithPolling() {
  const qc = useQueryClient();
  const [runId, setRunId] = useState<number | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const invalidatedForRef = useRef<number | null>(null);

  // On mount, check if there's already a running run (survives navigation/refresh).
  const runsQuery = useQuery<IngestionRunSummary[]>({
    queryKey: ["ingestion-runs"],
    queryFn: async () => {
      const res = await fetch("/api/ingestion/runs");
      if (!res.ok) return [];
      return res.json();
    },
  });

  useEffect(() => {
    if (runId === null && runsQuery.data) {
      const running = runsQuery.data.find((r) => r.status === "running");
      if (running) {
        setRunId(running.id);
      }
    }
  }, [runId, runsQuery.data]);

  const run = useQuery<IngestionRunDetail>({
    queryKey: ["ingestion-run", runId],
    queryFn: () => fetchRun(runId!),
    enabled: runId !== null,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 2500 : false),
  });

  // Derive running state from query data.
  const isRunning = runId !== null && (!run.data || run.data.status === "running");

  // When status transitions out of "running", refresh caches (once per run).
  useEffect(() => {
    if (
      runId !== null &&
      run.data &&
      run.data.status !== "running" &&
      invalidatedForRef.current !== runId
    ) {
      invalidatedForRef.current = runId;
      qc.invalidateQueries({ queryKey: ["ingestion-runs"] });
      qc.invalidateQueries({ queryKey: ["proposals"] });
    }
  }, [runId, run.data, qc]);

  const trigger = async () => {
    setError(null);
    setRunId(null);
    invalidatedForRef.current = null;
    try {
      const res = await fetch("/api/ingestion/sync", { method: "POST" });
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Sync failed (${res.status}): ${body}`);
      }
      const data: SyncResult = await res.json();
      setRunId(data.run_id);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  };

  return { trigger, isRunning, run: run.data ?? null, error };
}
