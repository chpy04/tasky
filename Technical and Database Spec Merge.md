# Task Organization System — Technical Architecture and Database Specification

Engineering specification for a local-first application that combines an Obsidian vault, a SQLite database, and an AI-assisted ingestion and review workflow.

> **Project scope:** A local-first task and context organization system that stores operational state in SQLite, narrative context in markdown, and routes external signals through an AI-assisted proposal workflow before any task changes are applied.

---

## 1. Purpose of this document

This document merges the current database design proposal with the technical implementation specification.

The database design proposal is treated as the most current source of truth for:

- the system data model
- the separation between database state and Obsidian markdown
- the ingestion and proposal workflow
- the current assumptions around experiences and LLM context assembly

This document extends that database proposal with:

- the overall application architecture
- subsystem responsibilities
- repository and module structure
- API direction
- execution flow between components
- explicit TODO stubs for areas that are not yet fully designed

Where the previous technical spec included stale or conflicting assumptions, they have been corrected to match the database proposal.

---

## 2. System goals

The system is designed to support a personal task and context management workflow where:

- the user has many long-running contexts such as classes, projects, clubs, and jobs
- relevant information arrives from multiple external systems
- AI helps interpret incoming information
- AI does **not** directly mutate operational data
- the user reviews proposed task changes before they are applied
- durable human-authored context lives in an Obsidian vault, not in the database

This architecture is intended to keep the operational state simple, auditable, and trustworthy while still allowing the LLM to reason over rich narrative context.

---

## 3. Core design principles

1. **Operational state lives in the database**

   The database stores:

   - tasks
   - task proposals
   - task status history
   - experiences metadata
   - ingestion runs and batches

2. **Narrative context lives in Obsidian markdown files**

   The database does not store long-form experience summaries as primary records.

   Instead, each experience maps to a folder in the Obsidian vault containing required markdown context files.

3. **AI never writes directly to tasks**

   AI produces proposals.

   Proposals must be reviewed and approved before they create or update tasks.

4. **Ingestion is batched**

   External content is grouped into batches, then processed into structured task proposals.

5. **The system is local-first**

   Core state should remain usable locally with minimal infrastructure.

6. **The architecture should remain extensible**

   The MVP should stay simple, but the system should leave room for future additions like more sources, summaries, analytics, and richer task intelligence.

---

## 4. High-level architecture

The application has four primary layers:

1. **Frontend UI**

   A React + Vite frontend provides:

   - task views
   - proposal review interfaces
   - ingestion controls
   - experience management views
   - future analytics and configuration interfaces

2. **Backend application**

   A Python backend coordinates:

   - database access
   - vault access
   - ingestion execution
   - context assembly
   - LLM calls
   - proposal validation and application
   - API endpoints for the frontend

3. **Structured operational store**

   SQLite, accessed through SQLAlchemy, stores transactional application state.

4. **Narrative knowledge store**

   The Obsidian vault stores human-authored markdown context, especially per-experience context files that are loaded into prompts.

### Architecture summary

- The frontend communicates with the backend over a local HTTP API.
- The backend reads and writes structured state through SQLAlchemy models.
- The backend reads markdown files directly from the filesystem.
- Connector modules ingest raw external data into ingestion batches.
- The backend assembles context from batches, tasks, and experience markdown files.
- The LLM produces structured task proposals.
- The user reviews proposals.
- Approved proposals mutate tasks and append task history.

---

## 5. Chosen stack

| Area | Technology | Notes |
|---|---|---|
| Backend language | Python | Preferred implementation language |
| Web framework | FastAPI | Typed local API service and future background orchestration |
| ORM | SQLAlchemy | Mature ORM with strong SQLite support |
| Database | SQLite | Local-first operational database for MVP |
| Frontend | React + Vite | Local UI for tasks, proposals, and controls |
| Knowledge store | Obsidian vault | Human-readable markdown knowledge base |
| Scheduling | In-process scheduler or cron-style triggers | MVP-friendly execution model |
| Automation / source access | API clients first, browser automation later where needed | Connector-specific |
| LLM interface | Structured outputs / schema-constrained generation | Proposal-only AI writes |
| Vault/version backup | Git for vault, separate DB backup strategy | Keeps markdown portable |

---

## 6. Source-of-truth boundaries

A major architectural decision is the separation between database state and vault state.

### Database owns

- tasks
- task status lifecycle
- proposal review state
- ingestion tracking
- references between tasks and experiences
- execution/audit state for operational workflows

### Vault owns

- per-experience narrative context
- editable prompt files
- templates
- generated summaries
- future long-form notes and derived documents

### Why this matters

This prevents the database from turning into a semi-structured note system while also preventing important operational state from becoming unqueryable freeform text.

---

## 7. Experience model and vault structure

Experiences represent long-running contexts such as:

- projects
- classes
- jobs
- clubs
- other major commitments

Each experience corresponds to a folder in the Obsidian vault.

### Required files per experience

Each experience folder must contain:

```text
overview.md
current_status.md
```

### `overview.md`

A short description of:

- what the experience is
- its purpose
- long-term goals

### `current_status.md`

A short description of:

- current work
- current priorities
- blockers or ongoing work

These files are loaded into LLM prompts for active experiences.

### Experience database table

The database stores only the operational metadata needed to track experiences.

#### `experiences`

Fields:

- `id`
- `active` (boolean)
- `folder_path`

### Experience behavior

- tasks reference an experience via `experience_id`
- only active experiences are loaded into the main LLM context
- the markdown files remain the narrative description of the experience
- the database does not currently attempt to mirror or normalize the content of those markdown files

### TODO — experience metadata expansion

The system will likely need a richer experience model later, potentially including slugs, names, categories, ordering, archival state, or lightweight metadata for UI display. That has not been fully scoped yet.

There will be an implementation here that:

- preserves the current simple active/folder-path design
- adds only the minimum metadata needed for UI usability and stable references
- avoids duplicating narrative markdown content in the database unnecessarily

---

## 8. Task model

Tasks are the main actionable records in the system.

#### `tasks`

Fields:

- `id`
- `title`
- `description` (nullable)
- `status`
- `priority`
- `experience_id`
- `due_at` (nullable)
- `created_at`
- `updated_at`
- `parent_task_id` (nullable)
- `created_by` (internal)
- `external_ref` (nullable)

### `status` enum

- `todo`
- `in_progress`
- `blocked`
- `done`
- `cancelled`

### `priority` enum

- `low`
- `medium`
- `high`
- `urgent`

### Task behavior

- tasks may optionally belong to an experience
- subtasks are modeled by setting `parent_task_id`
- `external_ref` can link a task to an external system identifier if needed
- active task context for LLM processing includes tasks whose status is:
  - `todo`
  - `in_progress`
  - `blocked`

### Notes on `created_by`

The exact internal semantics of `created_by` have not been fully specified yet, but the field is intended to distinguish between manually created tasks and system-originated tasks.

### TODO — task deduplication and reconciliation rules

The system has not yet fully defined how incoming proposals should reconcile with existing tasks when there are partial matches, possible duplicates, or ambiguous references.

There will be an implementation here that:

- compares proposed task changes against current open tasks
- handles duplicate prevention and merge suggestions
- preserves auditability when AI is uncertain
- biases toward proposal generation instead of silent auto-resolution

---

## 9. Task status history

Task history must preserve the lifecycle of each task.

#### `task_status_history`

Fields:

- `id`
- `task_id`
- `status`
- `changed_at`
- `changed_by`

### `changed_by` enum

- `user`
- `ai`
- `system`

### Behavior

- append-only
- records every status transition for audit and later analysis
- written whenever an approved proposal or a manual action changes status

### Clarification

Even though AI does not directly modify tasks, `changed_by = ai` may still be useful when an approved AI-originated proposal is what caused the resulting change.

If later implementation semantics suggest that this should instead always be `user` or `system` at apply time, that can be refined during implementation.

---

## 10. Task proposal model

The proposal layer is the central trust boundary of the system.

LLMs do not write to tasks directly. They generate proposals that must be reviewed.

#### `task_proposals`

Fields:

- `id`
- `proposal_type`
- `status`
- `task_id` (nullable)
- `proposed_title` (nullable)
- `proposed_description` (nullable)
- `proposed_status` (nullable)
- `proposed_priority` (nullable)
- `proposed_experience_id` (nullable)
- `proposed_due_at` (nullable)
- `proposed_parent_task_id` (nullable)
- `proposed_external_ref` (nullable)
- `reason_summary` (nullable)
- `created_at`
- `reviewed_at` (nullable)
- `reviewed_by` (nullable)
- `created_by`
- `ingestion_batch_id` (nullable)

### `proposal_type` enum

- `create_task`
- `update_task`
- `change_status`
- `cancel_task`

### proposal `status` enum

- `pending`
- `approved`
- `rejected`
- `superseded`

### `reviewed_by` enum

- `user`
- `system`

### `created_by` enum

- `ai`
- `system`

### Proposal behavior

- proposals are created from ingestion + context processing
- proposals remain stored even after review
- approving a proposal triggers task creation or mutation
- rejected proposals remain visible for audit and future tuning
- a proposal may optionally be associated with an ingestion batch

### Why proposals are explicit records

This makes the system:

- reviewable
- debuggable
- safer than direct AI writes
- tunable over time through inspection of accepted vs rejected outputs

### TODO — proposal editing UX

The exact UI and backend mechanics for “edit before approve” are not yet fully designed.

There will be an implementation here that:

- lets the user inspect all proposed fields
- allows correcting proposed values before application
- preserves a record of both the original proposal and the final applied change
- keeps the workflow fast enough that reviewing proposals remains practical

---

## 11. Ingestion model

External information is ingested in batches and processed into task proposals.

Possible sources include:

- Slack
- email
- notes
- calendar
- GitHub

The current database design intentionally tracks ingestion state without deeply normalizing every source payload into a large relational source model.

### `ingestion_runs`

Represents a full ingestion cycle.

Fields:

- `id`
- `started_at`
- `finished_at`
- `status`
- `triggered_by`
- `source_type`
- `error_summary` (nullable)

#### `status` enum

- `running`
- `completed`
- `failed`

#### `triggered_by` enum

- `manual`
- `scheduled`
- `system`

#### `source_type` enum

- `slack`
- `email`
- `calendar`
- `github`
- `mixed`

### `ingestion_batches`

Stores raw content to be processed.

Fields:

- `id`
- `ingestion_run_id`
- `source_type`
- `raw_payload`
- `created_at`
- `processed_at` (nullable)
- `status`
- `error_summary` (nullable)

#### `status` enum

- `pending`
- `processed`
- `failed`

### Ingestion behavior

- an ingestion run represents one full execution cycle
- a run may generate multiple batches
- `raw_payload` contains minimally structured JSON or text
- the LLM reads a batch plus system context and produces proposals
- processed and failed states support reruns, debugging, and observability

### Correction from older technical assumptions

The older technical spec referred to a broader normalized “source item” model. That is no longer the current source of truth.

For now, the design is intentionally simpler:

- ingestion tracking is modeled explicitly
- raw external content is stored at the batch layer
- downstream intelligence is driven off batches rather than a full generalized source-item schema

### TODO — source-specific normalization strategy

The project has not yet decided how much normalization should happen before batch creation, or whether some sources should eventually have lightweight intermediate models.

There will be an implementation here that:

- gathers source data reliably from each connector
- converts it into a consistent enough batch representation for downstream processing
- preserves important metadata like timestamps, source identifiers, and links
- avoids premature schema complexity until real connector needs justify it

---

## 12. LLM context construction

When processing an ingestion batch, the backend constructs a prompt from multiple sources of context.

### Current intended prompt inputs

1. **The new ingestion batch**

   - `raw_payload` from `ingestion_batches`

2. **Active tasks**

   - tasks with status:
     - `todo`
     - `in_progress`
     - `blocked`

3. **Active experiences**

   - `overview.md`
   - `current_status.md`

4. **Optional recent proposals**

   - included if useful for reconciliation and avoiding repeated low-value suggestions

### Output

The LLM returns structured proposal objects which are validated and stored in `task_proposals`.

### Backend responsibilities in this flow

- load batch payload
- query active tasks
- query active experiences
- read required markdown files from each active experience folder
- assemble prompt payload
- invoke LLM with a constrained schema
- validate returned proposals
- persist proposals and mark batch processing status

### TODO — exact prompt format and proposal schema contract

The exact structure of prompt files, context packaging, function calling, and schema enforcement has not yet been fully designed.

There will be an implementation here that:

- packages ingestion data and current operational context into a predictable prompt structure
- constrains model outputs to a proposal schema that the backend can validate
- supports prompt iteration without requiring invasive code changes
- records enough metadata to debug poor outputs and tune the prompts later

---

## 13. End-to-end workflow

### 13.1 Ingestion

External source data is fetched by one or more connectors.

Flow:

```text
External systems -> connector modules -> ingestion_run -> ingestion_batches
```

### 13.2 Context assembly

For each pending batch, the backend loads:

- the batch payload
- active tasks
- active experiences from the database
- `overview.md` and `current_status.md` for each active experience
- optional recent proposal/task context if needed

### 13.3 LLM processing

The backend sends the assembled context to the LLM.

The LLM analyzes:

- whether new work is implied
- whether existing tasks should be updated
- whether tasks may have been completed, blocked, or cancelled

The LLM returns proposal records only.

### 13.4 Proposal storage

Returned structured proposals are written to `task_proposals`.

The associated ingestion batch is marked processed or failed.

### 13.5 Review

The user reviews pending proposals in the UI.

They may:

- approve
- reject
- later, possibly edit before approving

### 13.6 Application

If approved, the backend applies the proposal in a transaction:

- creates or updates a task
- appends task status history if status changed
- updates proposal status and review metadata

### 13.7 Result

The system ends with:

- updated operational task state
- preserved proposal audit history
- preserved ingestion tracking

---

## 14. Component interaction outline

This section gives a more detailed outline of how the system’s components work together.

### A. Frontend UI

The frontend is responsible for user interaction and visualization of system state.

Primary views include:

- open task list
- task detail / edit view
- proposal review queue
- ingestion history / run controls
- experience list and experience folder linkage views
- future settings, prompt, and analytics views

The frontend should not contain business logic for proposal application or context assembly. Those responsibilities belong to the backend.

### B. API layer

The backend exposes HTTP endpoints used by the UI.

The API layer should:

- validate request shapes
- call domain services
- serialize DB records into UI-friendly responses
- enforce transactional write boundaries through service methods

### C. Domain services

Service modules own application logic such as:

- task creation and editing
- proposal review and application
- ingestion run orchestration
- vault file loading
- LLM context assembly
- connector execution

These services should prevent business logic from leaking into route handlers or ORM models.

### D. Connector layer

Connectors are responsible for talking to external systems.

Their job is to:

- authenticate
- fetch raw data
- extract the subset relevant to this system
- convert it into batch payloads suitable for `ingestion_batches`

They should not directly create tasks or proposals.

### E. Vault access layer

This layer is responsible for:

- resolving experience folder paths
- reading `overview.md` and `current_status.md`
- reading and later writing prompts, templates, and summaries
- keeping filesystem logic isolated from the rest of the app

### F. LLM orchestration layer

This layer is responsible for:

- building prompt payloads
- calling the model
- validating structured outputs
- translating outputs into proposal persistence calls
- recording any model metadata needed for debugging or traceability

### G. Persistence layer

The persistence layer, via SQLAlchemy, manages:

- relational mappings
- transactions
- migrations
- query helpers for active tasks, proposal queues, ingestion states, and experience metadata

---

## 15. Backend module and repository direction

A suggested repository layout, updated to reflect the current design:

| Path | Purpose |
|---|---|
| `frontend/` | React UI |
| `backend/app/api/` | FastAPI routes |
| `backend/app/models/` | SQLAlchemy models |
| `backend/app/services/` | Task, proposal, ingestion, and experience domain services |
| `backend/app/connectors/` | External source integrations |
| `backend/app/llm/` | Prompt loading, schema validation, and model orchestration |
| `backend/app/jobs/` | Scheduled jobs and manual ingestion triggers |
| `backend/app/vault/` | Markdown and filesystem helpers |
| `backend/app/db/` | Session management, migrations, base model config |
| `vault/` | User-owned Obsidian vault |
| `data/app.db` | SQLite database file |

### Important implementation note

This is a structural suggestion, not a locked final architecture. The exact package layout can change as implementation begins.

---

## 16. Vault content structure

The vault should remain useful even outside the application.

A likely folder structure:

| Folder | Content |
|---|---|
| `Experiences/` | Experience folders, one per experience |
| `Prompts/` | Editable LLM prompt files |
| `Templates/` | Markdown templates |
| `Daily/YYYY/` | Generated daily summaries |
| `Weekly/YYYY/` | Future weekly rollups |
| `Monthly/YYYY/` | Future monthly rollups |

### Important correction

The current experience design is folder-based with required `overview.md` and `current_status.md` files. Earlier ideas about experience markdown as single standalone records should be treated as stale unless reintroduced later.

### TODO — summary generation structure

The exact format of generated daily, weekly, and monthly summary documents has not been fully specified.

There will be an implementation here that:

- writes generated summaries into predictable vault locations
- keeps the files human-readable and AI-readable
- uses templates where helpful
- supports future rollups without forcing them into MVP scope

---

## 17. API direction

The backend will likely expose APIs along these lines.

### Tasks

- `GET /tasks`
- `POST /tasks`
- `PATCH /tasks/{id}`
- `POST /tasks/{id}/complete`

### Proposals

- `GET /proposals`
- `POST /proposals/{id}/approve`
- `POST /proposals/{id}/reject`
- future: `POST /proposals/{id}/edit-and-approve`

### Ingestion

- `POST /ingestion/run`
- `GET /ingestion/runs`
- `GET /ingestion/runs/{id}`
- `GET /ingestion/batches/{id}`

### Experiences

- `GET /experiences`
- `POST /experiences`
- `PATCH /experiences/{id}`
- `GET /experiences/{id}`

### Prompts / configuration

- `GET /prompts`
- `PATCH /prompts/{name}`

### Future analytics / summaries

- `GET /summaries/daily/{date}`
- `POST /summaries/regenerate`
- `GET /analytics/time`
- `GET /analytics/completions`

### API design note

These endpoints describe likely capability boundaries, not a final frozen API contract.

---

## 18. Scheduling and execution model

MVP execution should stay simple.

The system can support:

- manual ingestion runs triggered from the UI
- scheduled ingestion runs triggered by an in-process scheduler or cron-style command

Each run should:

1. create an `ingestion_run`
2. call the selected connectors
3. create one or more `ingestion_batches`
4. process pending batches into proposals
5. store the results and final statuses

### TODO — job orchestration and retry strategy

The exact retry logic, concurrency limits, and scheduling mechanism have not yet been decided.

There will be an implementation here that:

- allows both manual and scheduled runs
- handles connector failures gracefully
- prevents one broken source from corrupting the rest of the run
- supports rerunning failed work without destroying audit history

---

## 19. Connector strategy

The system is intended to ingest from multiple sources over time.

### Likely early sources

- email
- GitHub
- Slack
- calendar
- notes or manual imports

Earlier product and technical drafts also referenced Canvas, which still fits naturally as a future or early connector depending on implementation priorities.

### Connector contract

Each connector should:

- fetch raw external data
- filter to information that matters for the system
- produce minimally structured batch payloads
- attach source metadata needed for downstream reasoning
- avoid writing directly into tasks or proposals

### TODO — per-source acquisition design

The exact source-specific designs have not been scoped yet, including:

- how each connector authenticates
- how incremental sync is tracked
- how filtering works per source
- how noisy sources are constrained

There will be an implementation here that:

- supports reliable acquisition from each source
- minimizes duplicate ingestion
- provides enough metadata for human review and debugging
- can evolve source-by-source without destabilizing the core data model

---

## 20. Review and approval flow

The review flow is a first-class subsystem, not a side feature.

### Requirements

- all AI-generated task changes must appear in a pending state first
- the user must be able to review proposal details and rationale
- approval must be transactional and auditable
- rejection must preserve history

### Approval behavior

Approving a proposal should:

- validate the proposal against application rules
- create or update the associated task
- append status history if applicable
- mark the proposal as approved
- record who reviewed it and when

### Rejection behavior

Rejecting a proposal should:

- mark it rejected
- preserve the original proposal content and reason summary
- avoid mutating tasks

### TODO — proposal conflict handling

The system has not yet fully defined how to handle cases where:

- two proposals target the same task
- a task changes after a proposal is generated but before it is reviewed
- a proposal becomes stale due to later ingestion

There will be an implementation here that:

- detects conflicting or outdated proposals
- lets newer proposals supersede older ones where appropriate
- preserves a clear audit trail of why a proposal was no longer valid

---

## 21. Security and local operation considerations

- secrets should not be stored in the vault
- credentials should be stored in environment variables or another local secret mechanism
- the SQLite DB should remain separate from the git-tracked vault
- the app should degrade gracefully offline except when live connector sync is required
- only the minimum necessary context should be sent to the LLM
- raw payload retention should be bounded to what is needed for debugging and reprocessing

### TODO — privacy and retention policy

The exact retention policy for raw payloads, prompt inputs, and model outputs has not yet been defined.

There will be an implementation here that:

- bounds retained data appropriately
- preserves enough information for debugging and audits
- minimizes unnecessary long-term storage of sensitive external data

---

## 22. Non-functional requirements

The system should aim for:

- trustworthy and legible review-heavy workflows
- low operational complexity for local use
- deterministic schema validation around AI outputs
- strong auditability for applied and rejected changes
- graceful handling of failed connectors or failed model calls
- an architecture that can grow without rewriting the core trust boundary

---

## 23. Implementation order

A revised staged plan based on the current design:

| Stage | Focus |
|---|---|
| 1 | Define SQLAlchemy models for experiences, tasks, task history, proposals, ingestion runs, and ingestion batches |
| 2 | Implement core backend services and manual task CRUD |
| 3 | Implement experience management tied to folder-based vault structure |
| 4 | Implement proposal review and approval flow |
| 5 | Implement ingestion run creation and batch persistence |
| 6 | Implement context assembly from active tasks and active experience markdown files |
| 7 | Implement structured LLM proposal generation and persistence |
| 8 | Add initial connectors and scheduled runs |
| 9 | Add summaries, analytics, and later higher-order workflows |

### Important sequencing note

The review boundary and simple ingestion model should be working before the system invests heavily in broad source coverage.

---

## 24. Out-of-scope or not-yet-scoped areas

The following areas are intentionally not fully specified yet:

- the exact LLM call pattern and tool/function calling design
- the exact schema and heuristics for proposal reconciliation
- source-by-source ingestion implementations
- summary generation logic beyond broad intent
- analytics/time-tracking data model and UX
- advanced experience metadata or hierarchy
- automatic approval of low-risk changes

For each of these, the current plan is to leave explicit implementation space rather than locking in a design too early.

---

## 25. Model relationship overview

```text
experiences
  -> tasks
     -> task_status_history

ingestion_runs
  -> ingestion_batches
     -> task_proposals
        -> tasks
```

### Relationship summary

- `tasks.experience_id` links tasks to experiences
- `task_status_history.task_id` links history to tasks
- `task_proposals.task_id` optionally points to an existing task being modified
- `task_proposals.ingestion_batch_id` links proposals to the batch that generated them
- `ingestion_batches.ingestion_run_id` links batches to the parent run

---

## 26. Technical summary

This system is a Python-first, local-first architecture built around a strict separation of concerns:

- **database for structured operational state**
- **Obsidian markdown for narrative context**
- **ingestion batches for raw external signals**
- **LLM-generated proposals for AI assistance**
- **human review before any task mutation**

That separation is what keeps the architecture simple, auditable, and adaptable.

The current database proposal provides the clearest and most up-to-date foundation, and the technical structure in this document is designed to support it without reintroducing stale assumptions from earlier drafts.
