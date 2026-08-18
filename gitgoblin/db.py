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
