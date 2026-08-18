from __future__ import annotations

import traceback
from datetime import datetime, timezone
from pathlib import Path

from gitgoblin.db import Store
from gitgoblin.hashing import sha256_json, stable_id
from gitgoblin.models import ScanRun
from gitgoblin.settings import AppSettings, SectorProfile
from gitgoblin.sources import ArxivCollector, GitHubCollector, HackerNewsCollector, OpenAlexCollector

from .opportunities import OpportunityEngine
from .signals import SignalEngine


class Scout:
    """Orchestrates one bounded frontier scan with evidence-preserving failure semantics."""

    def __init__(
        self,
        store: Store,
        settings: AppSettings,
        profile: SectorProfile,
        *,
        github: GitHubCollector | None = None,
        openalex: OpenAlexCollector | None = None,
        arxiv: ArxivCollector | None = None,
        hackernews: HackerNewsCollector | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.profile = profile
        self.github = github or GitHubCollector(settings)
        self.openalex = openalex or OpenAlexCollector(settings)
        self.arxiv = arxiv or ArxivCollector(settings)
        self.hackernews = hackernews or HackerNewsCollector(settings)

    def run(
        self,
        seeds: list[str] | None = None,
        *,
        expand_per_seed: int = 2,
        research: bool = True,
        include_test: bool = False,
    ) -> ScanRun:
        seeds = [s.lower() for s in (seeds or self.store.seeds(self.profile.id) or self.profile.seed_builders)]
        started = datetime.now(timezone.utc)
        run = ScanRun(run_id=stable_id("run", {"sector": self.profile.id, "seeds": seeds, "started": started.isoformat()}), sector=self.profile.id, seeds=seeds, started_at=started)
        self.store.save_run(run)
        log: list[dict] = []
        try:
            total = 0
            expanded: set[str] = set(seeds)
            for seed in seeds:
                self.store.add_seed(self.profile.id, seed)
                entities, observations = self.github.collect(seed, sector=self.profile.id)
                for entity in entities:
                    self.store.upsert_entity(entity)
                total += self.store.add_observations(observations)
                log.append({"source": "github", "seed": seed, "entities": len(entities), "observations": len(observations)})

                candidates = [
                    o.target_id.removeprefix("github:user:")
                    for o in observations
                    if o.action == "follow" and o.target_id and o.target_id.startswith("github:user:")
                ][:expand_per_seed]
                for candidate in candidates:
                    if candidate in expanded:
                        continue
                    expanded.add(candidate)
                    try:
                        ents2, obs2 = self.github.collect(candidate, sector=self.profile.id, pages=1)
                        for entity in ents2:
                            self.store.upsert_entity(entity)
                        total += self.store.add_observations(obs2)
                        log.append({"source": "github", "expanded": candidate, "entities": len(ents2), "observations": len(obs2)})
                    except Exception as exc:
                        log.append({"source": "github", "expanded": candidate, "error": str(exc)})

            if research:
                for query in self.profile.arxiv_queries[:3]:
                    try:
                        entities, observations = self.arxiv.collect(query, sector=self.profile.id)
                        for entity in entities:
                            self.store.upsert_entity(entity)
                        total += self.store.add_observations(observations)
                        log.append({"source": "arxiv", "query": query, "observations": len(observations)})
                    except Exception as exc:
                        log.append({"source": "arxiv", "query": query, "error": str(exc)})
                    try:
                        entities, observations = self.openalex.collect(query, sector=self.profile.id, days=45, max_pages=1)
                        for entity in entities:
                            self.store.upsert_entity(entity)
                        total += self.store.add_observations(observations)
                        log.append({"source": "openalex", "query": query, "observations": len(observations)})
                    except Exception as exc:
                        log.append({"source": "openalex", "query": query, "error": str(exc)})
                try:
                    entities, observations = self.hackernews.collect(self.profile.keywords[:12], sector=self.profile.id, max_items=40)
                    for entity in entities:
                        self.store.upsert_entity(entity)
                    total += self.store.add_observations(observations)
                    log.append({"source": "hackernews", "observations": len(observations)})
                except Exception as exc:
                    log.append({"source": "hackernews", "error": str(exc)})

            signal_engine = SignalEngine(self.store, self.settings, self.profile)
            signals = signal_engine.detect(include_test=include_test)
            signal_count = sum(1 for signal in signals if self.store.add_signal(signal))
            opp_engine = OpportunityEngine(self.store, self.settings, self.profile)
            opp_count = 0
            for signal in signals:
                for opp in opp_engine.derive(signal):
                    opp_count += int(self.store.add_opportunity(opp))
            run.observations_added = total
            run.signals_added = signal_count
            run.opportunities_added = opp_count
            run.status = "PASS"
        except Exception as exc:
            run.status = "FAIL"
            run.error = f"{exc}\n{traceback.format_exc(limit=8)}"
            raise
        finally:
            run.finished_at = datetime.now(timezone.utc)
            run.log_sha256 = sha256_json(log)
            self.store.save_run(run)
            self._write_run_log(run, log)
        return run

    def _write_run_log(self, run: ScanRun, log: list[dict]) -> None:
        path = Path(self.settings.artifact_dir) / "runs"
        path.mkdir(parents=True, exist_ok=True)
        payload = {"run": run.model_dump(mode="json"), "events": log}
        (path / f"{run.run_id}.json").write_text(__import__("json").dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
