import {
  DndContext,
  DragOverlay,
  type DragEndEvent,
  type DragMoveEvent,
  type DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { useState, useRef, useEffect } from "react";
import {
  type CanvasSegment,
  type SelectedBlock,
  type SourceType,
  getAdjacentConnectedPairs,
  getUnplacedConnectedPairs,
  getUnplacedSourceData,
  getUnplacedSources,
} from "../../utils/parsePrompt";
import { isReadOnlyBlockSelected, type ReadOnlyBlock } from "../../utils/blockInfo";
import DropZone, { type DropZoneHandle } from "./DropZone";
import ReadOnlyChip from "./ReadOnlyChip";
import SourceChip from "./SourceChip";
import TextSegment from "./TextSegment";
import UnplacedTray from "./UnplacedTray";
import styles from "./PromptCanvas.module.css";

interface PromptCanvasProps {
  segments: CanvasSegment[];
  selectedBlock: SelectedBlock | null;
  dirtySourceTypes: Set<SourceType>;
  sourcePreviews: Record<string, string>;
  onSegmentsChange: (segments: CanvasSegment[]) => void;
  onSelectBlock: (block: SelectedBlock) => void;
}

/** Returns true if the segment matches the drag payload. */
function segmentMatchesDrag(seg: CanvasSegment, drag: SelectedBlock): boolean {
  if (drag.kind === "source") return seg.kind === "source" && seg.sourceType === drag.sourceType;
  if (drag.kind === "source_data")
    return seg.kind === "source_data" && seg.sourceType === drag.sourceType;
  if (drag.kind === "experiences") return seg.kind === "experiences";
  if (drag.kind === "active_tasks") return seg.kind === "active_tasks";
  return false;
}

/** Converts a drag payload back to a CanvasSegment for insertion. */
function dragToSegment(drag: SelectedBlock): CanvasSegment {
  if (drag.kind === "source") return { kind: "source", sourceType: drag.sourceType };
  if (drag.kind === "source_data") return { kind: "source_data", sourceType: drag.sourceType };
  if (drag.kind === "experiences") return { kind: "experiences" };
  return { kind: "active_tasks" };
}

export default function PromptCanvas({
  segments,
  selectedBlock,
  dirtySourceTypes,
  sourcePreviews,
  onSegmentsChange,
  onSelectBlock,
}: PromptCanvasProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [activeDrag, setActiveDrag] = useState<SelectedBlock | null>(null);
  const [pairedDragType, setPairedDragType] = useState<SourceType | null>(null);
  const [editingSegmentId, setEditingSegmentId] = useState<string | null>(null);
  const [nearestDropIndex, setNearestDropIndex] = useState<number | null>(null);
  const dropZoneRefs = useRef<Map<number, DropZoneHandle>>(new Map());
  const rafRef = useRef<number | null>(null);

  // Cancel any pending rAF on unmount
  useEffect(
    () => () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    },
    [],
  );

  const unplacedInstructions = getUnplacedSources(segments);
  const unplacedData = getUnplacedSourceData(segments);
  const experiencePlaced = segments.some((s) => s.kind === "experiences");
  const activeTasksPlaced = segments.some((s) => s.kind === "active_tasks");
  const connectedPairs = getAdjacentConnectedPairs(segments);
  const unplacedConnected = getUnplacedConnectedPairs(unplacedInstructions, unplacedData);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const handleDragStart = (event: DragStartEvent) => {
    const drag = event.active.data.current as SelectedBlock;
    setIsDragging(true);
    setActiveDrag(drag);
    if (drag.kind === "source") {
      const hasCanvasPair = connectedPairs.has(drag.sourceType);
      const hasTrayPair = unplacedConnected.has(drag.sourceType);
      setPairedDragType(hasCanvasPair || hasTrayPair ? drag.sourceType : null);
    } else {
      setPairedDragType(null);
    }
  };

  const handleDragMove = (event: DragMoveEvent) => {
    // Capture cursor position immediately from the event (data may stale after rAF delay)
    const cursorY =
      event.activatorEvent instanceof MouseEvent
        ? event.activatorEvent.clientY + event.delta.y
        : (event.activatorEvent as TouchEvent).touches[0].clientY + event.delta.y;

    // Throttle the O(n) drop-zone scan to one update per animation frame
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      let closestIndex: number | null = null;
      let closestDist = Infinity;
      for (const [index, handle] of dropZoneRefs.current.entries()) {
        const y = handle.getY();
        if (y === null) continue;
        const dist = Math.abs(cursorY - y);
        if (dist < closestDist) {
          closestDist = dist;
          closestIndex = index;
        }
      }
      setNearestDropIndex(closestIndex);
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    const drag = active.data.current as SelectedBlock;
    const overId = over?.id as string | undefined;

    // Build new segments without the dragged chip (and its paired data if applicable)
    let withoutChip = segments.filter((s) => !segmentMatchesDrag(s, drag));
    if (pairedDragType && drag.kind === "source") {
      withoutChip = withoutChip.filter(
        (s) => !(s.kind === "source_data" && s.sourceType === pairedDragType),
      );
    }

    if (!overId) {
      setIsDragging(false);
      setActiveDrag(null);
      setPairedDragType(null);
      setNearestDropIndex(null);
      return;
    }

    if (overId === "unplaced-tray") {
      onSegmentsChange(withoutChip);
      setIsDragging(false);
      setActiveDrag(null);
      setPairedDragType(null);
      setNearestDropIndex(null);
      return;
    }

    if (overId.startsWith("drop-")) {
      const dropIndex = parseInt(overId.slice(5), 10);
      const originalIndex = segments.findIndex((s) => segmentMatchesDrag(s, drag));
      const adjustedIndex =
        originalIndex !== -1 && originalIndex < dropIndex ? dropIndex - 1 : dropIndex;
      const inserted = [
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
  };

  const handleDragCancel = () => {
    setIsDragging(false);
    setActiveDrag(null);
    setPairedDragType(null);
    setNearestDropIndex(null);
  };

  const handleTextChange = (id: string, content: string) => {
    onSegmentsChange(
      segments.map((s) => (s.kind === "text" && s.id === id ? { ...s, content } : s)),
    );
  };

  const handleDeleteSegment = (id: string) => {
    setEditingSegmentId(null);
    onSegmentsChange(segments.filter((s) => !(s.kind === "text" && s.id === id)));
  };

  const handleSplitSegment = (id: string, before: string, after: string) => {
    const newId = `t${crypto.randomUUID()}`;
    const newSegments = segments.flatMap((s) => {
      if (s.kind !== "text" || s.id !== id) return [s];
      const updated = { ...s, content: before };
      const fresh = { kind: "text" as const, id: newId, content: after };
      return [updated, fresh];
    });
    onSegmentsChange(newSegments);
    setEditingSegmentId(newId);
  };

  // Drop zones: one before each segment + one at the end
  const items: Array<
    { type: "drop"; index: number } | { type: "segment"; seg: CanvasSegment; segIndex: number }
  > = [];
  for (let i = 0; i <= segments.length; i++) {
    items.push({ type: "drop", index: i });
    if (i < segments.length) {
      items.push({ type: "segment", seg: segments[i], segIndex: i });
    }
  }

  return (
    <DndContext
      sensors={sensors}
      autoScroll={false}
      onDragStart={handleDragStart}
      onDragMove={handleDragMove}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div className={styles.canvas}>
        {items.map((item) => {
          if (item.type === "drop") {
            const prevSeg = segments[item.index - 1];
            const nextSeg = segments[item.index];
            const isChainLink =
              !isDragging &&
              prevSeg?.kind === "source" &&
              nextSeg?.kind === "source_data" &&
              prevSeg.sourceType === nextSeg.sourceType &&
              connectedPairs.has(prevSeg.sourceType);
            return (
              <DropZone
                key={`drop-${item.index}`}
                id={`drop-${item.index}`}
                isNearest={isDragging && nearestDropIndex === item.index}
                isChainLink={isChainLink}
                ref={(handle) => {
                  if (handle) dropZoneRefs.current.set(item.index, handle);
                  else dropZoneRefs.current.delete(item.index);
                }}
              />
            );
          }

          const { seg, segIndex } = item;

          if (seg.kind === "text") {
            return (
              <TextSegment
                key={seg.id}
                id={seg.id}
                content={seg.content}
                isEditing={editingSegmentId === seg.id}
                onFocus={() => setEditingSegmentId(seg.id)}
                onChange={(content) => handleTextChange(seg.id, content)}
                onBlur={() => setEditingSegmentId(null)}
                onDeleteRequest={() => handleDeleteSegment(seg.id)}
                onSplitRequest={(before, after) => handleSplitSegment(seg.id, before, after)}
              />
            );
          }

          if (seg.kind === "source") {
            return (
              <SourceChip
                key={`${seg.sourceType}-${segIndex}`}
                sourceType={seg.sourceType}
                isDirty={dirtySourceTypes.has(seg.sourceType)}
                isSelected={
                  selectedBlock?.kind === "source" && selectedBlock.sourceType === seg.sourceType
                }
                preview={sourcePreviews[seg.sourceType]}
                onClick={() => onSelectBlock({ kind: "source", sourceType: seg.sourceType })}
              />
            );
          }

          // read-only block (experiences, active_tasks, source_data)
          const roBlock: ReadOnlyBlock = seg as ReadOnlyBlock;
          const connectedAbove =
            seg.kind === "source_data" &&
            segIndex > 0 &&
            segments[segIndex - 1]?.kind === "source" &&
            (segments[segIndex - 1] as { kind: "source"; sourceType: SourceType }).sourceType ===
              seg.sourceType &&
            connectedPairs.has(seg.sourceType);

          return (
            <ReadOnlyChip
              key={`ro-${seg.kind === "source_data" ? `${seg.kind}-${seg.sourceType}` : seg.kind}-${segIndex}`}
              block={roBlock}
              isSelected={isReadOnlyBlockSelected(roBlock, selectedBlock)}
              connectedTop={connectedAbove}
              onClick={() => onSelectBlock(roBlock)}
            />
          );
        })}

        <UnplacedTray
          unplacedInstructions={unplacedInstructions}
          unplacedData={unplacedData}
          experiencePlaced={experiencePlaced}
          activeTasksPlaced={activeTasksPlaced}
          selectedBlock={selectedBlock}
          dirtySourceTypes={dirtySourceTypes}
          isDragging={isDragging}
          unplacedConnectedPairs={unplacedConnected}
          onSelectBlock={onSelectBlock}
        />
      </div>

      <DragOverlay>
        {activeDrag?.kind === "source" && pairedDragType ? (
          <div className={styles.pairedOverlay}>
            <SourceChip
              sourceType={activeDrag.sourceType}
              isDirty={dirtySourceTypes.has(activeDrag.sourceType)}
              preview={sourcePreviews[activeDrag.sourceType]}
              isOverlay
            />
            <ReadOnlyChip
              block={{ kind: "source_data", sourceType: pairedDragType }}
              connectedTop
              isOverlay
            />
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
    </DndContext>
  );
}
