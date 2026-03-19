// src/components/tasks/TaskCard.tsx
import { useState } from "react";
import type { Experience, Task, TaskStatus } from "../../types";
import { colors } from "../../theme";
import { formatDueDate, formatExperienceName, isDueSoon, isOverdue } from "../../utils/formatters";
import TaskDetail from "./TaskDetail";
import styles from "./TaskCard.module.css";

interface TaskCardProps {
  task: Task;
  experience: Experience | undefined;
  onEdit: (task: Task) => void;
  onComplete: (id: number) => void;
  onUncomplete: (id: number) => void;
  onStatusChange: (id: number, status: TaskStatus) => void;
}

export default function TaskCard({
  task,
  experience,
  onEdit,
  onComplete,
  onUncomplete,
  onStatusChange,
}: TaskCardProps) {
  const [expanded, setExpanded] = useState(false);
  const isDone = task.status === "done";
  const isBlocked = task.status === "blocked";
  const dueLabel = formatDueDate(task.due_at);
  const dueSoon = isDueSoon(task.due_at);
  const overdue = !isDone && isOverdue(task.due_at);
  const expName = experience ? formatExperienceName(experience.folder_path) : null;

  function handleComplete(e: React.SyntheticEvent) {
    e.stopPropagation();
    if (isDone) onUncomplete(task.id);
    else onComplete(task.id);
  }

  return (
    <div
      className={`${styles.card} ${isDone ? styles.done : ""} ${isBlocked ? styles.blocked : ""} ${overdue ? styles.overdue : ""}`}
      style={{ borderLeftColor: isBlocked || overdue ? "#c03030" : colors.borderCard }}
    >
      <div className={styles.main} onClick={() => !isDone && setExpanded((prev) => !prev)}>
        <div
          className={`${styles.check} ${isDone ? styles.checked : ""}`}
          onClick={handleComplete}
          role="checkbox"
          aria-checked={isDone}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleComplete(e);
          }}
        >
          {isDone && "✓"}
        </div>

        <div className={styles.info}>
          <div
            className={`${styles.title} ${isDone ? styles.titleDone : ""} ${expanded ? styles.titleExpanded : ""}`}
          >
            {task.title}
          </div>
          <div className={styles.metaRow}>
            {dueLabel && (
              <span
                className={`${styles.due} ${overdue ? styles.dueOverdue : dueSoon ? styles.dueSoon : ""}`}
              >
                {dueLabel}
              </span>
            )}
            {expName && <span className={styles.expBadge}>{expName}</span>}
          </div>
        </div>

        {!isDone && (
          <button
            className={`${styles.chevron} ${expanded ? styles.chevronOpen : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((prev) => !prev);
            }}
            aria-label={expanded ? "Collapse" : "Expand"}
          >
            ▾
          </button>
        )}
      </div>

      {expanded && !isDone && (
        <TaskDetail
          task={task}
          onEdit={onEdit}
          onComplete={onComplete}
          onStatusChange={onStatusChange}
        />
      )}
    </div>
  );
}
