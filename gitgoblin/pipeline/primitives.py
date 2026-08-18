from __future__ import annotations

from dataclasses import dataclass

from gitgoblin.db import Store
from gitgoblin.models import FrontierSignal
from gitgoblin.settings import SectorProfile


@dataclass(frozen=True)
class PrimitiveCandidate:
    name: str
    confidence: float
    evidence_terms: tuple[str, ...]


DEFAULT_RULES: dict[str, list[str]] = {
    "durable-agent-state": ["checkpoint", "durable", "state", "replication", "transaction", "storage", "volume"],
    "agent-web-access": ["browser", "crawl", "scrape", "render", "playwright", "fetch", "web"],
    "execution-placement": ["sandbox", "vm", "container", "edge", "runtime", "compute", "wasm"],
    "verification-receipts": ["verify", "verification", "test", "eval", "proof", "audit", "trace"],
    "technical-intelligence-graph": ["graph", "search", "index", "knowledge", "dependency", "analytics", "trend"],
    "agent-orchestration": ["agent", "workflow", "orchestration", "scheduler", "queue", "retry", "supervisor"],
    "local-first-sync": ["local-first", "offline", "sync", "replication", "crdt", "edge"],
    "model-routing": ["model", "inference", "router", "llm", "provider", "latency", "token"],
}


class PrimitiveExtractor:
    def __init__(self, store: Store, profile: SectorProfile) -> None:
        self.store = store
        self.profile = profile

    def extract(self, signal: FrontierSignal) -> list[PrimitiveCandidate]:
        entity = self.store.get_entity(signal.target_id)
        text_parts = []
        if entity:
            text_parts += [entity.name, str(entity.attrs.get("description") or "")]
            text_parts += list(entity.attrs.get("topics") or [])
            text_parts += [str(entity.attrs.get("language") or "")]
        for obs in self.store.observations(sector=self.profile.id, target_id=signal.target_id):
            text_parts.extend(obs.tags)
            text_parts.append(str(obs.value.get("summary") or ""))
        text = " ".join(text_parts).lower()
        rules = dict(DEFAULT_RULES)
        rules.update(self.profile.primitive_rules)
        candidates: list[PrimitiveCandidate] = []
        for name, terms in rules.items():
            matched = tuple(sorted({t for t in terms if t.lower() in text}))
            if not matched:
                continue
            confidence = min(1.0, 0.35 + 0.13 * len(matched) + 0.15 * signal.technical_alpha)
            candidates.append(PrimitiveCandidate(name=name, confidence=round(confidence, 6), evidence_terms=matched))
        if not candidates:
            candidates.append(PrimitiveCandidate("emerging-software-primitive", 0.35, tuple()))
        return sorted(candidates, key=lambda c: c.confidence, reverse=True)
