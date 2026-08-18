from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .hashing import sha256_json, stable_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Evidence(BaseModel):
    source_url: str | None = None
    artifact_sha256: str
    retrieved_at: datetime = Field(default_factory=utcnow)
    source_record_id: str | None = None


class Observation(BaseModel):
    observation_id: str | None = None
    source: str
    source_family: str
    entity_type: str
    entity_id: str
    actor_id: str | None = None
    action: str
    target_id: str | None = None
    occurred_at: datetime
    observed_at: datetime = Field(default_factory=utcnow)
    value: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    sector: str | None = None
    evidence: Evidence
    quality: dict[str, Any] = Field(default_factory=dict)
    is_test_fixture: bool = False

    def model_post_init(self, __context: Any) -> None:
        if not self.observation_id:
            payload = self.model_dump(mode="json", exclude={"observation_id", "observed_at"})
            self.observation_id = stable_id("obs", payload)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return sorted({v.strip().lower() for v in value if v and v.strip()})


class Entity(BaseModel):
    entity_id: str
    entity_type: str
    name: str
    source: str
    url: str | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)
    first_seen_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)


class BuilderScore(BaseModel):
    builder_id: str
    score: float = Field(ge=0, le=1)
    components: dict[str, float]
    computed_at: datetime = Field(default_factory=utcnow)


class FrontierSignal(BaseModel):
    signal_id: str | None = None
    target_id: str
    sector: str
    technical_alpha: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    expert_count: int = Field(ge=0)
    independent_cluster_count: int = Field(ge=0)
    novelty: float = Field(ge=0, le=1)
    momentum: float = Field(ge=0, le=1)
    reasons: list[str]
    metrics: dict[str, Any]
    evidence_ids: list[str]
    detected_at: datetime = Field(default_factory=utcnow)

    def model_post_init(self, __context: Any) -> None:
        if not self.signal_id:
            basis = {
                "target": self.target_id,
                "sector": self.sector,
                "evidence": sorted(self.evidence_ids),
                "detected": self.detected_at.date().isoformat(),
            }
            self.signal_id = stable_id("sig", basis)


Decision = Literal["BUILD", "RESEARCH", "WATCH", "REJECT"]


class Opportunity(BaseModel):
    opportunity_id: str | None = None
    signal_id: str
    sector: str
    title: str
    problem: str
    primitive: str
    solution_hypotheses: list[str]
    scorecard: dict[str, float]
    decision: Decision
    evidence_ids: list[str]
    created_at: datetime = Field(default_factory=utcnow)

    def model_post_init(self, __context: Any) -> None:
        if not self.opportunity_id:
            self.opportunity_id = stable_id(
                "opp", {"signal": self.signal_id, "primitive": self.primitive, "title": self.title}
            )


class ScanRun(BaseModel):
    run_id: str
    sector: str
    seeds: list[str]
    started_at: datetime
    finished_at: datetime | None = None
    observations_added: int = 0
    signals_added: int = 0
    opportunities_added: int = 0
    status: Literal["RUNNING", "PASS", "FAIL"] = "RUNNING"
    error: str | None = None
    log_sha256: str | None = None


def evidence_for_payload(payload: Any, source_url: str | None = None, source_record_id: str | None = None) -> Evidence:
    return Evidence(
        source_url=source_url,
        artifact_sha256=sha256_json(payload),
        source_record_id=source_record_id,
    )
