import { useEffect, useRef } from "react";
import { SOURCE_DISPLAY, type SourceType } from "../../utils/parsePrompt";
import SourceIcon from "./SourceIcon";
import styles from "./SourceEditor.module.css";

export interface SourceDraft {
  content: string;
  description: string;
  savedContent: string;
  savedDescription: string;
}

interface SourceEditorProps {
  selectedSource: SourceType | null;
  drafts: Record<string, SourceDraft>;
  onContentChange: (st: SourceType, content: string) => void;
  onDescriptionChange: (st: SourceType, description: string) => void;
}

export default function SourceEditor({
  selectedSource,
  drafts,
  onContentChange,
  onDescriptionChange,
}: SourceEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [selectedSource, drafts]);

  if (!selectedSource) {
    return (
      <div className={styles.empty}>
        <span className={styles.emptyText}>Click a source block to edit its prompt content.</span>
      </div>
    );
  }

  const { label, color } = SOURCE_DISPLAY[selectedSource];
  const draft = drafts[selectedSource];
  const isDirty = draft
    ? draft.content !== draft.savedContent || draft.description !== draft.savedDescription
    : false;

  return (
    <div className={styles.editor}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.badge} style={{ background: color }}>
          <SourceIcon sourceType={selectedSource} size={15} />
        </span>
        <span className={styles.title}>{label}</span>
        {isDirty && <span className={styles.dirtyBadge}>•</span>}
      </div>

      {/* Description */}
      <div className={styles.field}>
        <label className={styles.fieldLabel}>Description</label>
        <input
          className={styles.descInput}
          value={draft?.description ?? ""}
          onChange={(e) => onDescriptionChange(selectedSource, e.target.value)}
          placeholder="Briefly describe what this source context does…"
          spellCheck={false}
        />
      </div>

      {/* Content */}
      <div className={styles.field}>
        <label className={styles.fieldLabel}>Content</label>
        <textarea
          ref={textareaRef}
          className={styles.contentTextarea}
          value={draft?.content ?? ""}
          onChange={(e) => onContentChange(selectedSource, e.target.value)}
          spellCheck={false}
        />
      </div>
    </div>
  );
}
