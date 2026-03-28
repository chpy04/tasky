import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import styles from "./TextSegment.module.css";

interface TextSegmentProps {
  id: string;
  content: string;
  isEditing: boolean;
  onFocus: () => void;
  onChange: (content: string) => void;
  onBlur: () => void;
  onDeleteRequest?: () => void;
  onSplitRequest?: (before: string, after: string) => void;
}

export default function TextSegment({
  content,
  isEditing,
  onFocus,
  onChange,
  onBlur,
  onDeleteRequest,
  onSplitRequest,
}: TextSegmentProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // When entering edit mode: seed value, focus, resize
  useEffect(() => {
    if (!isEditing) return;
    const el = textareaRef.current;
    if (!el) return;
    el.value = content;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
    el.focus();
    el.setSelectionRange(el.value.length, el.value.length);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditing]); // intentionally omits `content` — we only seed once on entry

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  };

  const handleBlur = () => {
    onChange(textareaRef.current?.value ?? content);
    onBlur();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Backspace" && textareaRef.current?.value === "") {
      e.preventDefault();
      onDeleteRequest?.();
      return;
    }
    if (e.key === "Enter") {
      const el = textareaRef.current;
      if (!el) return;
      const pos = el.selectionStart;
      // Second Enter: char just before cursor is already a newline → split into new block
      if (pos > 0 && el.value[pos - 1] === "\n") {
        e.preventDefault();
        const before = el.value.slice(0, pos - 1); // strip the trailing \n
        const after = el.value.slice(pos);
        onSplitRequest?.(before, after);
      }
    }
  };

  if (isEditing) {
    return (
      <textarea
        ref={textareaRef}
        className={styles.textarea}
        defaultValue={content}
        onChange={handleInput}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        spellCheck={false}
      />
    );
  }

  return (
    <div className={styles.text} onClick={onFocus} title="Click to edit">
      {content ? (
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      ) : (
        <span className={styles.placeholder}>Click to edit…</span>
      )}
    </div>
  );
}
