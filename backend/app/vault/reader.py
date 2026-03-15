"""Vault filesystem helpers.

All reads and writes to the Obsidian vault go through this module.
Nothing else in the application should access vault files directly.

Responsibilities:
- resolve experience folder paths (relative to vault root)
- read overview.md and current_status.md for an experience
- scaffold a new experience folder from templates
- read prompt files from vault/Prompts/
- write prompt files
- read and write summary files (vault/Daily/, vault/Weekly/, etc.)
- read template files from vault/Templates/

The vault root is configured via settings.vault_path.
"""

from pathlib import Path

from app.config import settings


class VaultReader:
    def __init__(self, vault_path: str | None = None) -> None:
        self.root = Path(vault_path or settings.vault_path)

    def read_experience_file(self, folder_path: str, filename: str) -> str:
        """Read a file from an experience folder. Raises FileNotFoundError if missing."""
        path = self.root / "Experiences" / folder_path / filename
        if not path.exists():
            raise FileNotFoundError(f"Vault file not found: {path}")
        return path.read_text(encoding="utf-8")

    def scaffold_experience_folder(self, folder_path: str) -> None:
        """Create the experience folder and populate it from templates.

        Creates vault/Experiences/{folder_path}/overview.md and
        current_status.md using the files in vault/Templates/. If the
        templates are missing, empty placeholder files are written instead.
        """
        dest = self.root / "Experiences" / folder_path
        dest.mkdir(parents=True, exist_ok=True)

        for filename, template_name in (
            ("overview.md", "experience-overview.md"),
            ("current_status.md", "experience-current-status.md"),
        ):
            dest_file = dest / filename
            if dest_file.exists():
                continue
            template_path = self.root / "Templates" / template_name
            content = template_path.read_text(encoding="utf-8") if template_path.exists() else ""
            dest_file.write_text(content, encoding="utf-8")

    def experience_path_exists(self, folder_path: str) -> bool:
        """Return True if vault/Experiences/{folder_path} is an existing directory."""
        path = self.root / "Experiences" / folder_path
        return path.is_dir()

    def list_prompts(self) -> list[str]:
        # TODO: return list of .md filenames in self.root / "Prompts"
        raise NotImplementedError

    def read_prompt(self, name: str) -> str:
        # TODO: read self.root / "Prompts" / f"{name}.md"; raise if missing
        raise NotImplementedError

    def write_prompt(self, name: str, content: str) -> None:
        # TODO: write content to self.root / "Prompts" / f"{name}.md"
        raise NotImplementedError

    def write_daily_summary(self, date_str: str, content: str) -> None:
        # TODO: write to self.root / "Daily" / date_str[:4] / f"{date_str}.md"
        raise NotImplementedError
