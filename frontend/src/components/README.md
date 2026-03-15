# components/

Shared UI components used across multiple pages.

## What goes here

- Reusable presentational components (buttons, badges, modals, form fields)
- Layout primitives (cards, containers, dividers)
- Any component used by more than one page

## What does NOT go here

- Page-level components → see `../pages/`
- API/data-fetching logic → see `../api/`
- One-off components used only within a single page (keep those co-located)

## TODO

Components will be added as pages are implemented. Likely candidates:
- `TaskCard` — displays a single task with status badge and priority
- `ProposalCard` — displays a proposal with approve/reject actions
- `StatusBadge` — colored badge for task/proposal status enum values
- `IngestionRunRow` — summary row for an ingestion run
