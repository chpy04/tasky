import { useCallback, useMemo, useState } from "react";
import type { Prompt } from "../../api/usePrompts";
import { SOURCE_TYPES, type SourceType } from "../../utils/parsePrompt";
import type { SourceDraft } from "./SourceEditor";

function buildDrafts(sourcePrompts: Prompt[]): Record<SourceType, SourceDraft> {
  const drafts = {} as Record<SourceType, SourceDraft>;
  for (const st of SOURCE_TYPES) {
    const prompt = sourcePrompts.find((p) => p.source_type === st);
    const content = prompt?.content ?? "";
    const description = prompt?.description ?? "";
    drafts[st] = { content, description, savedContent: content, savedDescription: description };
  }
  return drafts;
}

export function useSourceDrafts(sourcePrompts: Prompt[]) {
  const [prevSourcePrompts, setPrevSourcePrompts] = useState(sourcePrompts);
  const [sourceDrafts, setSourceDrafts] = useState<Record<SourceType, SourceDraft>>(() =>
    buildDrafts(sourcePrompts),
  );

  // Sync with server data when it changes (e.g. after save + query invalidation).
  // Using "adjust state during render" instead of useEffect to avoid cascading renders.
  if (prevSourcePrompts !== sourcePrompts) {
    setPrevSourcePrompts(sourcePrompts);
    setSourceDrafts(buildDrafts(sourcePrompts));
  }

  const dirtySourceTypes = useMemo<Set<SourceType>>(() => {
    const dirty = new Set<SourceType>();
    for (const st of SOURCE_TYPES) {
      const d = sourceDrafts[st];
      if (d && (d.content !== d.savedContent || d.description !== d.savedDescription)) {
        dirty.add(st);
      }
    }
    return dirty;
  }, [sourceDrafts]);

  // Short preview for each source chip — first non-empty line, max 72 chars
  const sourcePreviews = useMemo<Record<SourceType, string>>(() => {
    const out = {} as Record<SourceType, string>;
    for (const st of SOURCE_TYPES) {
      const draft = sourceDrafts[st];
      const first =
        draft.content
          .trim()
          .split("\n")
          .find((l) => l.trim()) ?? "";
      out[st] = first.length > 72 ? first.slice(0, 69) + "…" : first;
    }
    return out;
  }, [sourceDrafts]);

  // Mark all current draft values as saved (called after a successful save)
  const markAllSaved = useCallback(() => {
    setSourceDrafts((prev) => {
      const next = { ...prev } as Record<SourceType, SourceDraft>;
      for (const st of SOURCE_TYPES) {
        next[st] = {
          ...next[st],
          savedContent: next[st].content,
          savedDescription: next[st].description,
        };
      }
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    setSourceDrafts(buildDrafts(sourcePrompts));
  }, [sourcePrompts]);

  return { sourceDrafts, setSourceDrafts, dirtySourceTypes, sourcePreviews, markAllSaved, reset };
}
