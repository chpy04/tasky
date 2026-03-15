"""Prompt management service.

Prompts are markdown files stored in vault/Prompts/. They are read at
LLM call time and can be edited by the user via the UI without code
changes.

Responsibilities:
- list all prompt files (name + content)
- read a single prompt by name
- write updated content to a prompt file

These operations delegate to the vault reader for filesystem access.
"""
from app.vault.reader import VaultReader


class PromptService:
    def __init__(self, vault_reader: VaultReader) -> None:
        self.vault = vault_reader

    def list_prompts(self) -> list[dict]:
        # TODO: enumerate vault/Prompts/*.md; return [{name, content}, ...]
        raise NotImplementedError

    def get_prompt(self, name: str) -> str:
        # TODO: read vault/Prompts/{name}.md; raise 404 if missing
        raise NotImplementedError

    def update_prompt(self, name: str, content: str) -> None:
        # TODO: write content to vault/Prompts/{name}.md
        raise NotImplementedError
