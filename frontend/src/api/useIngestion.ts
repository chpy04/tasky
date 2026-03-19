// src/api/useIngestion.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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

export function useCreateIngestionRun() {
  const qc = useQueryClient();
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
      return res.json() as Promise<IngestionRunDetail>;
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
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["ingestion-runs"] });
    },
  });
}

export function useRerunIngestionRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (runId: number) => {
      const res = await fetch(`/api/ingestion/runs/${runId}/rerun`, {
        method: "POST",
      });
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Rerun failed (${res.status}): ${body}`);
      }
      return res.json() as Promise<IngestionRunDetail>;
    },
    onSuccess: (_data, runId) => {
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
  model: string;
  proposals_saved: number;
  input_tokens: number;
  output_tokens: number;
  duration_ms: number;
}

export function useRunProposals(runId: number | null) {
  return useQuery<RunProposal[]>({
    queryKey: ["ingestion-run-proposals", runId],
    queryFn: async () => {
      const res = await fetch(`/api/ingestion/runs/${runId}/proposals`);
      if (!res.ok) throw new Error("Failed to fetch proposals");
      return res.json();
    },
    enabled: runId !== null,
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
  return useMutation({
    mutationFn: async (runId: number): Promise<ProposeResult> => {
      const res = await fetch(`/api/ingestion/runs/${runId}/propose`, { method: "POST" });
      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Propose failed (${res.status}): ${body}`);
      }
      return res.json();
    },
    onSuccess: (_data, runId) => {
      qc.invalidateQueries({ queryKey: ["ingestion-run-proposals", runId] });
      qc.invalidateQueries({ queryKey: ["proposals"] });
    },
  });
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
  status: string;
  proposals_saved: number;
  duration_ms?: number;
  input_tokens?: number;
  output_tokens?: number;
  error?: string;
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
