// src/api/useIngestion.ts
import { useMutation } from '@tanstack/react-query'

export type SourceId = 'github' | 'gmail' | 'slack' | 'canvas'

export interface IngestionBatch {
  source_type: string
  payload: string   // serialised JSON string
  metadata: {
    fetched_at: string
    since: string
    count: number
    kind: string
    [key: string]: unknown
  }
}

export interface IngestionPreviewResult {
  success: boolean
  found_new_content: boolean
  item_count: number
  api_calls: number
  llm_cost: number
  duration_ms: number
  batches: IngestionBatch[]
  fetched_at: string
}

async function fetchPreview(source: SourceId): Promise<IngestionPreviewResult> {
  const res = await fetch(`/api/ingestion/preview/${source}`)
  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText)
    throw new Error(`${source} fetch failed (${res.status}): ${body}`)
  }
  return res.json()
}

export function usePreview(source: SourceId) {
  return useMutation({ mutationFn: () => fetchPreview(source) })
}
