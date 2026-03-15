#!/bin/bash
# Runs on every agent Stop: auto-formats code, then checks linters.
# Clean  → exits 0 silently.
# Errors → writes only the error output to stderr and exits 2,
#           which blocks the stop and feeds the errors back to the agent.

# ── Prevent infinite loops ────────────────────────────────────────────────────
# Claude sets stop_hook_active=true if a Stop hook already blocked once this turn.
INPUT=$(cat)
STOP_HOOK_ACTIVE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(str(json.load(sys.stdin).get('stop_hook_active', False)).lower())
except Exception:
    print('false')
" 2>/dev/null)

if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
    exit 0
fi

# ── Resolve repo root from this script's location ────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# ── Auto-format (silent) ──────────────────────────────────────────────────────
make format > /dev/null 2>&1 || true

# ── Lint ──────────────────────────────────────────────────────────────────────
LINT_ERRORS=""

BACKEND_OUT=$(cd backend && uv run ruff check . 2>&1)
if [ $? -ne 0 ]; then
    LINT_ERRORS="${LINT_ERRORS}=== Backend (ruff) ===\n${BACKEND_OUT}\n\n"
fi

FRONTEND_OUT=$(cd frontend && npm run lint --silent 2>&1)
if [ $? -ne 0 ]; then
    LINT_ERRORS="${LINT_ERRORS}=== Frontend (eslint) ===\n${FRONTEND_OUT}\n\n"
fi

# ── Report ────────────────────────────────────────────────────────────────────
if [ -z "$LINT_ERRORS" ]; then
    exit 0
fi

printf "Linting errors found after auto-formatting. Please fix them:\n\n%b" \
    "$LINT_ERRORS" >&2
exit 2
