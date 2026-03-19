import { useCallback, useMemo, useState } from "react";
import type { Prompt } from "../../api/usePrompts";
import { parseSystemPrompt, serializeSegments, type CanvasSegment } from "../../utils/parsePrompt";

export function useSystemPromptCanvas(systemPrompt: Prompt) {
  const [prevContent, setPrevContent] = useState(systemPrompt.content);
  const [segments, setSegments] = useState<CanvasSegment[]>(() =>
    parseSystemPrompt(systemPrompt.content),
  );

  // Sync with server data when it changes (e.g. after save + query invalidation).
  // Using "adjust state during render" instead of useEffect to avoid cascading renders.
  if (prevContent !== systemPrompt.content) {
    setPrevContent(systemPrompt.content);
    setSegments(parseSystemPrompt(systemPrompt.content));
  }

  const systemDirty = useMemo(
    () => serializeSegments(segments) !== systemPrompt.content.trim(),
    [segments, systemPrompt.content],
  );

  const reset = useCallback(() => {
    setSegments(parseSystemPrompt(systemPrompt.content));
  }, [systemPrompt.content]);

  return { segments, setSegments, systemDirty, reset };
}
