from __future__ import annotations

from datetime import datetime, timedelta, timezone

from gitgoblin.db import Store
from gitgoblin.integrations.cuntgoblin import opportunity_to_cuntgoblin, signal_to_market_observations
from gitgoblin.models import Entity, Observation, evidence_for_payload
from gitgoblin.pipeline.scout import Scout


class DeterministicGitHub:
    """Deterministic source simulator used only to exercise the full pipeline in tests."""

    def collect(self, username: str, *, sector: str, pages: int = 2):
        now = datetime.now(timezone.utc)
        uid = f"github:user:{username}"
        target_id = "github:repo:newco/frontier"
        own_id = f"github:repo:{username}/systems"
        idx = {"alpha": 0, "beta": 1, "gamma": 2}.get(username, 3)
        entities = [
            Entity(
                entity_id=uid,
                entity_type="developer",
                name=username,
                source="github",
                attrs={"followers": 1800 + idx * 200, "company": f"company-{idx}", "created_at": "2013-01-01T00:00:00Z"},
            ),
            Entity(
                entity_id=own_id,
                entity_type="repository",
                name=f"{username}/systems",
                source="github",
                attrs={"stars": 1400, "language": "Rust", "license_spdx": "MIT"},
            ),
            Entity(
                entity_id=target_id,
                entity_type="repository",
                name="newco/frontier",
                source="github",
                url="https://github.com/newco/frontier",
                attrs={
                    "stars": 57,
                    "language": "Rust",
                    "license_spdx": "MIT",
                    "created_at": (now - timedelta(days=10)).isoformat(),
                    "description": "Durable agent checkpoint storage using transactional replication",
                    "topics": ["agents", "checkpoint", "storage"],
                },
            ),
        ]
        action = ["pull_request", "fork", "push"][min(idx, 2)]
        observations = [
            Observation(
                source="github",
                source_family="code_host",
                entity_type="repository",
                entity_id=own_id,
                actor_id=uid,
                action="owns",
                target_id=own_id,
                occurred_at=now - timedelta(days=300),
                value={"stars": 1400, "language": "Rust"},
                sector=sector,
                evidence=evidence_for_payload({"owner": username, "repo": own_id}),
            ),
            Observation(
                source="github",
                source_family="code_host",
                entity_type="repository_interaction",
                entity_id=f"event:{username}",
                actor_id=uid,
                action=action,
                target_id=target_id,
                occurred_at=now - timedelta(days=idx + 1),
                value={},
                sector=sector,
                evidence=evidence_for_payload({"actor": username, "target": target_id, "action": action}),
                quality={"temporal_precision": "event"},
            ),
        ]
        return entities, observations


def test_full_scout_to_cuntgoblin_export(settings, profile, tmp_path):
    profile.seed_builders = ["alpha", "beta", "gamma"]
    store = Store(tmp_path / "e2e.db")
    scout = Scout(store, settings, profile, github=DeterministicGitHub())

    run = scout.run(seeds=profile.seed_builders, expand_per_seed=0, research=False)

    assert run.status == "PASS"
    assert run.observations_added >= 6
    signals = store.signals(sector="ai")
    opportunities = store.opportunities(sector="ai")
    assert signals, "full pipeline must emit at least one frontier signal"
    assert opportunities, "full pipeline must derive at least one opportunity"
    assert signals[0].target_id == "github:repo:newco/frontier"
    assert any(o.primitive == "durable-agent-state" for o in opportunities)

    market_records = signal_to_market_observations(signals[0])
    venture_opportunity = opportunity_to_cuntgoblin(opportunities[0])
    assert {r["metric"] for r in market_records} >= {"technical_alpha", "momentum", "novelty"}
    assert all(r["evidence"]["artifact_sha256"] for r in market_records)
    assert venture_opportunity["decision"] in {"BUILD", "RESEARCH", "WATCH", "REJECT"}

    run_log = tmp_path / "artifacts" / "runs" / f"{run.run_id}.json"
    assert run_log.exists(), "scout must write a reproducible run log"
    assert run.log_sha256
