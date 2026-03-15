# Experiences

Each experience (project, class, job, club, or other major commitment)
lives in its own subfolder here.

## Folder structure

```
Experiences/
└── <experience-slug>/
    ├── overview.md         ← what this experience is and its long-term goals
    └── current_status.md  ← current work, priorities, and blockers
```

Both files are **required**. They are loaded into the LLM prompt for
every active experience during ingestion processing. Keep them concise
and up to date.

## Creating an experience

Use the Experiences page in the app — it will scaffold the folder and
template files for you. Or copy a folder manually and register it via
the API.

## Active vs inactive

The `active` flag in the database controls whether an experience is
included in LLM context. Inactive experiences are archived but
preserved for historical reference.
