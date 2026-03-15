# Professional Life Organization System — Product Summary

Product document for a local-first AI-assisted organization platform built around an Obsidian vault, SQLite task engine, and a Python web application.

> **Project scope:** Local-first professional organization system combining a markdown knowledge base, a structured task database, and AI-assisted ingestion and review workflows.

## Product vision

The product is a centralized professional operating system for a student balancing classes, clubs, projects, side work, and communication across many disconnected platforms. Its purpose is to replace a fragile “list in my head” with a durable system that captures work, organizes it, and makes that context usable by both the user and AI tools.

The system is intentionally local-first. Long-term knowledge is stored in markdown files inside an Obsidian vault, while structured operational data such as tasks, review states, and time logs live in a local SQLite database. A web application becomes the primary interface for reviewing AI-suggested updates, managing tasks, and maintaining a searchable record of ongoing and past experiences.

## Core goals

- Create a single source of truth for tasks across classes, ski team, electric racing, side jobs, and future commitments.
- Maintain a durable database of projects, jobs, and classes with enough detail to support recall, reflection, and future resume and job-search workflows.
- Ingest information from external sources and turn raw signals into suggested task updates and summaries.
- Keep the user in control by routing AI output through an approval workflow instead of allowing silent task edits.
- Preserve portability and reduce vendor lock-in by storing long-form knowledge in markdown and keeping the entire system runnable locally.
- Make the system legible to AI so it can support planning, summarization, retrieval, and future workflow automation.

## Product principles

- **Local-first and portable:** core knowledge remains in ordinary markdown files that can be version-controlled and opened without the application.
- **Human-approved automation:** AI proposes; the user confirms, edits, or rejects.
- **Structured where structure matters:** tasks, statuses, due dates, and time logs live in a database rather than loose notes.
- **Flexible where narrative matters:** experiences, summaries, and prompts live as readable markdown documents.
- **Incremental rollout:** start with the highest-value connectors and only expand to more brittle integrations after the core workflow is stable.
- **Cost-aware AI usage:** deterministic parsing and cheap structured models first; stronger models only for ambiguous or synthesis-heavy work.

## Users and primary use cases

| User / context | Need | Desired outcome |
|---|---|---|
| Student managing multiple roles | Track obligations across school, clubs, and work without relying on memory | Clear task queue, deadlines, and recent activity in one place |
| Busy project contributor | See updates from GitHub, Slack, email, and class systems without manually checking each tool | AI-generated proposed changes and daily summary |
| Future job applicant | Recall meaningful work details from past projects and classes | Searchable experience records and reusable resume/interview details |
| User reviewing workload | Understand where time and effort are being spent | Time tracking tied to completed tasks and aggregate views by experience/category |

## Key user stories

- As a user, I want one place to see all open tasks across my life so I do not have to remember them mentally.
- As a user, I want AI to review new source data and suggest task creations, edits, and completions so I spend less time maintaining the system.
- As a user, I want all AI task updates to appear as pending changes so I remain in control of what is applied.
- As a user, I want to manually create, edit, prioritize, and complete tasks in the interface at any time.
- As a user, I want to record hours spent when a task is completed so I can later analyze where my effort went.
- As a user, I want daily markdown summaries generated from communications and activity so I have a searchable historical log.
- As a user, I want to create structured experience pages for projects, jobs, and classes from a rough info dump plus optional repository context.
- As a user, I want prompts to be editable from the frontend so I can refine the system without modifying code.
- As a user, I want to trigger ingestion manually whenever I choose instead of waiting for the scheduled run.
- As a user, I want the system to remain useful even if I stop using a vendor product because the core knowledge stays in files I own.

## Scope of the initial product

### Included in MVP

- Centralized task system with statuses, due dates, priorities, source links, and completion tracking.
- Pending-change review flow for AI-proposed task updates.
- Experience management for projects, jobs, and classes using markdown templates.
- Daily summary generation written into the Obsidian vault.
- Manually triggered and scheduled ingestion runs.
- Prompt management UI for core AI workflows.
- Initial integrations with Gmail/email, GitHub, Canvas, and selected Slack sources.

### Explicitly deferred from MVP

- iMessage ingestion.
- Sending messages or replying on external platforms.
- Full recursive experience hierarchies beyond light support in file structure.
- Highly automated task application without user review.
- Weekly and monthly rollup summaries, except as a later extension.
- Broad support for every possible site connector before the core workflow is validated.

## Functional areas

### A. Data ingestion

The system periodically or manually pulls data from configured external sources. Each source produces normalized records that can be processed for task updates, historical summaries, or both.

### B. Task management

The task interface is the operational center of the product. Users can browse open work, view pending AI changes, and manually create or edit tasks. Completion workflows should capture time spent.

### C. Experience management

Experiences store durable context for projects, jobs, and classes. Each experience is represented as a markdown file following a common structure so it remains readable to both humans and AI systems.

### D. Summaries and history

Daily summaries convert fragmented communication signals into a compact written record. These documents support later search, reflection, and future rollup summaries.

### E. Analytics and reflection

When tasks are completed, the system asks for time spent. Over time, this enables reporting on time allocation by class, job, project, and broader category.

## Output objectives

| Output | Definition of success |
|---|---|
| Task list | Accurately reflects current open work with useful metadata and source traceability |
| Pending AI changes | Provides high-signal suggested edits with enough explanation for quick approval or correction |
| Daily summaries | Capture key activity and decisions in readable markdown with consistent structure |
| Experience records | Store reusable project, job, and class context in a format that supports retrieval, resumes, and interviews |
| Time analytics | Show meaningful aggregation of effort across domains and periods |
| Prompt editing | Allows iterative system tuning without code changes |

## Risks and design responses

- **Risk:** noisy ingestion creates too many low-value tasks. **Response:** start with narrow filters and require approval for all AI-generated task changes.
- **Risk:** overuse of LLMs increases cost and inconsistency. **Response:** prefer direct API parsing and cheap structured models whenever possible.
- **Risk:** knowledge and operational state become mixed together. **Response:** separate markdown knowledge from database-backed task operations.
- **Risk:** brittle connectors slow down the project. **Response:** sequence integrations by reliability and value, beginning with Canvas, Gmail, GitHub, and filtered Slack.
- **Risk:** user trust drops if automation makes silent mistakes. **Response:** maintain audit trails and explicit pending-change review.

## Staged implementation plan

| Stage | Objective | Key deliverables |
|---|---|---|
| Stage 0 — Foundations | Define schemas, templates, and review model | Vault structure, task schema, experience template, prompt files, UX wireframe |
| Stage 1 — Core product | Build the local-first app without heavy integrations | SQLite-backed task engine, manual task CRUD, pending-change UI, experience creation flow, prompt editor |
| Stage 2 — First connectors | Automate high-value ingestion | Canvas assignments, Gmail ingestion, GitHub tracked-repo updates, selected Slack ingestion |
| Stage 3 — Daily intelligence | Turn source data into useful outputs | Task proposal pipeline, daily summary generation, improved linking to experiences |
| Stage 4 — Analytics | Measure effort and workload | Completion-time capture, dashboards by category, experience, and time period |
| Stage 5 — Extended sources and rollups | Expand coverage and historical summarization | Custom site connectors, weekly and monthly summaries, more refined filtering and classification |

## Long-term opportunities

- Resume and interview assistant that maps a job description to the most relevant experience records and forgotten accomplishments.
- Deeper source-specific ingestion controls such as per-channel Slack rules or keyword filters.
- Light automatic approval for low-risk structured updates after trust is established.
- More advanced experience hierarchies and sub-project linking.
- Search and retrieval workflows that package the right subset of the vault and database context for AI tools.

## Product summary statement

This product is a personal professional operating system: a local-first application that centralizes tasks, preserves the history of work, and converts scattered signals from different platforms into actionable, reviewable, and reusable context.
