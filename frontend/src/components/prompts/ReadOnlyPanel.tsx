import { getReadOnlyBlockMeta, type ReadOnlyBlock } from "../../utils/blockInfo";
import SourceIcon from "./SourceIcon";
import styles from "./ReadOnlyPanel.module.css";

interface ReadOnlyPanelProps {
  block: ReadOnlyBlock;
}

export default function ReadOnlyPanel({ block }: ReadOnlyPanelProps) {
  const meta = getReadOnlyBlockMeta(block);

  const icon =
    meta.iconKind === "glyph" ? (
      <span className={styles.glyph}>{meta.glyph}</span>
    ) : (
      <SourceIcon sourceType={meta.sourceType} size={15} />
    );

  return (
    <div className={styles.panel}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.badge} style={{ background: meta.color }}>
          {icon}
        </span>
        <span className={styles.title}>{meta.label}</span>
        <span className={styles.readonlyBadge}>runtime</span>
      </div>

      {/* Description */}
      <p className={styles.description}>{meta.description}</p>

      {/* Marker reference */}
      <div className={styles.markerRow}>
        <span className={styles.markerLabel}>Marker</span>
        <code className={styles.marker}>{meta.markerText}</code>
      </div>

      <p className={styles.hint}>
        This block is injected at runtime and cannot be edited here. Drag it to reposition it within
        the prompt, or drag it to the Unplaced tray to exclude it entirely.
      </p>
    </div>
  );
}
