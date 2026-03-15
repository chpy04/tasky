"""Prompt management API routes.

Endpoints:
    GET    /prompts           List all prompt files in the vault
    PATCH  /prompts/{name}    Update a prompt file's content

Prompts are markdown files stored in vault/Prompts/. They are read at
runtime and injected into LLM context. Editing them here updates the
file on disk without requiring a code change.

TODO: implement route handlers using PromptService
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_prompts():
    # TODO: return all prompt names and content from vault/Prompts/
    raise NotImplementedError


@router.patch("/{prompt_name}")
def update_prompt(prompt_name: str):
    # TODO: write updated content to vault/Prompts/{prompt_name}.md
    raise NotImplementedError
