from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from gitgoblin.db import Store
from gitgoblin.models import Entity, Observation, evidence_for_payload
from gitgoblin.settings import AppSettings, SectorProfile


@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    cfg = AppSettings(database_path=str(tmp_path / "gitgoblin.db"), artifact_dir=str(tmp_path / "artifacts"))
    cfg.scoring.min_experts = 2
    cfg.scoring.min_signal_score = 0.30
    return cfg


@pytest.fixture
def profile() -> SectorProfile:
    return SectorProfile(
        id="ai",
        description="test",
        seed_builders=["alpha"],
        keywords=["agent", "durable"],
        arxiv_queries=[],
        expertise_languages=["rust", "python"],
        primitive_rules={},
    )


@pytest.fixture
def populated_store(tmp_path: Path, profile: SectorProfile) -> Store:
    store = Store(tmp_path / "signals.db")
    now = datetime.now(timezone.utc)
    target = Entity(
        entity_id="github:repo:newco/frontier",
        entity_type="repository",
        name="newco/frontier",
        source="github",
        url="https://github.com/newco/frontier",
        attrs={
            "description": "Durable agent checkpoint storage with transactional replication",
            "topics": ["agent", "storage", "checkpoint"],
            "language": "Rust",
            "created_at": (now - timedelta(days=12)).isoformat(),
            "stars": 42,
            "license_spdx": "MIT",
        },
    )
    store.upsert_entity(target)
    actions = ["pull_request", "fork", "push"]
    families = ["code_host", "oss_index", "research_graph"]
    for i, name in enumerate(["alpha", "beta", "gamma"]):
        uid = f"github:user:{name}"
        store.upsert_entity(
            Entity(
                entity_id=uid,
                entity_type="developer",
                name=name,
                source="github",
                attrs={
                    "followers": 700 + i * 300,
                    "created_at": "2014-01-01T00:00:00Z",
                    "company": f"company-{i}",
                },
            )
        )
        own = f"github:repo:{name}/serious"
        store.upsert_entity(Entity(entity_id=own, entity_type="repository", name=own, source="github", attrs={"stars": 900, "language": "Rust"}))
        observations = [
            Observation(
                source="github", source_family="code_host", entity_type="repository", entity_id=own,
                actor_id=uid, action="owns", target_id=own, occurred_at=now - timedelta(days=200),
                value={"stars": 900, "language": "Rust"}, sector=profile.id,
                evidence=evidence_for_payload({"own": name}), is_test_fixture=True,
            ),
            Observation(
                source="fixture", source_family=families[i], entity_type="repository_interaction",
                entity_id=f"fixture:event:{i}", actor_id=uid, action=actions[i],
                target_id=target.entity_id, occurred_at=now - timedelta(days=i + 1),
                value={}, sector=profile.id, evidence=evidence_for_payload({"event": i}),
                quality={"temporal_precision": "event"}, is_test_fixture=True,
            ),
        ]
        store.add_observations(observations)
    return store
