"""In-memory concurrency guard for background ingestion jobs.

Uses two module-level sets to track which run IDs have in-flight
operations. A threading.Lock protects the check-then-add pattern
against TOCTOU races when multiple requests arrive concurrently.

Sets:
  _active_runs     — full pipeline / connector-only runs in flight
  _active_proposes — per-run LLM propose calls in flight
"""

import threading

_lock = threading.Lock()
_active_runs: set[int] = set()
_active_proposes: set[int] = set()


def claim_run(run_id: int) -> bool:
    """Attempt to claim a run ID as active.

    Returns True if successfully claimed (not already active).
    Returns False if the run ID is already in the active set.
    """
    with _lock:
        if run_id in _active_runs:
            return False
        _active_runs.add(run_id)
        return True


def release_run(run_id: int) -> None:
    """Release a previously claimed run ID."""
    with _lock:
        _active_runs.discard(run_id)


def claim_propose(run_id: int) -> bool:
    """Attempt to claim a run ID for an LLM propose call.

    Returns True if successfully claimed (not already proposing).
    Returns False if already in the active proposes set.
    """
    with _lock:
        if run_id in _active_proposes:
            return False
        _active_proposes.add(run_id)
        return True


def release_propose(run_id: int) -> None:
    """Release a previously claimed propose run ID."""
    with _lock:
        _active_proposes.discard(run_id)


def has_active_run() -> bool:
    """Check if any run is currently active."""
    with _lock:
        return len(_active_runs) > 0
