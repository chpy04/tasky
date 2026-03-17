import styles from "./ProposalTypeBadge.module.css";
import type { ProposalType } from "../../types";

const LABELS: Record<ProposalType, string> = {
  create_task: "CREATE",
  update_task: "UPDATE",
  change_status: "STATUS",
  cancel_task: "CANCEL",
};

export function ProposalTypeBadge({ type }: { type: ProposalType }) {
  return <span className={`${styles.badge} ${styles[type]}`}>{LABELS[type]}</span>;
}
