# Connected Source + Data Blocks

## Overview

A source (`[[source:X]]`) and data (`[[source_data:X]]`) block of the same `sourceType` are
"connected" when either:
- They are **adjacent in the canvas** (source immediately precedes data)
- **Both are unplaced** in the tray

When connected: show a chain link icon between them. When the user drags the source block, carry
the data block along. Dragging the data block away disconnects the pair (implicit — no explicit
disconnect button).

---

## 1. `parsePrompt.ts` — Add detection utilities

Add two exported functions:

```ts
/** Source types where source block is directly followed by its source_data block in segments. */
export function getAdjacentConnectedPairs(segments: CanvasSegment[]): Set<SourceType> {
  const pairs = new Set<SourceType>();
  for (let i = 0; i < segments.length - 1; i++) {
    const cur = segments[i], next = segments[i + 1];
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
  return new Set(unplacedInstructions.filter(st => dataSet.has(st)));
}
```

---

## 2. `DropZone.tsx` — Add `isChainLink` prop

Add a prop `isChainLink?: boolean`. When true and `isNearest` is false (i.e. not actively being
hovered during drag), render a small chain link icon in place of the normal collapsed drop zone.
The zone is still droppable — dropping something between connected chips disconnects the pair by
breaking adjacency.

```tsx
interface DropZoneProps {
  id: string;
  isNearest: boolean;
  isChainLink?: boolean; // NEW
}
```

Render logic:
- If `isChainLink && !isNearest`: render `<div className={styles.chainLink}>` with a chain icon
  (⛓ or small SVG). Retain the underlying droppable ref so drops still register.
- Otherwise: existing behavior.

`DropZone.module.css` additions:
```css
.chainLink {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 18px;
  opacity: 0.45;
  color: var(--color-accent);
  font-size: 13px;
  transition: opacity 0.15s;
}
.chainLink:hover {
  opacity: 0.8;
}
```

---

## 3. `PromptCanvas.tsx` — Main changes

### A. Compute connected state (at render time)

```ts
const connectedPairs    = getAdjacentConnectedPairs(segments);
const unplacedConnected = getUnplacedConnectedPairs(unplacedInstructions, unplacedData);
```

(`unplacedInstructions` and `unplacedData` are already computed in the component.)

### B. Add `pairedDragType` state

```ts
const [pairedDragType, setPairedDragType] = useState<SourceType | null>(null);
```

### C. `handleDragStart` — detect paired drag

```ts
const drag = event.active.data.current as SelectedBlock;
setIsDragging(true);
setActiveDrag(drag);
if (drag.kind === "source") {
  const hasCanvasPair = connectedPairs.has(drag.sourceType);
  const hasTrayPair   = unplacedConnected.has(drag.sourceType);
  setPairedDragType(hasCanvasPair || hasTrayPair ? drag.sourceType : null);
} else {
  setPairedDragType(null);
}
```

### D. `handleDragEnd` — compound move

```ts
const drag = active.data.current as SelectedBlock;

// Remove source (and its paired data if applicable)
let withoutChip = segments.filter(s => !segmentMatchesDrag(s, drag));
if (pairedDragType && drag.kind === "source") {
  withoutChip = withoutChip.filter(
    s => !(s.kind === "source_data" && s.sourceType === pairedDragType)
  );
}

if (overId === "unplaced-tray") {
  onSegmentsChange(withoutChip); // data block stays unplaced naturally (wasn't in segments or was removed)
  setIsDragging(false);
  setActiveDrag(null);
  setPairedDragType(null);
  setNearestDropIndex(null);
  return;
}

if (overId.startsWith("drop-")) {
  const dropIndex = parseInt(overId.slice(5), 10);
  const originalIndex = segments.findIndex(s => segmentMatchesDrag(s, drag));
  const adjustedIndex =
    originalIndex !== -1 && originalIndex < dropIndex ? dropIndex - 1 : dropIndex;

  const inserted: CanvasSegment[] = [
    ...withoutChip.slice(0, adjustedIndex),
    dragToSegment(drag),
    ...(pairedDragType && drag.kind === "source"
      ? [{ kind: "source_data" as const, sourceType: pairedDragType }]
      : []),
    ...withoutChip.slice(adjustedIndex),
  ];
  onSegmentsChange(inserted);
}

setIsDragging(false);
setActiveDrag(null);
setPairedDragType(null);
setNearestDropIndex(null);
```

Also add `onDragCancel` to `DndContext`:
```ts
const handleDragCancel = () => {
  setIsDragging(false);
  setActiveDrag(null);
  setPairedDragType(null);
  setNearestDropIndex(null);
};
```

### E. Pass `isChainLink` to DropZones

In the `items.map()` render, for each `drop` item at index `i`, compute:

```ts
const prevSeg = segments[item.index - 1];
const nextSeg = segments[item.index];
const isChainLink =
  !isDragging &&
  prevSeg?.kind === "source" &&
  nextSeg?.kind === "source_data" &&
  prevSeg.sourceType === nextSeg.sourceType &&
  connectedPairs.has(prevSeg.sourceType);
```

Pass `isChainLink` to `<DropZone>`.

### F. `DragOverlay` — paired visualization

```tsx
<DragOverlay>
  {activeDrag?.kind === "source" && pairedDragType ? (
    <div className={styles.pairedOverlay}>
      <SourceChip
        sourceType={activeDrag.sourceType}
        isDirty={dirtySourceTypes.has(activeDrag.sourceType)}
        preview={sourcePreviews[activeDrag.sourceType]}
        isOverlay
      />
      <div className={styles.overlayChain}>⛓</div>
      <ReadOnlyChip block={{ kind: "source_data", sourceType: pairedDragType }} isOverlay />
    </div>
  ) : activeDrag?.kind === "source" ? (
    <SourceChip
      sourceType={activeDrag.sourceType}
      isDirty={dirtySourceTypes.has(activeDrag.sourceType)}
      preview={sourcePreviews[activeDrag.sourceType]}
      isOverlay
    />
  ) : activeDrag ? (
    <ReadOnlyChip block={activeDrag as ReadOnlyBlock} isOverlay />
  ) : null}
</DragOverlay>
```

`PromptCanvas.module.css` additions:
```css
.pairedOverlay {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.overlayChain {
  text-align: center;
  font-size: 11px;
  opacity: 0.6;
  padding: 2px 0;
}
```

---

## 4. `UnplacedTray.tsx` — Connected pairs in tray

### A. New prop

```ts
unplacedConnectedPairs: Set<SourceType>;
```

Pass this from `PromptCanvas` (already computed as `unplacedConnected`).

### B. Reorder chip rendering

```tsx
const connectedSourceTypes = unplacedInstructions.filter(st => unplacedConnectedPairs.has(st));
const lonelyInstructions   = unplacedInstructions.filter(st => !unplacedConnectedPairs.has(st));
const lonelyDataBlocks     = unplacedReadOnly.filter(
  b => !(b.kind === "source_data" && unplacedConnectedPairs.has((b as SourceDataSegment).sourceType))
);

// Render:
{connectedSourceTypes.map(st => (
  <React.Fragment key={`pair-${st}`}>
    <SourceChip
      sourceType={st}
      isDirty={dirtySourceTypes.has(st)}
      isSelected={selectedBlock?.kind === "source" && selectedBlock.sourceType === st}
      compact
      onClick={() => onSelectBlock({ kind: "source", sourceType: st })}
    />
    <span className={styles.chainLink}>⛓</span>
    <ReadOnlyChip
      block={{ kind: "source_data", sourceType: st }}
      isSelected={isReadOnlyBlockSelected({ kind: "source_data", sourceType: st }, selectedBlock)}
      compact
      onClick={() => onSelectBlock({ kind: "source_data", sourceType: st })}
    />
  </React.Fragment>
))}
{lonelyInstructions.map(st => (
  <SourceChip key={`instr-${st}`} ... />
))}
{lonelyDataBlocks.map(block => (
  <ReadOnlyChip key={...} ... />
))}
```

`UnplacedTray.module.css` addition:
```css
.chainLink {
  font-size: 11px;
  opacity: 0.5;
  align-self: center;
  margin: 0 -2px;
}
```

---

## File Change Summary

| File | Change |
|------|--------|
| `frontend/src/utils/parsePrompt.ts` | Add `getAdjacentConnectedPairs`, `getUnplacedConnectedPairs` |
| `frontend/src/components/prompts/PromptCanvas.tsx` | `pairedDragType` state; compound drag start/end/cancel; `isChainLink` on DropZones; paired DragOverlay |
| `frontend/src/components/prompts/PromptCanvas.module.css` | Add `.pairedOverlay`, `.overlayChain` |
| `frontend/src/components/prompts/DropZone.tsx` | Add `isChainLink` prop; render chain icon when not dragging |
| `frontend/src/components/prompts/DropZone.module.css` | Add `.chainLink` style |
| `frontend/src/components/prompts/UnplacedTray.tsx` | Add `unplacedConnectedPairs` prop; render connected pairs adjacent with chain link |
| `frontend/src/components/prompts/UnplacedTray.module.css` | Add `.chainLink` style |

---

## Key Design Decisions

- **Disconnection is implicit**: no explicit disconnect button. Dragging the data block to a
  non-adjacent position breaks the pair since `getAdjacentConnectedPairs` recomputes from segment
  order on every render.
- **Only source carries data**: dragging the data block independently is the disconnect gesture.
  Dragging the source brings data along.
- **Drop zone between connected chips is still droppable**: dropping a text block between them
  disconnects the pair by inserting between them.
- **Tray pairs auto-detect**: both blocks being unplaced is sufficient; no canvas adjacency needed.
- **Pairing covers canvas + tray origins**: `handleDragStart` checks both `connectedPairs` (canvas)
  and `unplacedConnected` (tray) so paired drag works regardless of where the source started.
