// src/components/tasks/TaskDetail.tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import rehypeRaw from "rehype-raw";
import type { Task, TaskStatus } from "../../types";
import styles from "./TaskDetail.module.css";

function applyHighlight(text: string): string {
  return text.replace(/==(.+?)==/g, "<mark>$1</mark>");
}

interface TaskDetailProps {
  task: Task;
  onEdit: (task: Task) => void;
  onComplete: (id: number) => void;
  onStatusChange: (id: number, status: TaskStatus) => void;
}

export default function TaskDetail({ task, onEdit, onComplete, onStatusChange }: TaskDetailProps) {
  const STATUS_LABELS: Record<string, string> = {
    todo: "To Do",
    in_progress: "In Progress",
    blocked: "Blocked",
    done: "Done",
    cancelled: "Cancelled",
  };

  return (
    <div className={styles.detail}>
      <div className={styles.metaRow}>
        <span className={`${styles.statusTag} ${styles[`status_${task.status}`]}`}>
          {STATUS_LABELS[task.status] ?? task.status}
        </span>
      </div>
      {task.description && (
        <div className={styles.desc}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkBreaks]}
            rehypePlugins={[rehypeRaw]}
            components={{
              a: ({ ...props }) => <a target="_blank" rel="noopener noreferrer" {...props} />,
            }}
          >
            {applyHighlight(task.description)}
          </ReactMarkdown>
        </div>
      )}

      {task.external_ref && (
        <div className={styles.row}>
          <span className={styles.rowLabel}>Source</span>
          <span className={styles.rowVal}>{task.external_ref}</span>
        </div>
      )}

      <div className={styles.actions}>
        <button className={styles.btn} onClick={() => onEdit(task)}>
          Edit
        </button>

        {task.status === "blocked" && (
          <button className={styles.btn} onClick={() => onStatusChange(task.id, "todo")}>
            Unblock
          </button>
        )}

        {task.status !== "done" && (
          <button
            className={`${styles.btn} ${styles.btnPrimary}`}
            onClick={() => onComplete(task.id)}
          >
            Mark done
          </button>
        )}
      </div>
    </div>
  );
}
