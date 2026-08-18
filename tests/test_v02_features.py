"""Tests for V0.2 features: source tracking, CAS, provenance, replay, verification."""
import json
import tempfile
from pathlib import Path

import pytest
from gitgoblin.db import Store
from gitgoblin.hashing import sha256_json
from gitgoblin.models import Entity, Observation, evidence_for_payload, utcnow
from gitgoblin.pipeline.signals import SignalEngine
from gitgoblin.settings import AppSettings, SectorProfile
from gitgoblin.verify import (
    BuildCertificate, CommandReceipt, VerificationRun,
    compute_tree_hash, compute_source_manifest, run_command, verify, save_certificate,
)


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.db")


@pytest.fixture
def settings():
    return AppSettings()


@pytest.fixture
def profile():
    return SectorProfile(id="test", description="test sector", keywords=["test"])


# --- Source Cursors & Health ---

def test_cursor_set_and_get(store):
    store.set_cursor("github", "ai", "last_event_id", "12345")
    assert store.get_cursor("github", "ai", "last_event_id") == "12345"


def test_cursor_update(store):
    store.set_cursor("github", "ai", "last_event_id", "12345")
    store.set_cursor("github", "ai", "last_event_id", "12346")
    assert store.get_cursor("github", "ai", "last_event_id") == "12346"


def test_cursor_missing(store):
    assert store.get_cursor("github", "ai", "nonexistent") is None


def test_source_health_healthy(store):
    store.update_source_health("github", "ai", success=True)
    health = store.get_source_health("github", "ai")
    assert len(health) == 1
    assert health[0]["status"] == "HEALTHY"
    assert health[0]["consecutive_failures"] == 0


def test_source_health_degraded(store):
    for _ in range(2):
        store.update_source_health("github", "ai", success=False, error="rate limit")
    health = store.get_source_health("github", "ai")
    assert health[0]["status"] == "DEGRADED"
    assert health[0]["consecutive_failures"] == 2


def test_source_health_unhealthy(store):
    for _ in range(3):
        store.update_source_health("github", "ai", success=False, error="timeout")
    health = store.get_source_health("github", "ai")
    assert health[0]["status"] == "UNHEALTHY"
    assert health[0]["consecutive_failures"] == 3


def test_source_health_recovery(store):
    store.update_source_health("github", "ai", success=False, error="timeout")
    store.update_source_health("github", "ai", success=False, error="timeout")
    store.update_source_health("github", "ai", success=True)
    health = store.get_source_health("github", "ai")
    assert health[0]["status"] == "HEALTHY"
    assert health[0]["consecutive_failures"] == 0


def test_source_health_filter(store):
    store.update_source_health("github", "ai", success=True)
    store.update_source_health("arxiv", "ai", success=True)
    assert len(store.get_source_health(source="github")) == 1
    assert len(store.get_source_health(sector="ai")) == 2


# --- Artifact Storage (CAS) ---

def test_store_and_get_artifact(store):
    payload = {"key": "value"}
    store.store_artifact("art_1", "github", "https://api.github.com/test", "application/json", "sha256:abc", 100, payload)
    result = store.get_artifact("art_1")
    assert result is not None
    assert result["key"] == "value"


def test_artifact_duplicate_ignored(store):
    store.store_artifact("art_1", "github", "https://api.github.com/test", "application/json", "sha256:abc", 100, {"v": 1})
    store.store_artifact("art_1", "github", "https://api.github.com/test", "application/json", "sha256:abc", 100, {"v": 2})
    result = store.get_artifact("art_1")
    assert result["v"] == 1  # first write wins


def test_find_artifact_by_sha(store):
    store.store_artifact("art_1", "github", "https://api.github.com/test", "application/json", "sha256:abc123", 100, {"data": "test"})
    result = store.find_artifact_by_sha("sha256:abc123")
    assert result is not None
    assert result["data"] == "test"


def test_artifact_not_found(store):
    assert store.get_artifact("nonexistent") is None
    assert store.find_artifact_by_sha("sha256:nonexistent") is None


# --- Provenance Chain ---

def test_provenance_chain(store):
    obs = Observation(
        source="github", source_family="code_host", entity_type="repository",
        entity_id="test/repo", action="push", target_id="test/repo",
        occurred_at=utcnow(), observed_at=utcnow(), sector="ai",
        evidence=evidence_for_payload({"test": True}),
    )
    store.add_observations([obs])

    store.add_provenance("prov_1", obs.observation_id, "collected", "github_collector")
    store.add_provenance("prov_2", obs.observation_id, "scored", "signal_engine", parent_provenance_id="prov_1")

    chain = store.get_provenance_chain(obs.observation_id)
    assert len(chain) == 2
    assert chain[0]["action"] == "collected"
    assert chain[1]["action"] == "scored"
    assert chain[1]["parent_provenance_id"] == "prov_1"


def test_provenance_duplicate_ignored(store):
    store.add_provenance("prov_1", "obs_1", "collected", "github_collector")
    store.add_provenance("prov_1", "obs_1", "collected", "github_collector")
    chain = store.get_provenance_chain("obs_1")
    assert len(chain) == 1


# --- Stale Data Detection ---

def test_stale_observations(store):
    obs = Observation(
        source="github", source_family="code_host", entity_type="repository",
        entity_id="test/repo", action="push", target_id="test/repo",
        occurred_at=utcnow(), observed_at=utcnow(), sector="ai",
        evidence=evidence_for_payload({"test": True}),
    )
    store.add_observations([obs])
    stale = store.stale_observations("ai", stale_days=0)
    assert len(stale) == 1  # immediately stale with 0 days


# --- Deterministic Replay ---

def test_replay_observations_by_time_window(store):
    obs = Observation(
        source="github", source_family="code_host", entity_type="repository",
        entity_id="test/repo", action="push", target_id="test/repo",
        occurred_at=utcnow(), observed_at=utcnow(), sector="ai",
        evidence=evidence_for_payload({"test": True}),
    )
    store.add_observations([obs])
    window = store.observations_by_time_window("ai", "2020-01-01T00:00:00+00:00")
    assert len(window) == 1


def test_signal_version_stats(store):
    stats = store.signal_version_stats("ai")
    assert stats["total"] == 0
    assert stats["avg_alpha"] is None or stats["avg_alpha"] == 0


# --- Verification Model ---

def test_command_receipt_hash_deterministic():
    r1 = CommandReceipt("echo hi", 0, "sha256:a", "sha256:b", 100, "2026-01-01T00:00:00+00:00")
    r2 = CommandReceipt("echo hi", 0, "sha256:a", "sha256:b", 100, "2026-01-01T00:00:00+00:00")
    assert r1.receipt_hash == r2.receipt_hash


def test_command_receipt_different_input():
    r1 = CommandReceipt("echo hi", 0, "sha256:a", "sha256:b", 100, "2026-01-01T00:00:00+00:00")
    r2 = CommandReceipt("echo lo", 0, "sha256:a", "sha256:b", 100, "2026-01-01T00:00:00+00:00")
    assert r1.receipt_hash != r2.receipt_hash


def test_run_command_success(tmp_path):
    receipt = run_command("echo hello", tmp_path)
    assert receipt.exit_code == 0
    assert receipt.stdout_hash.startswith("sha256:")
    assert receipt.duration_ms >= 0


def test_run_command_failure(tmp_path):
    receipt = run_command("false", tmp_path)
    assert receipt.exit_code != 0


def test_compute_tree_hash(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.py").write_text("print('hi')")
    h = compute_tree_hash(tmp_path)
    assert h.startswith("sha256:")


def test_compute_tree_hash_deterministic(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    h1 = compute_tree_hash(tmp_path)
    h2 = compute_tree_hash(tmp_path)
    assert h1 == h2


def test_compute_source_manifest(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    manifest = compute_source_manifest(tmp_path)
    assert manifest["file_count"] == 1
    assert "a.txt" in manifest["files"]
    assert len(manifest["files"]["a.txt"]["sha256"]) == 64  # hex hash


def test_verify_produces_certificate(tmp_path):
    (tmp_path / "test.py").write_text("print('ok')")
    cert = verify(tmp_path, ["echo test"], schema_version="v0.2", scoring_version="v1.0")
    assert cert.schema_version == "v0.2"
    assert cert.scoring_version == "v1.0"
    assert cert.certificate_id.startswith("cert_")
    assert len(cert.source_manifest_hash) == 64  # hex hash
    assert cert.source_tree_hash.startswith("sha256:")
    assert len(cert.command_receipt_hashes) == 1


def test_verify_failing_command(tmp_path):
    cert = verify(tmp_path, ["false"])
    assert cert.certificate_id.startswith("cert_")
    # Certificate is still produced even if commands fail


def test_save_certificate(tmp_path):
    cert = verify(tmp_path, ["echo ok"])
    cert_path = save_certificate(cert, tmp_path / "build")
    assert cert_path.exists()
    loaded = json.loads(cert_path.read_text())
    assert loaded["certificate_id"] == cert.certificate_id
    assert loaded["schema_version"] == "v0.2"


# --- Schema Versions ---

def test_schema_version_tracking(store):
    with store.connect() as conn:
        conn.execute("INSERT INTO schema_versions(version, description, applied_at) VALUES(?,?,?)",
                      ("v0.2", "V0.2 features", utcnow().isoformat()))
        row = conn.execute("SELECT * FROM schema_versions WHERE version='v0.2'").fetchone()
    assert row is not None


def test_scoring_version_tracking(store):
    with store.connect() as conn:
        conn.execute("INSERT INTO scoring_versions(version, description, config_hash, applied_at) VALUES(?,?,?,?)",
                      ("v1.0", "Initial scoring", sha256_json({"test": True}), utcnow().isoformat()))
        row = conn.execute("SELECT * FROM scoring_versions WHERE version='v1.0'").fetchone()
    assert row is not None
