# Tasky

A local-first personal professional organization system.

## What it does

Centralizes tasks across classes, clubs, projects, and side work. Ingests signals from external sources (GitHub, Gmail, Slack, Canvas), uses an AI-assisted proposal workflow to suggest task changes, and routes all AI output through a human review step before anything is applied. Long-form context lives in an Obsidian vault; structured operational state lives in SQLite.

## Stack

| Area            | Technology                              |
| --------------- | --------------------------------------- |
| Backend         | Python, FastAPI, SQLAlchemy, Alembic    |
| Database        | SQLite                                  |
| Frontend        | React, Vite, TypeScript, TanStack Query |
| Knowledge store | Obsidian vault (markdown)               |
| Package manager | uv                                      |

## Getting started

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment

Copy `.env.example` to `.env` and fill in your credentials.

```bash
cp .env.example .env
```

## Repository structure

```
frontend/   React + Vite UI
backend/    Python FastAPI application
vault/      Obsidian vault (git-tracked)
data/       SQLite database (gitignored)
docs/       Project documentation and specs
```
