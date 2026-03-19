import { useDraggable } from "@dnd-kit/core";
import clsx from "clsx";
import { getReadOnlyBlockMeta, type ReadOnlyBlock } from "../../utils/blockInfo";
import SourceIcon from "./SourceIcon";
import styles from "./ReadOnlyChip.module.css";

export type { ReadOnlyBlock };

interface ReadOnlyChipProps {
  block: ReadOnlyBlock;
  isSelected?: boolean;
  compact?: boolean;
  isOverlay?: boolean;
  connectedTop?: boolean; // indents + slightly shrinks when linked to source above (canvas)
  connectedLeft?: boolean; // slightly shrinks when linked to source beside (tray)
  onClick?: () => void;
}

export default function ReadOnlyChip({
  block,
  isSelected,
  compact,
  isOverlay,
  connectedTop,
  connectedLeft,
  onClick,
}: ReadOnlyChipProps) {
  const meta = getReadOnlyBlockMeta(block);

  const icon =
    meta.iconKind === "glyph" ? (
      <span className={styles.glyph}>{meta.glyph}</span>
    ) : (
      <SourceIcon sourceType={meta.sourceType} size={compact ? 12 : 14} />
    );

  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: meta.dragId,
    data: block,
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
        connectedTop && styles.connectedTop,
        connectedLeft && styles.connectedLeft,
      )}
      onClick={onClick}
    >
      {/* Drag handle */}
      <span className={styles.handle} {...listeners} {...attributes} title="Drag to reorder">
        ⠿
      </span>

      {/* Icon badge */}
      <span className={styles.badge} style={{ background: meta.color }}>
        {icon}
      </span>

      {/* Label */}
      <span className={styles.meta}>
        <span className={styles.label}>{meta.label}</span>
      </span>

      {/* Read-only indicator */}
      <span className={styles.lockDot} title="Runtime data — not editable">
        ⊙
      </span>
    </div>
  );
}
