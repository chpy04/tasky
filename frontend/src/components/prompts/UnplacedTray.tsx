import { useDroppable } from "@dnd-kit/core";
import clsx from "clsx";
import React from "react";
import { isReadOnlyBlockSelected, type ReadOnlyBlock } from "../../utils/blockInfo";
import { type SelectedBlock, type SourceType } from "../../utils/parsePrompt";
import ReadOnlyChip from "./ReadOnlyChip";
import SourceChip from "./SourceChip";
import styles from "./UnplacedTray.module.css";

interface UnplacedTrayProps {
  unplacedInstructions: SourceType[];
  unplacedData: SourceType[];
  experiencePlaced: boolean;
  activeTasksPlaced: boolean;
  selectedBlock: SelectedBlock | null;
  dirtySourceTypes: Set<SourceType>;
  isDragging: boolean;
  unplacedConnectedPairs: Set<SourceType>;
  onSelectBlock: (block: SelectedBlock) => void;
}

export default function UnplacedTray({
  unplacedInstructions,
  unplacedData,
  experiencePlaced,
  activeTasksPlaced,
  selectedBlock,
  dirtySourceTypes,
  isDragging,
  unplacedConnectedPairs,
  onSelectBlock,
}: UnplacedTrayProps) {
  const { setNodeRef, isOver } = useDroppable({ id: "unplaced-tray" });

  const unplacedReadOnly: ReadOnlyBlock[] = [];
  if (!experiencePlaced) unplacedReadOnly.push({ kind: "experiences" });
  if (!activeTasksPlaced) unplacedReadOnly.push({ kind: "active_tasks" });
  for (const st of unplacedData) unplacedReadOnly.push({ kind: "source_data", sourceType: st });

  const connectedSourceTypes = unplacedInstructions.filter((st) => unplacedConnectedPairs.has(st));
  const lonelyInstructions = unplacedInstructions.filter((st) => !unplacedConnectedPairs.has(st));
  const lonelyDataBlocks = unplacedReadOnly.filter(
    (b) =>
      !(
        b.kind === "source_data" &&
        unplacedConnectedPairs.has(
          (b as { kind: "source_data"; sourceType: SourceType }).sourceType,
        )
      ),
  );

  const isEmpty = unplacedInstructions.length === 0 && unplacedReadOnly.length === 0;

  return (
    <div
      ref={setNodeRef}
      className={clsx(styles.tray, isDragging && styles.dragging, isOver && styles.over)}
    >
      <span className={styles.label}>Unplaced</span>
      <div className={styles.chips}>
        {connectedSourceTypes.map((st) => (
          <React.Fragment key={`pair-${st}`}>
            <SourceChip
              sourceType={st}
              isDirty={dirtySourceTypes.has(st)}
              isSelected={selectedBlock?.kind === "source" && selectedBlock.sourceType === st}
              compact
              onClick={() => onSelectBlock({ kind: "source", sourceType: st })}
            />
            <ReadOnlyChip
              block={{ kind: "source_data", sourceType: st }}
              isSelected={isReadOnlyBlockSelected(
                { kind: "source_data", sourceType: st },
                selectedBlock,
              )}
              compact
              connectedLeft
              onClick={() => onSelectBlock({ kind: "source_data", sourceType: st })}
            />
          </React.Fragment>
        ))}
        {lonelyInstructions.map((st) => (
          <SourceChip
            key={`instr-${st}`}
            sourceType={st}
            isDirty={dirtySourceTypes.has(st)}
            isSelected={selectedBlock?.kind === "source" && selectedBlock.sourceType === st}
            compact
            onClick={() => onSelectBlock({ kind: "source", sourceType: st })}
          />
        ))}
        {lonelyDataBlocks.map((block) => {
          const key = block.kind === "source_data" ? `data-${block.sourceType}` : block.kind;
          return (
            <ReadOnlyChip
              key={key}
              block={block}
              isSelected={isReadOnlyBlockSelected(block, selectedBlock)}
              compact
              onClick={() => onSelectBlock(block)}
            />
          );
        })}
        {isEmpty && <span className={styles.empty}>All blocks placed in canvas</span>}
      </div>
    </div>
  );
}
