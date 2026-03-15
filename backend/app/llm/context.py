"""LLM context assembly.

Builds the prompt payload sent to the model for proposal generation.
Draws from:
  1. The ingestion batch raw_payload
  2. Active tasks (todo, in_progress, blocked)
  3. Active experiences: overview.md + current_status.md for each
  4. Optionally: recent proposals (for reconciliation)

The assembled context is passed to LLMClient.generate_proposals().

TODO: define exact prompt format and context packaging (tech spec §12 TODO)
TODO: implement token budget management (truncate/prioritize if context is large)
"""
from sqlalchemy.orm import Session

from app.vault.reader import VaultReader


class ContextAssembler:
    def __init__(self, db: Session, vault_reader: VaultReader) -> None:
        self.db = db
        self.vault = vault_reader

    def build(self, batch_id: int) -> str:
        # TODO: load batch payload; load active tasks; load active experience markdown; assemble prompt string
        raise NotImplementedError
