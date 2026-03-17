"""Proposal review API routes.

Endpoints:
    GET    /proposals                 List pending (and optionally historical) proposals
    POST   /proposals/{id}/approve    Approve a proposal — triggers task creation/mutation
    POST   /proposals/{id}/reject     Reject a proposal
    POST   /proposals/batch-reject    Reject all proposals from an ingestion run
    POST   /proposals/approve-all     Approve all pending proposals
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.task import Task
from app.schemas.proposals import (
    ApproveProposalRequest,
    BatchRejectRequest,
    ProposalResponse,
)
from app.schemas.tasks import TaskResponse
from app.services.proposal_service import ProposalService
from app.services.task_service import _last_activity_at

router = APIRouter()


@router.get("", response_model=list[ProposalResponse])
def list_proposals(status: str | None = None, db: Session = Depends(get_db)):
    """List proposals with an optional status filter.

    If no status is provided, returns only pending proposals.
    Pass ``?status=approved``, ``?status=rejected``, etc. to retrieve other states.
    """
    svc = ProposalService(db)
    return svc.list_proposals(status)


@router.post("/batch-reject")
def batch_reject_proposals(body: BatchRejectRequest, db: Session = Depends(get_db)) -> dict:
    """Reject all pending proposals belonging to the given ingestion run."""
    svc = ProposalService(db)
    count = svc.batch_reject(body.ingestion_run_id)
    return {"rejected_count": count}


@router.post("/approve-all")
def approve_all_proposals(db: Session = Depends(get_db)) -> dict:
    """Approve all currently pending proposals."""
    svc = ProposalService(db)
    count = svc.approve_all_pending()
    return {"approved_count": count}


@router.post("/{proposal_id}/approve", response_model=TaskResponse)
def approve_proposal(
    proposal_id: int,
    body: ApproveProposalRequest | None = None,
    db: Session = Depends(get_db),
):
    """Approve a proposal, optionally overriding fields before applying.

    Returns the created or updated Task.
    """
    svc = ProposalService(db)
    overrides = body.model_dump(exclude_none=True) if body else None
    task = svc.approve(proposal_id, reviewed_by="user", overrides=overrides or None)

    # Eagerly load status_history for _last_activity_at
    task = (
        db.query(Task).options(joinedload(Task.status_history)).filter(Task.id == task.id).first()
    )
    activity = _last_activity_at(task)

    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        experience_id=task.experience_id,
        due_at=task.due_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        parent_task_id=task.parent_task_id,
        created_by=task.created_by,
        external_ref=task.external_ref,
        time_spent_minutes=task.time_spent_minutes,
        last_activity_at=activity,
    )


@router.post("/{proposal_id}/reject", response_model=ProposalResponse)
def reject_proposal(proposal_id: int, db: Session = Depends(get_db)):
    """Reject a proposal without mutating any task."""
    svc = ProposalService(db)
    return svc.reject(proposal_id)
