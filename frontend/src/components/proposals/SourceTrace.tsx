import type { TaskProposal } from "../../types";
import styles from "./SourceTrace.module.css";

const SOURCE_COLOR: Record<string, string> = {
  slack: "#4a9eff",
  github: "#e8c070",
  gmail: "#8a7058",
  email: "#8a7058",
  canvas: "#4caf50",
};

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return (
    d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) +
    " at " +
    d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  );
}

interface SourceTraceProps {
  proposal: TaskProposal;
}

export function SourceTrace({ proposal }: SourceTraceProps) {
  const batch = proposal.ingestion_batch;
  const run = batch?.ingestion_run ?? null;

  if (!batch && !run) {
    return (
      <div className={styles.trace}>
        <div className={styles.row}>
          <span className={styles.label}>Source</span>
          <span className={styles.value}>created manually</span>
        </div>
      </div>
    );
  }

  const sourceType = batch?.source_type ?? null;
  const color = sourceType ? (SOURCE_COLOR[sourceType] ?? "#8a7058") : "#8a7058";

  return (
    <div className={styles.trace}>
      {sourceType && (
        <div className={styles.row}>
          <span className={styles.label}>Source</span>
          <span className={styles.sourceTag} style={{ color, borderColor: color }}>
            {sourceType}
          </span>
          {batch && (
            <span className={styles.value}>
              batch #{batch.id}
              {batch.item_count !== null && <> &bull; {batch.item_count} items</>}
            </span>
          )}
        </div>
      )}
      {run && (
        <div className={styles.row}>
          <span className={styles.label}>Run</span>
          <span className={styles.value}>
            #{run.id}
            &nbsp;&bull;&nbsp;
            <span className={`${styles.runStatus} ${run.status === "completed" ? styles.ok : ""}`}>
              {run.status}
            </span>
            &nbsp;&bull;&nbsp;
            {run.triggered_by}
            &nbsp;&bull;&nbsp;
            {formatDateTime(run.started_at)}
          </span>
        </div>
      )}
    </div>
  );
}
