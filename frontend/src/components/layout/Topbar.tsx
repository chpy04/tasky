// src/components/layout/Topbar.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Task } from "../../types";
import { usePendingProposalCount } from "../../api/useProposals";
import { useSyncPipelineWithPolling } from "../../api/useIngestion";
import styles from "./Topbar.module.css";

interface TopbarProps {
  tasks: Task[];
  onNewTask: () => void;
}

function LogoCup() {
  return (
    <svg className={styles.logoCup} viewBox="0 0 30 30" fill="none">
      <path d="M6 10h18l-2 12H8L6 10z" stroke="#5a3e22" strokeWidth="1" fill="#1e1208" />
      <path
        d="M20 10c0 0 3 0 3 3s-3 3-3 3"
        stroke="#5a3e22"
        strokeWidth="1"
        fill="none"
        strokeLinecap="round"
      />
      <path
        d="M8 7c0 0 1-2 3-2s2 3 4 3 2-3 4-3"
        stroke="#3a2210"
        strokeWidth="1"
        fill="none"
        strokeLinecap="round"
      />
      <ellipse cx="14" cy="13" rx="4" ry="1.5" fill="#2e1a08" />
      <path d="M9 13c1 1 3 2 5 2s4-1 5-2" stroke="#3a2210" strokeWidth="0.75" fill="none" />
    </svg>
  );
}

export default function Topbar({ tasks, onNewTask }: TopbarProps) {
  const navigate = useNavigate();
  const pendingProposals = usePendingProposalCount();
  const { trigger, isRunning, run, error } = useSyncPipelineWithPolling();
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  // Detect run status transitions during render (React recommended pattern
  // for adjusting state when props/derived data change).
  const [prevRunStatus, setPrevRunStatus] = useState<string | null>(null);
  const currentRunStatus = run?.status ?? null;
  if (currentRunStatus !== prevRunStatus) {
    setPrevRunStatus(currentRunStatus);
    if (currentRunStatus === "failed") {
      setSyncMessage("sync failed");
    } else if (currentRunStatus === "completed") {
      const count = run!.proposal_count;
      setSyncMessage(`+${count} proposal${count !== 1 ? "s" : ""}`);
    }
  }

  // Detect trigger errors during render.
  const [prevError, setPrevError] = useState<Error | null>(null);
  if (error !== prevError) {
    setPrevError(error);
    if (error) {
      setSyncMessage("sync failed");
    }
  }

  // Auto-dismiss sync message after 4 seconds.
  useEffect(() => {
    if (!syncMessage) return;
    const t = setTimeout(() => setSyncMessage(null), 10000);
    return () => clearTimeout(t);
  }, [syncMessage]);

  async function handleSync() {
    setSyncMessage(null);
    await trigger();
  }

  const openCount = tasks.filter((t) =>
    ["todo", "in_progress", "blocked"].includes(t.status),
  ).length;
  const inProgressCount = tasks.filter((t) => t.status === "in_progress").length;

  return (
    <div className={styles.topbar}>
      <div className={styles.left}>
        <div className={styles.logoLockup}>
          <LogoCup />
          <div className={styles.logoText}>
            <div className={styles.logoMain}>Tasky</div>
            <div className={styles.logoSub}>est. 2026</div>
          </div>
        </div>

        <div className={styles.divider} />

        <div className={styles.stat}>
          <div className={styles.statNum}>{openCount}</div>
          <div className={styles.statLabel}>Open</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statNum}>{inProgressCount}</div>
          <div className={styles.statLabel}>In progress</div>
        </div>
      </div>

      <div className={styles.right}>
        <button
          className={styles.syncBtn}
          onClick={handleSync}
          disabled={isRunning}
          title="Ingest from last sync to now and generate proposals"
        >
          {isRunning ? (
            <span className={styles.syncSpinner} />
          ) : (
            <span className={styles.syncIcon}>↻</span>
          )}
          {isRunning ? "Syncing…" : (syncMessage ?? "Sync")}
        </button>
        <button className={styles.aiPill} onClick={() => navigate("/proposals")}>
          <span className={styles.aiDot} />
          {pendingProposals} proposal{pendingProposals !== 1 ? "s" : ""} to review
        </button>
        <button className={styles.addTaskBtn} onClick={onNewTask}>
          + New task
        </button>
      </div>
    </div>
  );
}
