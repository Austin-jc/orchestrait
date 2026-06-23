"""Configuration: runtime settings from `config.yaml`, secrets from the
environment (never from the file)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .types import Budget, WorkerSpec


class Secrets(BaseSettings):
    """API keys / tokens, read from env (or a local .env). Never logged."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    claude_code_oauth_token: str | None = None


class Defaults(BaseModel):
    budget: Budget = Field(default_factory=Budget)
    temperature: float = 0.2
    max_tokens: int = 1024


class Config(BaseModel):
    defaults: Defaults = Field(default_factory=Defaults)
    conductor_worker_id: int = 0
    workers: list[WorkerSpec] = Field(default_factory=list)
    prices: dict[str, dict[str, float]] = Field(default_factory=dict)


def load_config(path: str | Path = "config.yaml") -> Config:
    p = Path(path)
    if not p.exists():
        return Config()
    raw = yaml.safe_load(p.read_text()) or {}
    conductor = (raw.get("conductor") or {}).get("worker_id", 0)
    return Config(
        defaults=Defaults(**(raw.get("defaults") or {})),
        conductor_worker_id=conductor,
        workers=[WorkerSpec(**w) for w in (raw.get("workers") or [])],
        prices=raw.get("prices") or {},
    )
