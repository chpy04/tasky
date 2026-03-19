# Plan: Prompt Composer UI

## Overview

Redesign the Prompts page from a simple list of text editors into a visual "composer" — a canvas where the system prompt is displayed as inline-editable text and source prompt blocks (GitHub, Slack, Email, Canvas) are draggable chips that can be positioned between paragraphs. Block position determines the actual assembly order of the final prompt sent to the LLM.

---

## Decisions

| Question | Answer |
|---|---|
| Block position affects LLM assembly order | Yes |
| Unplaced blocks (no marker) | Excluded entirely from the run |
| Drop zone granularity | Between paragraphs |
| Visual reaction on drag | Glowing/expanding drop zone gap |
| System prompt editing | Inline in the canvas |
| Block display | Name + icon only (no content preview) |
| Save scope | Cmd+S / Save button saves everything at once |
| Icons | Colored letter-badge SVGs (no new dep) |

---

## Marker Format

Source block positions are encoded directly in the system prompt text using markers:

```
[[source:github]]
[[source:slack]]
[[source:email]]
[[source:canvas]]
```

Each marker sits on its own line, surrounded by blank lines. No new DB columns are needed — position is stored in the text itself. Unplaced = no marker in the text = source excluded from the run.

**Example stored system prompt:**
```
You are a task management assistant. Review the data below and propose task changes.

[[source:github]]

When reviewing Slack messages, focus on action items and blockers.

[[source:slack]]

Always output structured JSON proposals using the schema provided.
```

---

## New Dependencies

- **`@dnd-kit/core`** + **`@dnd-kit/sortable`** — drag and drop. Only new runtime dependency.
  - Install: `npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities`

---

## Layout

```
┌─────────────────────────────────┬─────────────────────────────┐
│  CANVAS (left, ~62%)            │  EDITOR PANEL (right, ~38%) │
│  ─────────────────────────────  │  ─────────────────────────  │
│                                 │                             │
│  You are a task management      │  ╔═══════════════════════╗  │
│  assistant. Review the data     │  ║  G  GitHub            ║  │
│  and propose task changes...    │  ╠═══════════════════════╣  │
│            [click to edit]      │  ║ description input     ║  │
│                                 │  ╠═══════════════════════╣  │
│  ┄┄ drop zone ┄┄┄┄┄┄┄┄┄┄┄┄┄   │  ║                       ║  │
│  ╔═══════════════════════════╗  │  ║  content textarea     ║  │
│  ║ ⠿  G  GitHub              ║  │  ║                       ║  │
│  ╚═══════════════════════════╝  │  ╚═══════════════════════╝  │
│  ┄┄ drop zone ┄┄┄┄┄┄┄┄┄┄┄┄┄   │  [Discard]  [Save  ⌘S]      │
│                                 │                             │
│  When reviewing Slack messages, │                             │
│  focus on action items...       │                             │
│            [click to edit]      │                             │
│                                 │                             │
│  ┄┄ drop zone ┄┄┄┄┄┄┄┄┄┄┄┄┄   │                             │
│  ╔═══════════════════════════╗  │                             │
│  ║ ⠿  S  Slack               ║  │                             │
│  ╚═══════════════════════════╝  │                             │
│  ┄┄ drop zone ┄┄┄┄┄┄┄┄┄┄┄┄┄   │                             │
│                                 │                             │
│  Always output structured...    │                             │
│                                 │                             │
│  ── Unplaced ───────────────    │                             │
│  ╔═══════╗ ╔═══════╗           │                             │
│  ║ Email ║ ║Canvas ║           │                             │
│  ╚═══════╝ ╚═══════╝           │                             │
└─────────────────────────────────┴─────────────────────────────┘
```

---

## Frontend: Component Tree

```
Prompts.tsx (page — becomes a thin shell)
└── PromptComposer.tsx           — left/right split layout, owns all state
    ├── PromptCanvas.tsx         — left panel: renders segments + chips
    │   ├── TextSegment.tsx      — inline-editable paragraph block
    │   ├── SourceChip.tsx       — draggable 48px chip (icon + name)
    │   ├── DropZone.tsx         — glowing drop target between segments
    │   └── UnplacedTray.tsx     — horizontal row of unplaced chips at bottom
    └── SourceEditor.tsx         — right panel: edits selected source block
        └── (empty state when nothing selected)

utils/parsePrompt.ts             — pure fns: string ↔ CanvasSegment[]
```

---

## State Shape

```ts
// utils/parsePrompt.ts
export type TextSegment   = { kind: "text";   id: string; content: string };
export type SourceSegment = { kind: "source"; sourceType: string };
export type CanvasSegment = TextSegment | SourceSegment;

// All valid source type keys
export const SOURCE_TYPES = ["github", "slack", "email", "canvas"] as const;
export type SourceType = typeof SOURCE_TYPES[number];

export const SOURCE_DISPLAY: Record<SourceType, { label: string; color: string; letter: string }> = {
  github: { label: "GitHub", color: "#4078c8", letter: "G" },
  slack:  { label: "Slack",  color: "#611f69", letter: "S" },
  email:  { label: "Email",  color: "#d44638", letter: "E" },
  canvas: { label: "Canvas", color: "#e66000", letter: "C" },
};

// PromptComposer internal state
type ComposerState = {
  segments: CanvasSegment[];           // interleaved text + source blocks, in order
  unplaced: SourceType[];              // source types not yet placed in the canvas
  sourceDrafts: Record<string, {       // keyed by source_type string
    content: string;
    description: string;
    savedContent: string;
    savedDescription: string;
  }>;
  selectedSource: SourceType | null;   // which chip is open in right panel
};
```

---

## `parsePrompt.ts` — Serialization Round-Trip

```ts
const MARKER_RE = /\[\[source:(\w+)\]\]/g;

// "...text...\n\n[[source:github]]\n\n...more..."
//   →  [TextSegment, SourceSegment, TextSegment]
export function parseSystemPrompt(raw: string): CanvasSegment[] { ... }

// [TextSegment, SourceSegment, TextSegment]
//   →  "...text...\n\n[[source:github]]\n\n...more..."
export function serializeSegments(segments: CanvasSegment[]): string { ... }
```

Parsing rules:
- Split on `\n\n[[source:X]]\n\n` (or just `[[source:X]]` with surrounding whitespace trimmed)
- Each text piece between markers → `TextSegment` with a stable `id` (e.g. `t0`, `t1`)
- Empty text segments (from adjacent markers or leading/trailing whitespace) are dropped
- Unknown source types in markers are stripped silently

Serialization rules:
- Join text segments with `\n\n`
- Insert `\n\n[[source:X]]\n\n` at each SourceSegment position
- Trim leading/trailing whitespace from the result

---

## Canvas Interactions

### Drag and Drop (`@dnd-kit`)

```
DndContext (onDragStart, onDragEnd)
  ├── Draggable(id="chip-github")   ← SourceChip
  ├── Draggable(id="chip-slack")    ← SourceChip (in UnplacedTray)
  └── Droppable(id="drop-0")        ← DropZone between segment 0 and 1
      Droppable(id="drop-1")        ← DropZone between segment 1 and 2
      ...
```

- `onDragStart`: set `isDragging = true` → all drop zones expand and render glow
- `onDragEnd(event)`:
  - If dropped on a `drop-N` zone: remove chip's SourceSegment from current position, insert at index N
  - If dropped on `unplaced-tray`: remove SourceSegment from segments, add to `unplaced`
  - If dropped on nothing (cancelled): no-op
- Drop zones are always rendered (zero-height when not dragging, expand on drag)

### Drop Zone Visual States

```
idle:     height: 2px,  border: 1px dashed, opacity: 0.3
dragging: height: 20px, border: 1px dashed, opacity: 0.6,  background: faint highlight
active:   height: 24px, border: 1px solid,  opacity: 1.0,  box-shadow: glow
```

### Inline Text Editing

- Each `TextSegment` renders as a styled `<div>` with the paragraph text
- On click → replaces with an auto-sized `<textarea>` at the same position (no layout shift)
- `onBlur` / Enter-then-click-elsewhere: commits edit to `segments` state (does NOT save to server)
- Only one segment editable at a time; clicking a different segment commits the previous one first
- No "edited" indicator on text segments — all pending changes are indicated by the global save bar

### SourceChip

- 48px tall, full canvas width
- Left: drag handle (`⠿`) — drag only initiates from this handle to avoid conflicts with click
- Middle: colored letter badge + source name
- Right: if this source has unsaved content changes, show a small `•` dot
- Click anywhere except handle: selects the chip → opens in right panel, highlights chip border

---

## Right Panel (SourceEditor)

**Empty state** (nothing selected):
```
Click a source block to edit its prompt content.
```

**Selected state:**
- Header: colored letter badge + source name (large)
- `<input>` for description (labeled "Description")
- `<textarea>` for content (auto-sized, monospace, labeled "Content")
- Footer: `[Discard]` `[Save ⌘S]` buttons — but these save EVERYTHING (see Save section)
- Unsaved indicator: shows "unsaved changes" if `sourceDrafts[selected]` differs from saved values

**Switching selection with unsaved changes:**
- Changes stay in `sourceDrafts` (not lost) — the `•` dot on the chip reminds the user
- No blocking modal; switching is instant

---

## Save Behavior

Cmd+S (anywhere on the page) or the Save button fires one unified save:

1. Serialize `segments` → new system prompt string
2. `PATCH /prompts/{systemPrompt.id}` with `{ content: serialized }`
3. For each source type where `draft !== saved`:
   - `PATCH /prompts/{sourcePrompt.id}` with `{ content, description }`
4. On all success: clear all dirty state, show "saved" confirmation briefly
5. On any failure: show error, leave dirty state intact for retry

All PATCHes fire in parallel (Promise.all). The existing `useUpdatePrompt` mutation hook is reused per-prompt.

---

## Backend: `prompt_builder.py` Changes

### What changes

Currently, `build_proposal_prompt` returns `(system_prompt_text, user_prompt)` where:
- `system_prompt_text` = raw system prompt content (passed to Claude as the system message)
- `user_prompt` includes source-specific instruction text prepended to each source's batch data

**After this change:**
- The system prompt is expanded in-place — `[[source:X]]` markers are replaced with source instruction content
- Source instructions move from the user message into the system message
- Batch data (raw JSON payloads) remains in the user message, but without the source preface text

### New helper

```python
import re

MARKER_RE = re.compile(r'\[\[source:(\w+)\]\]')

def _expand_markers(system_prompt: str, source_prompts: dict[SourceType, str]) -> str:
    """Replace [[source:X]] markers with actual source instruction content."""
    def replacer(m: re.Match) -> str:
        try:
            st = SourceType(m.group(1))
        except ValueError:
            return ""  # unknown source type — strip the marker
        content = source_prompts.get(st)
        if content is None:
            return ""  # source not configured or unplaced — exclude entirely
        display = _SOURCE_DISPLAY_NAMES.get(st, st.value)
        return f"---\n\n## {display} Instructions\n\n{content}"
    return MARKER_RE.sub(replacer, system_prompt).strip()
```

### Updated `build_proposal_prompt`

```python
def build_proposal_prompt(...) -> tuple[str, str]:
    system_raw, source_prompts = _get_active_prompts(db)
    system_expanded = _expand_markers(system_raw, source_prompts)
    user_prompt = _build_user_prompt(run, source_prompts, active_tasks or [], experiences or [])
    return system_expanded, user_prompt
```

`_build_user_prompt` is updated to **not** prepend source instruction text before each batch — it only includes the batch header and raw payload. The instructions are now in the system message.

### Behavior change summary

| Aspect | Before | After |
|---|---|---|
| Source instruction location | User message (prepended per source section) | System message (at marker position) |
| Unplaced sources | Always included | Excluded entirely |
| Assembly order | Sources always appended after batch data intro | Sources appear wherever markers are placed |
| No markers in system prompt | All sources included at end (fallback) | All sources unplaced → excluded |

> **Important:** The fallback "no markers = append at end" behavior from before is intentionally removed. If the system prompt has no markers, no source instructions appear. This is a deliberate behavior change that matches the "unplaced = excluded" decision.

---

## Implementation Order

1. **`utils/parsePrompt.ts`** — pure functions, no React, easy to verify with unit tests
2. **`DropZone.tsx` + `SourceChip.tsx`** — small leaf components
3. **`TextSegment.tsx`** — inline editing component
4. **`UnplacedTray.tsx`** — horizontal chip row
5. **`PromptCanvas.tsx`** — assembles the above with `@dnd-kit` DndContext
6. **`SourceEditor.tsx`** — right panel, straightforward form
7. **`PromptComposer.tsx`** — top-level state, save logic, layout
8. **`Prompts.tsx`** — swap out old content, render PromptComposer
9. **`prompt_builder.py`** — `_expand_markers`, update `_build_user_prompt`
10. **CSS modules** — styling for each new component

---

## Edge Cases to Handle

- **System prompt with no markers** → all sources show as unplaced on first load
- **Marker for unknown source** → stripped silently on parse, source remains unplaced
- **All sources unplaced** → ingestion run proceeds with no source instructions (user's intent)
- **Adjacent markers** (no text between them) → renders as two chips with no text block between them; serializes correctly
- **Empty text segment** (marker at very start or end) → drop the empty TextSegment, don't render a blank editable block
- **Concurrent edits** — last save wins; no optimistic locking needed for a single-user local app
- **Prompt not found in DB** (e.g. source type exists in SourceType enum but no DB row) → skip silently, don't crash canvas
