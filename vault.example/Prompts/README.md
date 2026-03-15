# Prompts

Editable LLM prompt files. These are loaded at runtime during ingestion
processing and can be updated from the Prompts page in the app without
any code changes.

## Adding a prompt

Create a new `.md` file in this folder. The filename (without extension)
becomes the prompt name accessible via the API.

## TODO

- Define and add the initial ingestion prompt (used to generate task proposals from a batch)
- Define and add the daily summary prompt (used to generate vault/Daily/ entries)
- Consider adding a system context prompt loaded in every call
