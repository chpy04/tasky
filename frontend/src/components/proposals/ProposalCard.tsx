import type { TaskProposal } from "../../types";
import { ProposalTypeBadge } from "./ProposalTypeBadge";
import styles from "./ProposalCard.module.css";

interface ProposalCardProps {
  proposal: TaskProposal;
  selected: boolean;
  onClick: () => void;
}

const STATUS_DOT_COLOR: Record<string, string> = {
  approved: "#4caf50",
  rejected: "#ff4444",
  superseded: "#6a5038",
  pending: "transparent",
};

export function ProposalCard({ proposal, selected, onClick }: ProposalCardProps) {
  const title =
    proposal.proposal_type === "create_task"
      ? (proposal.proposed_title ?? "(untitled)")
      : (proposal.task?.title ?? proposal.proposed_title ?? "(untitled)");

  const excerpt = proposal.reason_summary
    ? proposal.reason_summary.length > 80
      ? proposal.reason_summary.slice(0, 80) + "…"
      : proposal.reason_summary
    : null;

  const sourceType = proposal.ingestion_batch?.source_type ?? null;

  return (
    <div
      className={`${styles.card} ${selected ? styles.selected : ""}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onClick();
      }}
    >
      <div className={styles.topRow}>
        <ProposalTypeBadge type={proposal.proposal_type} />
        {proposal.status !== "pending" && (
          <span
            className={styles.statusDot}
            style={{ background: STATUS_DOT_COLOR[proposal.status] ?? "#6a5038" }}
            title={proposal.status}
          />
        )}
      </div>
      <div className={styles.title}>{title}</div>
      {excerpt && <div className={styles.reason}>{excerpt}</div>}
      {sourceType && <div className={styles.source}>{sourceType}</div>}
    </div>
  );
}
