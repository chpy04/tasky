import { useCallback, useEffect, useState } from "react";
import { type Prompt, useUpdatePrompt } from "../../api/usePrompts";
import { serializeSegments, type SelectedBlock } from "../../utils/parsePrompt";
import { useSourceDrafts } from "./useSourceDrafts";
import { useSystemPromptCanvas } from "./useSystemPromptCanvas";
import PromptCanvas from "./PromptCanvas";
import ReadOnlyPanel from "./ReadOnlyPanel";
import SourceEditor from "./SourceEditor";
import styles from "./PromptComposer.module.css";

interface PromptComposerProps {
  systemPrompt: Prompt;
  sourcePrompts: Prompt[];
}

export default function PromptComposer({ systemPrompt, sourcePrompts }: PromptComposerProps) {
  const {
    segments,
    setSegments,
    systemDirty,
    reset: resetCanvas,
  } = useSystemPromptCanvas(systemPrompt);

  const {
    sourceDrafts,
    setSourceDrafts,
    dirtySourceTypes,
    sourcePreviews,
    markAllSaved,
    reset: resetDrafts,
  } = useSourceDrafts(sourcePrompts);

  const [selectedBlock, setSelectedBlock] = useState<SelectedBlock | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const updatePrompt = useUpdatePrompt();

  const anyDirty = systemDirty || dirtySourceTypes.size > 0;

  const handleSave = useCallback(async () => {
    if (!anyDirty) return;

    const mutations: Promise<unknown>[] = [];

    if (systemDirty) {
      mutations.push(
        updatePrompt.mutateAsync({ id: systemPrompt.id, content: serializeSegments(segments) }),
      );
    }

    for (const st of dirtySourceTypes) {
      const prompt = sourcePrompts.find((p) => p.source_type === st);
      if (!prompt) continue;
      const d = sourceDrafts[st];
      mutations.push(
        updatePrompt.mutateAsync({ id: prompt.id, content: d.content, description: d.description }),
      );
    }

    try {
      await Promise.all(mutations);
      markAllSaved();
      setSavedAt(new Date());
      updatePrompt.reset();
    } catch {
      // error is surfaced via updatePrompt.isError
    }
  }, [
    anyDirty,
    systemDirty,
    dirtySourceTypes,
    segments,
    systemPrompt.id,
    sourcePrompts,
    sourceDrafts,
    markAllSaved,
    updatePrompt,
  ]);

  const handleDiscard = useCallback(() => {
    resetCanvas();
    resetDrafts();
    updatePrompt.reset();
  }, [resetCanvas, resetDrafts, updatePrompt]);

  // Cmd+S global handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        if (anyDirty && !updatePrompt.isPending) handleSave();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [anyDirty, updatePrompt.isPending, handleSave]);

  const saveLabel = updatePrompt.isPending
    ? "Saving…"
    : updatePrompt.isError
      ? "Save failed — retry"
      : "Save";

  const selectedSource = selectedBlock?.kind === "source" ? selectedBlock.sourceType : null;
  const showReadOnlyPanel = selectedBlock !== null && selectedBlock.kind !== "source";

  return (
    <div className={styles.composer}>
      {/* Save bar */}
      <div className={`${styles.saveBar} ${anyDirty ? styles.saveBarDirty : ""}`}>
        <div className={styles.saveBarLeft}>
          {anyDirty ? <span className={styles.unsavedDot} /> : null}
          <span className={styles.saveBarStatus}>
            {updatePrompt.isPending
              ? "Saving…"
              : updatePrompt.isError
                ? "Save failed"
                : anyDirty
                  ? "Unsaved changes"
                  : savedAt
                    ? "Saved"
                    : "No changes"}
          </span>
        </div>
        <div className={styles.saveBarActions}>
          {anyDirty && (
            <button
              className={styles.discardBtn}
              onClick={handleDiscard}
              disabled={updatePrompt.isPending}
            >
              Discard
            </button>
          )}
          <button
            className={`${styles.saveBtn} ${anyDirty || updatePrompt.isError ? styles.saveBtnActive : ""}`}
            onClick={handleSave}
            disabled={updatePrompt.isPending || (!anyDirty && !updatePrompt.isError)}
          >
            {saveLabel} <kbd className={styles.kbd}>⌘S</kbd>
          </button>
        </div>
      </div>

      {/* Panels */}
      <div className={styles.panels}>
        {/* Canvas — left panel */}
        <div className={styles.canvasPanel}>
          <PromptCanvas
            segments={segments}
            selectedBlock={selectedBlock}
            dirtySourceTypes={dirtySourceTypes}
            sourcePreviews={sourcePreviews}
            onSegmentsChange={setSegments}
            onSelectBlock={setSelectedBlock}
          />
        </div>

        {/* Divider */}
        <div className={styles.divider} />

        {/* Editor — right panel */}
        <div className={styles.editorPanel}>
          {showReadOnlyPanel ? (
            <ReadOnlyPanel block={selectedBlock as Exclude<SelectedBlock, { kind: "source" }>} />
          ) : (
            <SourceEditor
              selectedSource={selectedSource}
              drafts={sourceDrafts}
              onContentChange={(st, content) =>
                setSourceDrafts((prev) => ({ ...prev, [st]: { ...prev[st], content } }))
              }
              onDescriptionChange={(st, description) =>
                setSourceDrafts((prev) => ({ ...prev, [st]: { ...prev[st], description } }))
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}
