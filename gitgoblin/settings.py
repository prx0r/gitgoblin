from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class GitHubSettings(BaseModel):
    token_env: str = "GITHUB_TOKEN"
    api_version: str = "2026-03-10"
    pages_per_seed: int = 2
    include_following: bool = True
    include_starred: bool = True
    include_events: bool = True
    include_repositories: bool = True


class ScoreSettings(BaseModel):
    recency_half_life_days: float = 21.0
    young_repo_days: float = 180.0
    min_experts: int = 2
    min_signal_score: float = 0.42
    build_threshold: float = 0.72
    research_threshold: float = 0.55
    watch_threshold: float = 0.38
    action_weights: dict[str, float] = Field(default_factory=lambda: {
        "follow": 0.12,
        "star": 0.25,
        "watch": 0.22,
        "fork": 0.55,
        "issue": 0.45,
        "pull_request": 0.82,
        "push": 0.88,
        "create": 0.75,
        "dependency": 0.92,
        "authored": 0.95,
        "cited": 0.65,
    })


class AppSettings(BaseModel):
    database_path: str = "data/gitgoblin.db"
    artifact_dir: str = "data/artifacts"
    user_agent: str = "GitGoblin/0.1 (+https://example.invalid/gitgoblin)"
    request_timeout_seconds: float = 20.0
    max_retries: int = 3
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    scoring: ScoreSettings = Field(default_factory=ScoreSettings)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "AppSettings":
        raw: dict[str, Any] = {}
        if path:
            with Path(path).open("r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
        return cls.model_validate(raw)

    def github_token(self) -> str | None:
        return os.getenv(self.github.token_env)


class SectorProfile(BaseModel):
    id: str
    description: str
    seed_builders: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    arxiv_queries: list[str] = Field(default_factory=list)
    expertise_languages: list[str] = Field(default_factory=list)
    primitive_rules: dict[str, list[str]] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "SectorProfile":
        with Path(path).open("r", encoding="utf-8") as fh:
            return cls.model_validate(yaml.safe_load(fh) or {})
