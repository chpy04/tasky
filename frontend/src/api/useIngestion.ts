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
    onSuccess: () => {
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
