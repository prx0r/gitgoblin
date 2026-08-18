from __future__ import annotations

from typing import Any

from gitgoblin.hashing import sha256_json
from gitgoblin.models import FrontierSignal, Opportunity


ORACLE_ID = "gitgoblin.frontier_graph.v1"


def signal_to_market_observations(signal: FrontierSignal) -> list[dict[str, Any]]:
    """Emit VentureLab MarketObservation-compatible records."""
    evidence_hash = sha256_json(signal.model_dump(mode="json"))
    base = {
        "oracle_id": ORACLE_ID,
        "entity_id": signal.target_id,
        "observed_at": signal.detected_at.isoformat(),
        "source_family": "frontier_attention",
        "sector": signal.sector,
        "evidence": {"artifact_sha256": evidence_hash, "source_url": None},
        "quality": {
            "confidence": signal.confidence,
            "expert_count": signal.expert_count,
            "independent_cluster_count": signal.independent_cluster_count,
            "evidence_count": len(signal.evidence_ids),
        },
    }
    metrics = {
        "technical_alpha": signal.technical_alpha,
        "novelty": signal.novelty,
        "momentum": signal.momentum,
        "expert_count": signal.expert_count,
        "independent_cluster_count": signal.independent_cluster_count,
    }
    out: list[dict[str, Any]] = []
    for metric, value in metrics.items():
        record = {**base, "metric": metric, "value": value, "unit": "score" if isinstance(value, float) else "count"}
        record["observation_id"] = f"gg_{signal.signal_id}_{metric}"
        out.append(record)
    return out


def opportunity_to_cuntgoblin(opp: Opportunity) -> dict[str, Any]:
    return {
        "opportunity_id": opp.opportunity_id,
        "market_topic_ids": [f"gitgoblin:{opp.sector}:{opp.primitive}"],
        "problem": opp.problem,
        "miner": "gitgoblin.frontier_opportunity_engine.v1",
        "evidence": opp.evidence_ids,
        "scorecard": opp.scorecard,
        "decision": opp.decision,
        "solution_hypotheses": opp.solution_hypotheses,
    }
