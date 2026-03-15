// src/pages/Tasks.tsx
import { useState } from "react";
import { useTasks } from "../api/useTasks";
import Topbar from "../components/layout/Topbar";
import KanbanBoard from "../components/tasks/KanbanBoard";
import styles from "./Tasks.module.css";

export default function Tasks() {
  const [showCreateModal, setShowCreateModal] = useState(false);

  const {
    data: tasks = [],
    isLoading,
    isError,
    refetch,
  } = useTasks({
    status: ["todo", "in_progress", "blocked", "done"],
  });

  return (
    <div className={styles.page}>
      <Topbar tasks={tasks} onNewTask={() => setShowCreateModal(true)} />

      {isError && (
        <div className={styles.errorBanner}>
          Failed to load tasks —{" "}
          <button className={styles.retryBtn} onClick={() => refetch()}>
            retry
          </button>
        </div>
      )}

      <div className={`${styles.boardWrapper} ${isLoading ? styles.loading : ""}`}>
        <KanbanBoard
          tasks={tasks}
          showCreateModal={showCreateModal}
          onCloseCreateModal={() => setShowCreateModal(false)}
        />
      </div>
    </div>
  );
}
