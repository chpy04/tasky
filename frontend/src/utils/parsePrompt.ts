export type TextSegment = { kind: "text"; id: string; content: string };
export type SourceSegment = { kind: "source"; sourceType: SourceType };
export type ExperienceSegment = { kind: "experiences" };
export type ActiveTasksSegment = { kind: "active_tasks" };
export type SourceDataSegment = { kind: "source_data"; sourceType: SourceType };
export type ReadOnlySegment = ExperienceSegment | ActiveTasksSegment | SourceDataSegment;
export type CanvasSegment = TextSegment | SourceSegment | ReadOnlySegment;

export const SOURCE_TYPES = ["github", "slack", "email", "canvas"] as const;
export type SourceType = (typeof SOURCE_TYPES)[number];

export const SOURCE_DISPLAY: Record<SourceType, { label: string; color: string }> = {
  github: { label: "GitHub", color: "#4078c8" },
  slack: { label: "Slack", color: "#611f69" },
  email: { label: "Email", color: "#d44638" },
  canvas: { label: "Canvas", color: "#e66000" },
};

export type SelectedBlock =
  | { kind: "source"; sourceType: SourceType }
  | { kind: "experiences" }
  | { kind: "active_tasks" }
  | { kind: "source_data"; sourceType: SourceType };

export const READONLY_BLOCK_INFO = {
  experiences: {
    label: "Experiences",
    color: "#5b3fa0",
    glyph: "◈",
    description:
      "Replaced at runtime with your active experience names (projects, jobs, classes, clubs) so the model can attribute tasks to the correct context.",
  },
  active_tasks: {
    label: "Active Tasks",
    color: "#1a6878",
    glyph: "≡",
    description:
      "Replaced at runtime with currently open tasks so the model can propose updates to existing items rather than creating duplicates.",
  },
  source_data: {
    label: "Data",
    color: "#2a6835",
    description: "Replaced at runtime with raw connector data fetched during the ingestion run.",
  },
} as const;

// Unified marker regex: [[source:X]], [[source_data:X]], [[experiences]], [[active_tasks]]
const MARKER_RE = /\[\[(\w+)(?::(\w+))?\]\]/g;

export function parseSystemPrompt(raw: string): CanvasSegment[] {
  const segments: CanvasSegment[] = [];
  let lastIndex = 0;
  let textCount = 0;

  // Reset regex state
  MARKER_RE.lastIndex = 0;

  const addTextChunk = (text: string) => {
    // Split each text chunk into individual paragraphs so every paragraph gets its own drop zone
    const paragraphs = text.trim().split(/\n\n+/);
    for (const para of paragraphs) {
      const p = para.trim();
      if (p) segments.push({ kind: "text", id: `t${textCount++}`, content: p });
    }
  };

  let match: RegExpExecArray | null;
  while ((match = MARKER_RE.exec(raw)) !== null) {
    addTextChunk(raw.slice(lastIndex, match.index));

    const [, markerKind, markerArg] = match;

    if (
      markerKind === "source" &&
      markerArg &&
      (SOURCE_TYPES as readonly string[]).includes(markerArg)
    ) {
      segments.push({ kind: "source", sourceType: markerArg as SourceType });
    } else if (
      markerKind === "source_data" &&
      markerArg &&
      (SOURCE_TYPES as readonly string[]).includes(markerArg)
    ) {
      segments.push({ kind: "source_data", sourceType: markerArg as SourceType });
    } else if (markerKind === "experiences") {
      segments.push({ kind: "experiences" });
    } else if (markerKind === "active_tasks") {
      segments.push({ kind: "active_tasks" });
    }
    // unknown marker kinds silently stripped

    lastIndex = match.index + match[0].length;
  }

  addTextChunk(raw.slice(lastIndex));

  return segments;
}

export function serializeSegments(segments: CanvasSegment[]): string {
  const parts: string[] = [];
  for (const seg of segments) {
    if (seg.kind === "text") {
      if (seg.content.trim()) parts.push(seg.content.trim());
    } else if (seg.kind === "source") {
      parts.push(`[[source:${seg.sourceType}]]`);
    } else if (seg.kind === "source_data") {
      parts.push(`[[source_data:${seg.sourceType}]]`);
    } else if (seg.kind === "experiences") {
      parts.push(`[[experiences]]`);
    } else if (seg.kind === "active_tasks") {
      parts.push(`[[active_tasks]]`);
    }
  }
  return parts.join("\n\n").trim();
}

/** Return source types whose instruction block is not placed in the canvas. */
export function getUnplacedSources(segments: CanvasSegment[]): SourceType[] {
  const placed = new Set(
    segments.filter((s): s is SourceSegment => s.kind === "source").map((s) => s.sourceType),
  );
  return SOURCE_TYPES.filter((st) => !placed.has(st));
}

/** Return source types whose data block is not placed in the canvas. */
export function getUnplacedSourceData(segments: CanvasSegment[]): SourceType[] {
  const placed = new Set(
    segments
      .filter((s): s is SourceDataSegment => s.kind === "source_data")
      .map((s) => s.sourceType),
  );
  return SOURCE_TYPES.filter((st) => !placed.has(st));
}

/** Source types where source block is directly followed by its source_data block in segments. */
export function getAdjacentConnectedPairs(segments: CanvasSegment[]): Set<SourceType> {
  const pairs = new Set<SourceType>();
  for (let i = 0; i < segments.length - 1; i++) {
    const cur = segments[i],
      next = segments[i + 1];
    if (cur.kind === "source" && next.kind === "source_data" && cur.sourceType === next.sourceType)
      pairs.add(cur.sourceType);
  }
  return pairs;
}

/** Source types where both the source and source_data block are unplaced (both in tray). */
export function getUnplacedConnectedPairs(
  unplacedInstructions: SourceType[],
  unplacedData: SourceType[],
): Set<SourceType> {
  const dataSet = new Set(unplacedData);
  return new Set(unplacedInstructions.filter((st) => dataSet.has(st)));
}
