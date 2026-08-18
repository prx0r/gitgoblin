"""Invariant tests — prove system properties hold."""
import hashlib
import json
import tempfile
from pathlib import Path

import pytest
from gitgoblin.db import Store
from gitgoblin.hashing import canonical_json, sha256_json, stable_id
from gitgoblin.mechanisms import extract_mechanisms
from gitgoblin.agent_context import detect_context_files, extract_practices
from gitgoblin.models import (
    Entity, Observation, FrontierSignal, Opportunity,
    ScanRun, evidence_for_payload, utcnow,
)


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "invariant.db")


def test_observation_ids_unique(store):
    """Every observation must have a unique ID."""
    ids = set()
    for i in range(50):
        obs = Observation(
            source="test", source_family="test", entity_type="paper",
            entity_id=f"p{i}", action="published",
            occurred_at=utcnow(), observed_at=utcnow(),
            evidence=evidence_for_payload({"test": True}),
        )
        assert obs.observation_id not in ids
        ids.add(obs.observation_id)


def test_sha256_deterministic():
    """Same input must produce same hash."""
    h1 = sha256_json({"a": 1, "b": 2})
    h2 = sha256_json({"b": 2, "a": 1})
    assert h1 == h2


def test_sha256_different_input():
    """Different input must produce different hash."""
    h1 = sha256_json({"a": 1})
    h2 = sha256_json({"a": 2})
    assert h1 != h2


def test_stable_id_deterministic():
    """Stable IDs must be deterministic."""
    s1 = stable_id("test", {"x": 1})
    s2 = stable_id("test", {"x": 1})
    assert s1 == s2


def test_stable_id_unique():
    """Different inputs must produce different IDs."""
    s1 = stable_id("test", {"x": 1})
    s2 = stable_id("test", {"x": 2})
    assert s1 != s2


def test_mechanism_extraction_deterministic():
    """Same input must produce same mechanisms."""
    files = {"test.py": "deterministic testing reproducible seed schedule"}
    m1 = extract_mechanisms(files)
    m2 = extract_mechanisms(files)
    assert len(m1) == len(m2)
    assert [m.name for m in m1] == [m.name for m in m2]


def test_mechanism_extraction_requires_keywords():
    """Single keyword match should not produce a mechanism."""
    files = {"test.py": "deterministic"}
    mechanisms = extract_mechanisms(files)
    assert len(mechanisms) == 0


def test_context_detection_exact():
    """File detection must match exact patterns."""
    paths = ["AGENTS.md", "agents.md", "AGENTS.MD"]
    contexts = detect_context_files(paths)
    assert len(contexts) == 1
    assert contexts[0]["path"] == "AGENTS.md"


def test_practices_extraction():
    """Practice extraction must find relevant patterns."""
    content = "Always run pytest. Never use bare except. Rate limit API calls."
    practices = extract_practices(content, "agents_md")
    assert len(practices) >= 2
