import { useState } from "react";
import type { TaskProposal, ApproveProposalRequest, TaskStatus } from "../../types";
import { ProposalTypeBadge } from "./ProposalTypeBadge";
import { ProposalDiff } from "./ProposalDiff";
import { SourceTrace } from "./SourceTrace";
import Button from "../ui/Button";
import styles from "./ProposalDetail.module.css";

interface ProposalDetailProps {
  proposal: TaskProposal;
  onApprove: (id: number, overrides?: ApproveProposalRequest) => void;
  onReject: (id: number) => void;
}

const STATUS_OPTIONS: TaskStatus[] = ["todo", "in_progress", "blocked", "done", "cancelled"];

function EditForm({
  proposal,
  onCancel,
  onSubmit,
}: {
  proposal: TaskProposal;
  onCancel: () => void;
  onSubmit: (overrides: ApproveProposalRequest) => void;
}) {
  const [title, setTitle] = useState(proposal.proposed_title ?? proposal.task?.title ?? "");
  const [description, setDescription] = useState(
    proposal.proposed_description ?? proposal.task?.description ?? "",
  );
  const [status, setStatus] = useState<TaskStatus>(
    proposal.proposed_status ?? proposal.task?.status ?? "todo",
  );
  const [dueAt, setDueAt] = useState(
    proposal.proposed_due_at
      ? proposal.proposed_due_at.slice(0, 10)
      : proposal.task?.due_at
        ? proposal.task.due_at.slice(0, 10)
        : "",
  );
  const [externalRef, setExternalRef] = useState(
    proposal.proposed_external_ref ?? proposal.task?.external_ref ?? "",
  );

  function handleSubmit() {
    const overrides: ApproveProposalRequest = {};
    if (title) overrides.proposed_title = title;
    if (description) overrides.proposed_description = description;
    overrides.proposed_status = status;
    if (dueAt) overrides.proposed_due_at = dueAt;
    if (externalRef) overrides.proposed_external_ref = externalRef;
    onSubmit(overrides);
  }

  return (
    <div className={styles.editForm}>
      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel}>Title</label>
        <input
          className={styles.fieldInput}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Task title"
        />
      </div>
      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel}>Description</label>
        <textarea
          className={styles.fieldTextarea}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          rows={4}
        />
      </div>
      <div className={styles.fieldRow}>
        <div className={styles.fieldGroup}>
          <label className={styles.fieldLabel}>Status</label>
          <select
            className={styles.fieldSelect}
            value={status}
            onChange={(e) => setStatus(e.target.value as TaskStatus)}
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>
        <div className={styles.fieldGroup}>
          <label className={styles.fieldLabel}>Due date</label>
          <input
            type="date"
            className={styles.fieldInput}
            value={dueAt}
            onChange={(e) => setDueAt(e.target.value)}
          />
        </div>
      </div>
      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel}>External ref</label>
        <input
          className={styles.fieldInput}
          value={externalRef}
          onChange={(e) => setExternalRef(e.target.value)}
          placeholder="e.g. github issue URL"
        />
      </div>
      <div className={styles.editActions}>
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button variant="primary" onClick={handleSubmit}>
          Approve
        </Button>
      </div>
    </div>
  );
}

export function ProposalDetail({ proposal, onApprove, onReject }: ProposalDetailProps) {
  const [editMode, setEditMode] = useState(false);
  const isPending = proposal.status === "pending";

  const title =
    proposal.proposal_type === "create_task"
      ? (proposal.proposed_title ?? "(untitled)")
      : (proposal.task?.title ?? proposal.proposed_title ?? "(untitled)");

  function handleApprove() {
    onApprove(proposal.id);
  }

  function handleEditApprove(overrides: ApproveProposalRequest) {
    onApprove(proposal.id, overrides);
    setEditMode(false);
  }

  function handleReject() {
    onReject(proposal.id);
  }

  return (
    <div className={styles.detail}>
      <div className={styles.scrollArea}>
        <div className={styles.header}>
          <ProposalTypeBadge type={proposal.proposal_type} />
          <h2 className={styles.taskTitle}>{title}</h2>
        </div>

        <section className={styles.section}>
          <div className={styles.sectionTitle}>Changes</div>
          {editMode ? (
            <EditForm
              proposal={proposal}
              onCancel={() => setEditMode(false)}
              onSubmit={handleEditApprove}
            />
          ) : (
            <ProposalDiff proposal={proposal} />
          )}
        </section>

        {proposal.reason_summary && !editMode && (
          <section className={styles.section}>
            <div className={styles.sectionTitle}>AI Rationale</div>
            <div className={styles.rationaleBox}>{proposal.reason_summary}</div>
          </section>
        )}

        {!editMode && (
          <section className={styles.section}>
            <div className={styles.sectionTitle}>Source</div>
            <SourceTrace proposal={proposal} />
          </section>
        )}

        {proposal.status !== "pending" && (
          <div className={styles.reviewedNote}>
            Reviewed as <strong>{proposal.status}</strong>
            {proposal.reviewed_at && (
              <>
                {" "}
                &bull;{" "}
                {new Date(proposal.reviewed_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </>
            )}
          </div>
        )}
      </div>

      {isPending && !editMode && (
        <div className={styles.actionBar}>
          <Button variant="danger" onClick={handleReject}>
            Reject
          </Button>
          <Button variant="ghost" onClick={() => setEditMode(true)}>
            Edit &amp; Approve
          </Button>
          <Button variant="primary" onClick={handleApprove}>
            Approve
          </Button>
        </div>
      )}
    </div>
  );
}
