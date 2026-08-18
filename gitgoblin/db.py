from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .models import Entity, FrontierSignal, Observation, Opportunity, ScanRun


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS observations (
  observation_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  source_family TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  actor_id TEXT,
  action TEXT NOT NULL,
  target_id TEXT,
  occurred_at TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  sector TEXT,
  evidence_sha256 TEXT NOT NULL,
  is_test_fixture INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_obs_target_time ON observations(target_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_obs_actor_time ON observations(actor_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_obs_sector ON observations(sector);

CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  name TEXT NOT NULL,
  source TEXT NOT NULL,
  url TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
  signal_id TEXT PRIMARY KEY,
  target_id TEXT NOT NULL,
  sector TEXT NOT NULL,
  technical_alpha REAL NOT NULL,
  confidence REAL NOT NULL,
  detected_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signals_score ON signals(technical_alpha DESC);

CREATE TABLE IF NOT EXISTS opportunities (
  opportunity_id TEXT PRIMARY KEY,
  signal_id TEXT NOT NULL,
  sector TEXT NOT NULL,
  decision TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opps_decision ON opportunities(decision, created_at DESC);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  sector TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS seeds (
  sector TEXT NOT NULL,
  username TEXT NOT NULL,
  added_at TEXT NOT NULL,
  PRIMARY KEY (sector, username)
);

CREATE TABLE IF NOT EXISTS source_cursors (
  source TEXT NOT NULL,
  sector TEXT NOT NULL,
  cursor_key TEXT NOT NULL,
  cursor_value TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (source, sector, cursor_key)
);

CREATE TABLE IF NOT EXISTS source_health (
  source TEXT NOT NULL,
  sector TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'UNKNOWN',
  last_success_at TEXT,
  last_failure_at TEXT,
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (source, sector)
);

CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  source_url TEXT NOT NULL,
  content_type TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  stored_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifacts_sha ON artifacts(content_sha256);

CREATE TABLE IF NOT EXISTS schema_versions (
  version TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scoring_versions (
  version TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  config_hash TEXT NOT NULL,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provenance_chain (
  provenance_id TEXT PRIMARY KEY,
  observation_id TEXT NOT NULL,
  parent_provenance_id TEXT,
  action TEXT NOT NULL,
  actor TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  metadata_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_provenance_obs ON provenance_chain(observation_id);
"""


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def add_observations(self, observations: Iterable[Observation]) -> int:
        added = 0
        with self.connect() as conn:
            for obs in observations:
                cur = conn.execute(
                    """INSERT OR IGNORE INTO observations
                    (observation_id,source,source_family,entity_type,entity_id,actor_id,action,target_id,
                     occurred_at,observed_at,sector,evidence_sha256,is_test_fixture,payload_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        obs.observation_id, obs.source, obs.source_family, obs.entity_type, obs.entity_id,
                        obs.actor_id, obs.action, obs.target_id, obs.occurred_at.isoformat(),
                        obs.observed_at.isoformat(), obs.sector, obs.evidence.artifact_sha256,
                        1 if obs.is_test_fixture else 0, obs.model_dump_json(),
                    ),
                )
                added += int(cur.rowcount > 0)
        return added

    def upsert_entity(self, entity: Entity) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO entities(entity_id,entity_type,name,source,url,first_seen_at,last_seen_at,payload_json)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(entity_id) DO UPDATE SET
                  name=excluded.name, source=excluded.source, url=excluded.url,
                  last_seen_at=excluded.last_seen_at, payload_json=excluded.payload_json""",
                (
                    entity.entity_id, entity.entity_type, entity.name, entity.source, entity.url,
                    entity.first_seen_at.isoformat(), entity.last_seen_at.isoformat(), entity.model_dump_json(),
                ),
            )

    def get_entity(self, entity_id: str) -> Entity | None:
        with self.connect() as conn:
            row = conn.execute("SELECT payload_json FROM entities WHERE entity_id=?", (entity_id,)).fetchone()
        return Entity.model_validate_json(row["payload_json"]) if row else None

    def observations(self, *, sector: str | None = None, target_id: str | None = None, include_test: bool = False) -> list[Observation]:
        where, args = [], []
        if sector:
            where.append("sector=?"); args.append(sector)
        if target_id:
            where.append("target_id=?"); args.append(target_id)
        if not include_test:
            where.append("is_test_fixture=0")
        sql = "SELECT payload_json FROM observations"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY occurred_at ASC"
        with self.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [Observation.model_validate_json(r["payload_json"]) for r in rows]

    def actors_for_sector(self, sector: str, include_test: bool = False) -> set[str]:
        test_clause = "" if include_test else " AND is_test_fixture=0"
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT DISTINCT actor_id FROM observations WHERE sector=? AND actor_id IS NOT NULL{test_clause}",
                (sector,),
            ).fetchall()
        return {r[0] for r in rows}

    def add_signal(self, signal: FrontierSignal) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO signals(signal_id,target_id,sector,technical_alpha,confidence,detected_at,payload_json) VALUES(?,?,?,?,?,?,?)",
                (signal.signal_id, signal.target_id, signal.sector, signal.technical_alpha, signal.confidence,
                 signal.detected_at.isoformat(), signal.model_dump_json()),
            )
        return bool(cur.rowcount)

    def signals(self, sector: str | None = None, limit: int = 100) -> list[FrontierSignal]:
        sql, args = "SELECT payload_json FROM signals", []
        if sector:
            sql += " WHERE sector=?"; args.append(sector)
        sql += " ORDER BY technical_alpha DESC, detected_at DESC LIMIT ?"; args.append(limit)
        with self.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [FrontierSignal.model_validate_json(r["payload_json"]) for r in rows]

    def add_opportunity(self, opp: Opportunity) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO opportunities(opportunity_id,signal_id,sector,decision,created_at,payload_json) VALUES(?,?,?,?,?,?)",
                (opp.opportunity_id, opp.signal_id, opp.sector, opp.decision, opp.created_at.isoformat(), opp.model_dump_json()),
            )
        return bool(cur.rowcount)

    def opportunities(self, sector: str | None = None, limit: int = 100) -> list[Opportunity]:
        sql, args = "SELECT payload_json FROM opportunities", []
        if sector:
            sql += " WHERE sector=?"; args.append(sector)
        sql += " ORDER BY created_at DESC LIMIT ?"; args.append(limit)
        with self.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [Opportunity.model_validate_json(r["payload_json"]) for r in rows]

    def add_seed(self, sector: str, username: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO seeds(sector,username,added_at) VALUES(?,?,?)",
                (sector, username, datetime.now(timezone.utc).isoformat()),
            )

    def seeds(self, sector: str) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT username FROM seeds WHERE sector=? ORDER BY username", (sector,)).fetchall()
        return [r[0] for r in rows]

    def save_run(self, run: ScanRun) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO runs(run_id,sector,status,started_at,finished_at,payload_json) VALUES(?,?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET status=excluded.status, finished_at=excluded.finished_at,
                payload_json=excluded.payload_json""",
                (run.run_id, run.sector, run.status, run.started_at.isoformat(),
                 run.finished_at.isoformat() if run.finished_at else None, run.model_dump_json()),
            )

    def get_cursor(self, source: str, sector: str, cursor_key: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT cursor_value FROM source_cursors WHERE source=? AND sector=? AND cursor_key=?",
                (source, sector, cursor_key),
            ).fetchone()
        return row["cursor_value"] if row else None

    def set_cursor(self, source: str, sector: str, cursor_key: str, cursor_value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO source_cursors(source,sector,cursor_key,cursor_value,updated_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(source,sector,cursor_key) DO UPDATE SET cursor_value=excluded.cursor_value, updated_at=excluded.updated_at""",
                (source, sector, cursor_key, cursor_value, datetime.now(timezone.utc).isoformat()),
            )

    def update_source_health(self, source: str, sector: str, *, success: bool, error: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT consecutive_failures FROM source_health WHERE source=? AND sector=?",
                (source, sector),
            ).fetchone()
            old_failures = row["consecutive_failures"] if row else 0
            failures = 0 if success else old_failures + 1
            status = "HEALTHY" if success else "DEGRADED" if failures < 3 else "UNHEALTHY"
            conn.execute(
                """INSERT INTO source_health(source,sector,status,last_success_at,last_failure_at,consecutive_failures,last_error,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(source,sector) DO UPDATE SET
                  status=excluded.status,
                  last_success_at=CASE WHEN ?='HEALTHY' THEN excluded.last_success_at ELSE last_success_at END,
                  last_failure_at=CASE WHEN ?!='HEALTHY' THEN excluded.last_failure_at ELSE last_failure_at END,
                  consecutive_failures=excluded.consecutive_failures,
                  last_error=excluded.last_error,
                  updated_at=excluded.updated_at""",
                (source, sector, status,
                 now if success else None, now if not success else None,
                 failures, error, now, status, status),
            )

    def get_source_health(self, source: str | None = None, sector: str | None = None) -> list[dict]:
        where, args = [], []
        if source:
            where.append("source=?"); args.append(source)
        if sector:
            where.append("sector=?"); args.append(sector)
        sql = "SELECT * FROM source_health"
        if where:
            sql += " WHERE " + " AND ".join(where)
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def store_artifact(self, artifact_id: str, source: str, source_url: str, content_type: str, content_sha256: str, size_bytes: int, payload: dict) -> bool:
        try:
            with self.connect() as conn:
                conn.execute(
                    """INSERT INTO artifacts(artifact_id,source,source_url,content_type,content_sha256,size_bytes,stored_at,payload_json)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (artifact_id, source, source_url, content_type, content_sha256, size_bytes,
                     datetime.now(timezone.utc).isoformat(), json.dumps(payload, sort_keys=True)),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def get_artifact(self, artifact_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT payload_json FROM artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def find_artifact_by_sha(self, sha256: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT payload_json FROM artifacts WHERE content_sha256=?", (sha256,)).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def add_provenance(self, provenance_id: str, observation_id: str, action: str, actor: str, parent_provenance_id: str | None = None, metadata: dict | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO provenance_chain(provenance_id,observation_id,parent_provenance_id,action,actor,timestamp,metadata_json)
                VALUES(?,?,?,?,?,?,?)""",
                (provenance_id, observation_id, parent_provenance_id, action, actor,
                 datetime.now(timezone.utc).isoformat(), json.dumps(metadata, sort_keys=True) if metadata else None),
            )

    def get_provenance_chain(self, observation_id: str) -> list[dict]:
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM provenance_chain WHERE observation_id=? ORDER BY timestamp ASC",
                (observation_id,),
            ).fetchall()]

    def observations_by_time_window(self, sector: str, since: str, until: str | None = None) -> list[Observation]:
        where = ["sector=?", "occurred_at>=?"]
        args: list = [sector, since]
        if until:
            where.append("occurred_at<=?"); args.append(until)
        sql = f"SELECT payload_json FROM observations WHERE {' AND '.join(where)} ORDER BY occurred_at ASC"
        with self.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [Observation.model_validate_json(r["payload_json"]) for r in rows]

    def stale_observations(self, sector: str, stale_days: int = 90) -> list[Observation]:
        cutoff = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT payload_json FROM observations
                WHERE sector=? AND is_test_fixture=0
                AND julianday(?) - julianday(observed_at) > ?
                ORDER BY observed_at ASC""",
                (sector, cutoff, stale_days),
            ).fetchall()
        return [Observation.model_validate_json(r["payload_json"]) for r in rows]

    def signal_version_stats(self, sector: str | None = None) -> dict:
        where, args = [], []
        if sector:
            where.append("sector=?"); args.append(sector)
        sql = "SELECT COUNT(*) as total, AVG(technical_alpha) as avg_alpha, MAX(detected_at) as latest FROM signals"
        if where:
            sql += " WHERE " + " AND ".join(where)
        with self.connect() as conn:
            row = conn.execute(sql, args).fetchone()
        return dict(row) if row else {"total": 0, "avg_alpha": 0, "latest": None}
