"""Proposal review API routes.

Endpoints:
    GET    /proposals                 List pending (and optionally historical) proposals
    POST   /proposals/{id}/approve    Approve a proposal — triggers task creation/mutation
    POST   /proposals/{id}/reject     Reject a proposal

TODO: implement route handlers using ProposalService
TODO: add POST /proposals/{id}/edit-and-approve once edit UX is designed
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_proposals():
    # TODO: return pending proposals; accept ?status= filter
    raise NotImplementedError


@router.post("/{proposal_id}/approve")
def approve_proposal(proposal_id: int):
    # TODO: delegate to ProposalService.approve — must be transactional
    raise NotImplementedError


@router.post("/{proposal_id}/reject")
def reject_proposal(proposal_id: int):
    # TODO: delegate to ProposalService.reject
    raise NotImplementedError
