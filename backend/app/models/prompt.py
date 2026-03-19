"""Prompt models for DB-backed prompt management.

Three models:
  Prompt            — the library of prompt texts
  PromptConfig      — a named configuration (exactly one is active at a time)
  PromptConfigEntry — junction: which source prompt each config uses per source type
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.ingestion_batch import SourceType


class PromptKind(str, enum.Enum):
    system = "system"
    source_context = "source_context"


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    kind: Mapped[PromptKind] = mapped_column(Enum(PromptKind), nullable=False)
    source_type: Mapped[SourceType | None] = mapped_column(Enum(SourceType), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    configs_as_system: Mapped[list["PromptConfig"]] = relationship(
        "PromptConfig",
        back_populates="system_prompt",
        foreign_keys="PromptConfig.system_prompt_id",
    )
    config_entries: Mapped[list["PromptConfigEntry"]] = relationship(
        "PromptConfigEntry", back_populates="prompt"
    )


class PromptConfig(Base):
    __tablename__ = "prompt_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    system_prompt_id: Mapped[int] = mapped_column(Integer, ForeignKey("prompts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    system_prompt: Mapped[Prompt] = relationship(
        "Prompt",
        back_populates="configs_as_system",
        foreign_keys=[system_prompt_id],
    )
    entries: Mapped[list["PromptConfigEntry"]] = relationship(
        "PromptConfigEntry", back_populates="config", cascade="all, delete-orphan"
    )


class PromptConfigEntry(Base):
    __tablename__ = "prompt_config_entries"
    __table_args__ = (UniqueConstraint("config_id", "source_type", name="uq_config_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_id: Mapped[int] = mapped_column(Integer, ForeignKey("prompt_configs.id"), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    prompt_id: Mapped[int] = mapped_column(Integer, ForeignKey("prompts.id"), nullable=False)

    config: Mapped[PromptConfig] = relationship("PromptConfig", back_populates="entries")
    prompt: Mapped[Prompt] = relationship("Prompt", back_populates="config_entries")
