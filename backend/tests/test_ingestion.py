"""Tests for ingestion run creation, batch persistence, and processing.

TODO: implement tests once IngestionService is built.
Connectors should be stubbed to return fixture data.
LLM calls should be stubbed to return fixture proposals.

Scenarios to cover:
- trigger a manual run; verify IngestionRun created with status=running
- connector returns batches; verify IngestionBatch records created
- process a batch; verify proposals generated and persisted
- connector failure; verify run marked failed; other batches unaffected
"""


def test_placeholder():
    pass  # TODO: remove once real tests are written
