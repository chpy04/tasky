# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Tasky** is a local-first personal task organization system. It combines an Obsidian markdown vault (the knowledge store), a SQLite database (structured operational state), a Python FastAPI backend, and a React frontend. The core design principle: **AI proposes, human approves** — all LLM-generated task changes flow through a proposal review step before any mutation is applied.

## Commands

### Backend

```bash
cd backend
uv sync                                       # Install dependencies
uv run uvicorn app.main:app --reload --port 7400  # Start dev server on :7400
uv run pytest                                 # Run all tests
uv run pytest tests/test_tasks.py             # Run a single test module
```

### Frontend

```bash
cd frontend
npm install                                   # Install dependencies
npm run dev                                   # Start Vite dev server (proxies /api → :8000)
npm run build                                 # Production build
```

### Environment Setup

```bash
cp .env.example .env
# Required: ANTHROPIC_API_KEY
# Optional: GITHUB_TOKEN, GMAIL_*, SLACK_*, CANVAS_* (validated when used)
```

## Architecture

### Data Flow

1. **Connectors** (`backend/app/connectors/`) fetch external data (GitHub, Gmail, Slack, Canvas) and return normalized batches.
2. **Ingestion service** stores batches into `IngestionBatch` records and calls the LLM to generate `TaskProposal` records.
3. **User reviews proposals** via the frontend Proposals UI — approve, edit, or reject.
4. **Proposal service** applies approved proposals by mutating `Task` records and writing audit entries to `TaskStatusHistory`.

### Backend Layer Separation

- `app/api/` — FastAPI routers (HTTP boundary only)
- `app/services/` — Business logic; all mutations go through here
- `app/models/` — SQLAlchemy ORM models (Task, TaskProposal, TaskStatusHistory, Experience, IngestionBatch, IngestionRun)
- `app/connectors/` — External data sources; implement the `base.py` protocol, return `{source_type, payload, metadata}`
- `app/llm/` — Anthropic client wrapper, context builder, Pydantic schemas for structured output
- `app/vault/` — Obsidian vault reader; experiences and prompts are markdown files in `vault/`

### Key Models

- **Task** — Core item. Status: `todo/in_progress/blocked/done/cancelled`. Priority: `low/medium/high/urgent`. Supports subtasks via `parent_task_id`. Linked to an `Experience`.
- **TaskProposal** — Trust boundary for AI changes. Types: `create_task`, `update_task`, `change_status`, `cancel_task`. Status: `pending/approved/rejected/superseded`. All proposals are logged for audit.
- **Experience** — Long-running context (project, job, class). Each experience has a corresponding markdown file in `vault/Experiences/{folder_path}/`.
- **IngestionRun / IngestionBatch** — Metadata and raw payloads from each connector run.

### Frontend

- React 18 + Vite 5 + TypeScript + TanStack Query
- Vite dev server proxies `/api/*` to `http://localhost:8000`
- Pages: Tasks, Proposals, Ingestion, Experiences, Prompts (in `src/pages/`)
- Server state managed with TanStack Query hooks in `src/api/`

### Vault

`vault/` is git-tracked markdown. Key subdirectories:
- `Experiences/` — One folder per experience with a markdown overview
- `Prompts/` — System prompts editable from the UI
- `Daily/`, `Weekly/`, `Monthly/` — Summaries

### Implementation Status

Most files are stubs with `NotImplementedError` or empty bodies. Implemented: database models, migration framework, FastAPI router structure, service/connector/vault interfaces, Vite + React scaffold. Not yet implemented: router handlers, service logic, connector fetching, LLM client, VaultReader I/O, React routing, page components, TanStack Query hooks, background job scheduling.

## Tech Stack Details

- Python 3.12 (required), managed with `uv`
- FastAPI + SQLAlchemy + Alembic (migrations in `backend/app/db/migrations/`)
- SQLite at `data/app.db` (git-ignored)
- Anthropic SDK for LLM integration
- pytest with `asyncio_mode = auto` (configured in `pyproject.toml`)
