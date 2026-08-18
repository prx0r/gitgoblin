from __future__ import annotations

from gitgoblin.db import Store
from gitgoblin.models import FrontierSignal, Opportunity
from gitgoblin.settings import AppSettings, SectorProfile

from .licensing import classify_license
from .primitives import PrimitiveCandidate, PrimitiveExtractor


HYPOTHESES: dict[str, list[str]] = {
    "durable-agent-state": [
        "Checkpoint/fork/resume state service for long-running coding and research agents",
        "Transactional shared workspace for parallel agent workers",
        "Local-first personal-agent state synchronization layer",
    ],
    "agent-web-access": [
        "Policy-aware web access router choosing API, fetch, browser render, authenticated session, or human handoff",
        "External synthetic health oracle for agent web tools",
    ],
    "execution-placement": [
        "Capability-aware execution router selecting local, VPS, edge, browser, or sandbox environments",
        "Environment compatibility sensor API for agent tasks",
    ],
    "verification-receipts": [
        "Independent outcome verifier for agent actions and deployments",
        "Machine-readable evidence receipt API for autonomous workflows",
    ],
    "technical-intelligence-graph": [
        "Technical-alpha graph over high-signal builders, repositories, papers, dependencies, and adoption",
        "Configurable frontier radar sold by industry vertical",
    ],
    "agent-orchestration": [
        "Framework-neutral supervisor detecting stuck, looping, blocked, or budget-exceeded agents",
        "Durable orchestration control plane spanning heterogeneous agent CLIs",
    ],
    "local-first-sync": [
        "Offline-first state substrate for consumer AI applications",
        "Selective synchronization layer for edge agents",
    ],
    "model-routing": [
        "Live inference-economics sensor with provider promotions, limits, latency, and reliability",
        "Task-aware model/provider routing oracle backed by real measurements",
    ],
    "emerging-software-primitive": [
        "Package the primitive behind a stable agent-facing API and empirically test the highest-friction downstream workflow",
    ],
}

MONETIZATION_PRIOR = {
    "durable-agent-state": 0.82,
    "agent-web-access": 0.86,
    "execution-placement": 0.84,
    "verification-receipts": 0.88,
    "technical-intelligence-graph": 0.85,
    "agent-orchestration": 0.83,
    "local-first-sync": 0.72,
    "model-routing": 0.82,
    "emerging-software-primitive": 0.55,
}


class OpportunityEngine:
    def __init__(self, store: Store, settings: AppSettings, profile: SectorProfile) -> None:
        self.store = store
        self.settings = settings
        self.profile = profile
        self.primitives = PrimitiveExtractor(store, profile)

    def derive(self, signal: FrontierSignal) -> list[Opportunity]:
        entity = self.store.get_entity(signal.target_id)
        source_families = {o.source_family for o in self.store.observations(sector=self.profile.id, target_id=signal.target_id)}
        license_info = classify_license((entity.attrs if entity else {}).get("license_spdx"))
        results: list[Opportunity] = []
        for primitive in self.primitives.extract(signal)[:3]:
            monetization = MONETIZATION_PRIOR.get(primitive.name, 0.55)
            evidence_breadth = min(1.0, len(source_families) / 3.0)
            proofability = 0.85 if signal.target_id.startswith("github:repo:") else 0.65
            reusability = 0.82 if license_info.category == "permissive" else 0.62 if license_info.category == "unknown" else 0.55
            total = (
                0.32 * signal.technical_alpha
                + 0.14 * signal.confidence
                + 0.12 * signal.novelty
                + 0.10 * signal.momentum
                + 0.12 * monetization
                + 0.10 * proofability
                + 0.05 * evidence_breadth
                + 0.05 * reusability
            )
            decision = self._decision(total)
            target_name = entity.name if entity else signal.target_id
            scorecard = {
                "total": round(total, 6),
                "technical_alpha": signal.technical_alpha,
                "signal_confidence": signal.confidence,
                "novelty": signal.novelty,
                "momentum": signal.momentum,
                "monetization_prior": monetization,
                "proofability": proofability,
                "source_breadth": evidence_breadth,
                "reuse_safety_prior": reusability,
                "primitive_confidence": primitive.confidence,
            }
            results.append(
                Opportunity(
                    signal_id=signal.signal_id,
                    sector=self.profile.id,
                    title=f"{primitive.name} opportunity around {target_name}",
                    problem=(
                        f"Frontier attention is converging on {target_name}. Determine whether the {primitive.name} "
                        "primitive removes a recurring external-world or agent-infrastructure bottleneck before broad adoption."
                    ),
                    primitive=primitive.name,
                    solution_hypotheses=HYPOTHESES.get(primitive.name, HYPOTHESES["emerging-software-primitive"]),
                    scorecard=scorecard,
                    decision=decision,
                    evidence_ids=signal.evidence_ids,
                )
            )
        return results

    def _decision(self, score: float) -> str:
        s = self.settings.scoring
        if score >= s.build_threshold:
            return "BUILD"
        if score >= s.research_threshold:
            return "RESEARCH"
        if score >= s.watch_threshold:
            return "WATCH"
        return "REJECT"
