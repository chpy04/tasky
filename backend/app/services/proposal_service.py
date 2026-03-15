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

from sqlalchemy.orm import Session


class ProposalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_proposals(self, status: str | None = None):
        # TODO: return proposals filtered by status
        raise NotImplementedError

    def approve(self, proposal_id: int, reviewed_by: str = "user"):
        # TODO: validate proposal; create/update task; append history; mark approved — all in one transaction
        raise NotImplementedError

    def reject(self, proposal_id: int, reviewed_by: str = "user"):
        # TODO: mark rejected; preserve original content; do not mutate task
        raise NotImplementedError
