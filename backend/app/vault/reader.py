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

    def list_experiences(self) -> list[str]:
        """Return relative folder paths for all experiences in the vault.

        Walks vault/Experiences/{section}/{experience} two levels deep.
        Returns paths like ["Class/cpp", "Projects/task_manager"].
        """
        experiences_dir = self.root / "Experiences"
        if not experiences_dir.is_dir():
            return []
        paths: list[str] = []
        for section in sorted(experiences_dir.iterdir()):
            if not section.is_dir():
                continue
            for experience in sorted(section.iterdir()):
                if not experience.is_dir():
                    continue
                paths.append(f"{section.name}/{experience.name}")
        return paths

    def experience_path_exists(self, folder_path: str) -> bool:
        """Return True if vault/Experiences/{folder_path} is an existing directory."""
        path = self.root / "Experiences" / folder_path
        return path.is_dir()

    def list_prompts(self) -> list[str]:
        """Return prompt names (without .md extension) for all prompts in vault/Prompts/.

        Names are relative to vault/Prompts/, e.g. ["system", "sources/github"].
        """
        prompts_dir = self.root / "Prompts"
        if not prompts_dir.is_dir():
            return []
        return sorted(
            str(p.relative_to(prompts_dir).with_suffix(""))
            for p in prompts_dir.rglob("*.md")
            if p.name != "README.md"
        )

    def read_prompt(self, name: str) -> str:
        """Read vault/Prompts/{name}.md. Raises FileNotFoundError if missing."""
        path = self.root / "Prompts" / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    def write_prompt(self, name: str, content: str) -> None:
        """Write content to vault/Prompts/{name}.md, creating parent dirs as needed."""
        path = self.root / "Prompts" / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_daily_summary(self, date_str: str, content: str) -> None:
        # TODO: write to self.root / "Daily" / date_str[:4] / f"{date_str}.md"
        raise NotImplementedError
