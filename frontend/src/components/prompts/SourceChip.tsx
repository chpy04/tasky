import { useDraggable } from "@dnd-kit/core";
import clsx from "clsx";
import { SOURCE_DISPLAY, type SourceType } from "../../utils/parsePrompt";
import SourceIcon from "./SourceIcon";
import styles from "./SourceChip.module.css";

interface SourceChipProps {
  sourceType: SourceType;
  isDirty?: boolean;
  isSelected?: boolean;
  compact?: boolean; // used in UnplacedTray
  isOverlay?: boolean; // rendered inside DragOverlay — no drag handlers needed
  preview?: string; // short content preview (canvas chips only)
  onClick?: () => void;
}

export default function SourceChip({
  sourceType,
  isDirty,
  isSelected,
  compact,
  isOverlay,
  preview,
  onClick,
}: SourceChipProps) {
  const { label, color } = SOURCE_DISPLAY[sourceType];
  const dragId = `chip-${sourceType}`;

  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: dragId,
    data: { kind: "source", sourceType },
    disabled: isOverlay,
  });

  return (
    <div
      ref={isOverlay ? undefined : setNodeRef}
      className={clsx(
        styles.chip,
        isSelected && styles.selected,
        compact && styles.compact,
        isDragging && styles.ghost,
        isOverlay && styles.dragging,
      )}
      onClick={onClick}
    >
      {/* Drag handle */}
      <span className={styles.handle} {...listeners} {...attributes} title="Drag to reorder">
        ⠿
      </span>

      {/* Icon badge */}
      <span className={styles.badge} style={{ background: color }}>
        <SourceIcon sourceType={sourceType} size={compact ? 12 : 14} />
      </span>

      {/* Label + preview */}
      <span className={styles.meta}>
        <span className={styles.label}>{label}</span>
        {!compact && preview && <span className={styles.preview}>{preview}</span>}
      </span>

      {/* Dirty dot */}
      {isDirty && <span className={styles.dirtyDot} title="Unsaved changes" />}
    </div>
  );
}
