import type { TaskProposal, TaskStatus } from "../../types";
import styles from "./ProposalDiff.module.css";

const STATUS_COLOR: Record<TaskStatus, string> = {
  todo: "#8a7058",
  in_progress: "#4a9eff",
  blocked: "#ff4444",
  done: "#4caf50",
  cancelled: "#5a3e22",
};

function StatusPill({ status }: { status: TaskStatus }) {
  return (
    <span
      className={styles.statusPill}
      style={{ color: STATUS_COLOR[status], borderColor: STATUS_COLOR[status] }}
    >
      {status.replace("_", " ")}
    </span>
  );
}

interface DiffRow {
  field: string;
  current: React.ReactNode;
  proposed: React.ReactNode;
  changed: boolean;
}

interface ProposalDiffProps {
  proposal: TaskProposal;
}

export function ProposalDiff({ proposal }: ProposalDiffProps) {
  const { proposal_type, task } = proposal;

  if (proposal_type === "cancel_task") {
    return (
      <div className={styles.cancelWarning}>
        <span className={styles.cancelIcon}>!</span>
        <div>
          <div className={styles.cancelTitle}>This task will be cancelled</div>
          {task && <div className={styles.cancelTask}>{task.title}</div>}
        </div>
      </div>
    );
  }

  if (proposal_type === "create_task") {
    const fields: { label: string; value: React.ReactNode }[] = [];
    if (proposal.proposed_title) fields.push({ label: "title", value: proposal.proposed_title });
    if (proposal.proposed_description)
      fields.push({ label: "description", value: proposal.proposed_description });
    if (proposal.proposed_status)
      fields.push({ label: "status", value: <StatusPill status={proposal.proposed_status} /> });
    if (proposal.proposed_due_at)
      fields.push({
        label: "due",
        value: new Date(proposal.proposed_due_at).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        }),
      });
    if (proposal.proposed_external_ref)
      fields.push({ label: "ref", value: proposal.proposed_external_ref });

    return (
      <div className={styles.createCard}>
        <div className={styles.createHeader}>New Task</div>
        <div className={styles.createFields}>
          {fields.map(({ label, value }) => (
            <div key={label} className={styles.createRow}>
              <span className={styles.createLabel}>{label}</span>
              <span className={styles.createValue}>{value}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // update_task or change_status — build diff table
  const rows: DiffRow[] = [];

  if (proposal.proposed_title !== null && proposal.proposed_title !== undefined) {
    const changed = proposal.proposed_title !== task?.title;
    rows.push({
      field: "title",
      current: task?.title ?? "—",
      proposed: proposal.proposed_title,
      changed,
    });
  }

  if (proposal.proposed_description !== null && proposal.proposed_description !== undefined) {
    const changed = proposal.proposed_description !== task?.description;
    rows.push({
      field: "description",
      current: task?.description ?? "—",
      proposed: proposal.proposed_description,
      changed,
    });
  }

  if (proposal.proposed_status !== null && proposal.proposed_status !== undefined) {
    const changed = proposal.proposed_status !== task?.status;
    rows.push({
      field: "status",
      current: task?.status ? <StatusPill status={task.status} /> : "—",
      proposed: <StatusPill status={proposal.proposed_status} />,
      changed,
    });
  }

  if (proposal.proposed_due_at !== null && proposal.proposed_due_at !== undefined) {
    const formatDate = (d: string | null) =>
      d
        ? new Date(d).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })
        : "—";
    const changed = proposal.proposed_due_at !== task?.due_at;
    rows.push({
      field: "due",
      current: formatDate(task?.due_at ?? null),
      proposed: formatDate(proposal.proposed_due_at),
      changed,
    });
  }

  if (proposal.proposed_external_ref !== null && proposal.proposed_external_ref !== undefined) {
    const changed = proposal.proposed_external_ref !== task?.external_ref;
    rows.push({
      field: "ref",
      current: task?.external_ref ?? "—",
      proposed: proposal.proposed_external_ref,
      changed,
    });
  }

  if (rows.length === 0) {
    return <div className={styles.empty}>No field changes</div>;
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th className={styles.thField}>Field</th>
          <th className={styles.thCurrent}>Current</th>
          <th className={styles.thProposed}>Proposed</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.field} className={row.changed ? styles.rowChanged : styles.rowUnchanged}>
            <td className={styles.tdField}>{row.field}</td>
            <td className={styles.tdCurrent}>{row.current}</td>
            <td className={`${styles.tdProposed} ${row.changed ? styles.tdProposedChanged : ""}`}>
              {row.proposed}
              {row.changed && <span className={styles.changedArrow} />}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
