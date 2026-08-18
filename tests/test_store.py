from datetime import datetime, timezone

from gitgoblin.db import Store
from gitgoblin.models import Observation, evidence_for_payload


def test_observation_insert_is_idempotent(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    obs = Observation(
        source="x", source_family="x", entity_type="repo", entity_id="repo:1", action="star",
        target_id="repo:1", occurred_at=datetime.now(timezone.utc), sector="ai",
        evidence=evidence_for_payload({"x": 1}),
    )
    assert store.add_observations([obs]) == 1
    assert store.add_observations([obs]) == 0
    assert len(store.observations(sector="ai")) == 1


def test_test_fixtures_are_excluded_by_default(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    obs = Observation(
        source="x", source_family="x", entity_type="repo", entity_id="repo:1", action="star",
        target_id="repo:1", occurred_at=datetime.now(timezone.utc), sector="ai",
        evidence=evidence_for_payload({"x": 1}), is_test_fixture=True,
    )
    store.add_observations([obs])
    assert store.observations(sector="ai") == []
    assert len(store.observations(sector="ai", include_test=True)) == 1
