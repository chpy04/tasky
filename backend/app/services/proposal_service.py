"""Proposal domain service.

Owns the review and application workflow. Approving a proposal is a
transactional operation: it must create/update the task and record
history in a single commit.

Responsibilities:
- list proposals (filtered by status)
- approve a proposal → mutate task in the same transaction
- reject a proposal → mark rejected, preserve original content
- (future) edit-and-approve

TODO: implement proposal conflict/staleness detection (tech spec §20 TODO)
TODO: implement edit-before-approve mechanics (tech spec §10 TODO)
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.ingestion_batch import IngestionBatch
from app.models.task import Task, TaskStatus
from app.models.task_proposal import ProposalStatus, ProposalType, TaskProposal
from app.models.task_status_history import ChangedBy, TaskStatusHistory


class ProposalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_proposals(self, status: str | None = None) -> list[TaskProposal]:
        """Return proposals filtered by status (defaults to pending if not specified).

        Eager-loads task and ingestion_batch (with ingestion_run), ordered newest first.
        """
        query = (
            self.db.query(TaskProposal)
            .options(
                joinedload(TaskProposal.task),
                joinedload(TaskProposal.ingestion_batch).joinedload(IngestionBatch.ingestion_run),
            )
            .order_by(TaskProposal.created_at.desc())
        )

        if status is not None:
            query = query.filter(TaskProposal.status == status)
        else:
            query = query.filter(TaskProposal.status == ProposalStatus.pending)

        return query.all()

    def approve(
        self,
        proposal_id: int,
        reviewed_by: str = "user",
        overrides: dict | None = None,
    ) -> Task:
        """Approve a proposal, mutating or creating the task in the same transaction."""
        proposal = self.db.query(TaskProposal).filter(TaskProposal.id == proposal_id).first()
        if proposal is None:
            raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

        # Apply user-supplied overrides to the proposal fields before applying.
        if overrides:
            for field, value in overrides.items():
                if value is not None:
                    setattr(proposal, field, value)

        now = datetime.now(timezone.utc)

        if proposal.proposal_type == ProposalType.create_task:
            task = Task(
                title=proposal.proposed_title or "",
                description=proposal.proposed_description,
                status=proposal.proposed_status or TaskStatus.todo,
                experience_id=proposal.proposed_experience_id,
                due_at=proposal.proposed_due_at,
                parent_task_id=proposal.proposed_parent_task_id,
                external_ref=proposal.proposed_external_ref,
                created_by="ai",
            )
            self.db.add(task)
            self.db.flush()  # populate task.id before writing history

            history = TaskStatusHistory(
                task_id=task.id,
                status=task.status,
                changed_by=ChangedBy.ai,
            )
            self.db.add(history)

        elif proposal.proposal_type == ProposalType.update_task:
            if proposal.task_id is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Proposal {proposal_id} has no associated task",
                )
            task = self.db.query(Task).filter(Task.id == proposal.task_id).first()
            if task is None:
                raise HTTPException(status_code=404, detail=f"Task {proposal.task_id} not found")

            old_status = task.status
            fields = {
                "title": proposal.proposed_title,
                "description": proposal.proposed_description,
                "status": proposal.proposed_status,
                "experience_id": proposal.proposed_experience_id,
                "due_at": proposal.proposed_due_at,
                "parent_task_id": proposal.proposed_parent_task_id,
                "external_ref": proposal.proposed_external_ref,
            }
            for field, value in fields.items():
                if value is not None:
                    setattr(task, field, value)

            if proposal.proposed_status is not None and proposal.proposed_status != old_status:
                history = TaskStatusHistory(
                    task_id=task.id,
                    status=task.status,
                    changed_by=ChangedBy.ai,
                )
                self.db.add(history)

        elif proposal.proposal_type == ProposalType.change_status:
            if proposal.task_id is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Proposal {proposal_id} has no associated task",
                )
            task = self.db.query(Task).filter(Task.id == proposal.task_id).first()
            if task is None:
                raise HTTPException(status_code=404, detail=f"Task {proposal.task_id} not found")

            if proposal.proposed_status is not None:
                old_status = task.status
                task.status = proposal.proposed_status
                if task.status != old_status:
                    history = TaskStatusHistory(
                        task_id=task.id,
                        status=task.status,
                        changed_by=ChangedBy.ai,
                    )
                    self.db.add(history)

        elif proposal.proposal_type == ProposalType.cancel_task:
            if proposal.task_id is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Proposal {proposal_id} has no associated task",
                )
            task = self.db.query(Task).filter(Task.id == proposal.task_id).first()
            if task is None:
                raise HTTPException(status_code=404, detail=f"Task {proposal.task_id} not found")

            old_status = task.status
            task.status = TaskStatus.cancelled
            if task.status != old_status:
                history = TaskStatusHistory(
                    task_id=task.id,
                    status=TaskStatus.cancelled,
                    changed_by=ChangedBy.ai,
                )
                self.db.add(history)

        else:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown proposal type: {proposal.proposal_type}",
            )

        proposal.status = ProposalStatus.approved
        proposal.reviewed_at = now
        proposal.reviewed_by = reviewed_by

        self.db.commit()
        self.db.refresh(task)
        return task

    def reject(self, proposal_id: int, reviewed_by: str = "user") -> TaskProposal:
        """Reject a proposal without mutating any task."""
        proposal = self.db.query(TaskProposal).filter(TaskProposal.id == proposal_id).first()
        if proposal is None:
            raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

        now = datetime.now(timezone.utc)
        proposal.status = ProposalStatus.rejected
        proposal.reviewed_at = now
        proposal.reviewed_by = reviewed_by

        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def batch_reject(self, ingestion_run_id: int) -> int:
        """Reject all pending proposals linked to the given ingestion run.

        Returns the count of proposals that were rejected.
        """
        now = datetime.now(timezone.utc)

        pending_proposals = (
            self.db.query(TaskProposal)
            .join(TaskProposal.ingestion_batch)
            .filter(
                IngestionBatch.ingestion_run_id == ingestion_run_id,
                TaskProposal.status == ProposalStatus.pending,
            )
            .all()
        )

        for proposal in pending_proposals:
            proposal.status = ProposalStatus.rejected
            proposal.reviewed_at = now
            proposal.reviewed_by = "user"

        self.db.commit()
        return len(pending_proposals)

    def approve_all_pending(self) -> int:
        """Approve all currently pending proposals.

        Returns the count of proposals that were approved.
        """
        pending_proposals = (
            self.db.query(TaskProposal).filter(TaskProposal.status == ProposalStatus.pending).all()
        )

        count = 0
        for proposal in pending_proposals:
            try:
                self.approve(proposal.id, reviewed_by="user")
                count += 1
            except HTTPException:
                # Skip proposals that fail (e.g., missing task reference); already committed
                # individual approvals are separate commits via approve(), so we continue.
                pass

        return count
