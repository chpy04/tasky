// src/components/tasks/TaskColumn.tsx
import type { Experience, Task, TaskStatus } from "../../types";
import TaskCard from "./TaskCard";
import styles from "./TaskColumn.module.css";

interface ColumnConfig {
  title: string;
  headerIcon: React.ReactNode;
  watermark: React.ReactNode;
}

export const COLUMN_CONFIG: Record<string, ColumnConfig> = {
  in_progress: {
    title: "In Progress",
    headerIcon: (
      <svg className={styles.colIcon} viewBox="0 0 18 18" fill="none">
        <circle cx="9" cy="9" r="7" stroke="#5a3e22" strokeWidth="1" />
        <path d="M9 5v4l3 2" stroke="#5a3e22" strokeWidth="1" strokeLinecap="round" />
      </svg>
    ),
    watermark: (
      <svg className={styles.watermark} width="60" height="60" viewBox="0 0 60 60" fill="none">
        <circle cx="30" cy="30" r="28" stroke="white" strokeWidth="1.5" />
        <circle cx="30" cy="30" r="18" stroke="white" strokeWidth="1" />
        <circle cx="30" cy="30" r="8" stroke="white" strokeWidth="0.75" />
        <path d="M30 2 Q32 20 30 30 Q28 20 30 2" fill="white" opacity="0.5" />
      </svg>
    ),
  },
  todo: {
    title: "To Do",
    headerIcon: (
      <svg className={styles.colIcon} viewBox="0 0 18 18" fill="none">
        <rect x="2" y="2" width="14" height="14" rx="1" stroke="#5a3e22" strokeWidth="1" />
        <path d="M5 9h8M5 6h8M5 12h5" stroke="#5a3e22" strokeWidth="1" strokeLinecap="round" />
      </svg>
    ),
    watermark: (
      <svg className={styles.watermark} width="60" height="60" viewBox="0 0 60 60" fill="none">
        <path d="M10 50 Q20 20 30 15 Q40 10 50 20" stroke="white" strokeWidth="1.5" fill="none" />
        <path d="M10 50 Q18 35 28 30 Q38 25 48 35" stroke="white" strokeWidth="1" fill="none" />
        <circle cx="30" cy="15" r="3" stroke="white" strokeWidth="1" />
      </svg>
    ),
  },
  done: {
    title: "Completed",
    headerIcon: (
      <svg className={styles.colIcon} viewBox="0 0 18 18" fill="none">
        <circle cx="9" cy="9" r="7" stroke="#5a3e22" strokeWidth="1" />
        <path
          d="M5.5 9l2.5 2.5 4.5-4.5"
          stroke="#5a3e22"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
    watermark: (
      <svg className={styles.watermark} width="60" height="60" viewBox="0 0 60 60" fill="none">
        <circle cx="30" cy="30" r="26" stroke="white" strokeWidth="1.5" fill="none" />
        <path
          d="M16 30l10 10 18-18"
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
};

interface TaskColumnProps {
  status: TaskStatus;
  activeTasks: Task[]; // non-done tasks for this column
  doneTasks: Task[]; // done tasks (already filtered to today)
  experiences: Experience[];
  onEdit: (task: Task) => void;
  onComplete: (id: number) => void;
  onUncomplete: (id: number) => void;
  onStatusChange: (id: number, status: TaskStatus) => void;
}

export default function TaskColumn({
  status,
  activeTasks,
  doneTasks,
  experiences,
  onEdit,
  onComplete,
  onUncomplete,
  onStatusChange,
}: TaskColumnProps) {
  const config = COLUMN_CONFIG[status];
  if (!config) return null;

  const expById = Object.fromEntries(experiences.map((e) => [e.id, e]));

  return (
    <div className={styles.col}>
      <div className={styles.header}>
        {config.headerIcon}
        <div className={styles.headerTitle}>{config.title}</div>
        <div className={styles.headerCount}>{activeTasks.length}</div>
      </div>

      <div className={styles.body}>
        {activeTasks.length === 0 && doneTasks.length === 0 && (
          <div className={styles.empty}>No tasks</div>
        )}

        {activeTasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            experience={task.experience_id != null ? expById[task.experience_id] : undefined}
            onEdit={onEdit}
            onComplete={onComplete}
            onUncomplete={onUncomplete}
            onStatusChange={onStatusChange}
          />
        ))}

        {doneTasks.length > 0 && (
          <>
            <div className={styles.doneDivider}>Completed today</div>
            {doneTasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                experience={task.experience_id != null ? expById[task.experience_id] : undefined}
                onEdit={onEdit}
                onComplete={onComplete}
                onUncomplete={onUncomplete}
                onStatusChange={onStatusChange}
              />
            ))}
          </>
        )}
      </div>

      {config.watermark}
    </div>
  );
}
