from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable

from gitgoblin.db import Store
from gitgoblin.models import BuilderScore, FrontierSignal, Observation
from gitgoblin.settings import AppSettings, SectorProfile

from .expertise import ExpertiseScorer


SIGNAL_ACTIONS = {"star", "fork", "issue", "pull_request", "push", "create", "dependency", "authored", "cited"}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


class SignalEngine:
    def __init__(self, store: Store, settings: AppSettings, profile: SectorProfile) -> None:
        self.store = store
        self.settings = settings
        self.profile = profile
        self.expertise = ExpertiseScorer(store, profile)

    def detect(self, *, now: datetime | None = None, include_test: bool = False) -> list[FrontierSignal]:
        now = now or datetime.now(timezone.utc)
        observations = [
            o for o in self.store.observations(sector=self.profile.id, include_test=include_test)
            if o.action in SIGNAL_ACTIONS and o.target_id and o.occurred_at >= now - timedelta(days=90)
        ]
        grouped: dict[str, list[Observation]] = defaultdict(list)
        for obs in observations:
            grouped[obs.target_id].append(obs)

        signals: list[FrontierSignal] = []
        for target_id, items in grouped.items():
            actors = sorted({o.actor_id for o in items if o.actor_id})
            if len(actors) < self.settings.scoring.min_experts:
                continue
            scores = {actor: self.expertise.score(actor, include_test=include_test) for actor in actors}
            weighted_attention = self._attention(items, scores, now)
            novelty = self._novelty(target_id, now)
            momentum = self._momentum(items, now)
            cluster_keys = {self._cluster_key(a) for a in actors}
            independence = min(1.0, len(cluster_keys) / max(1, len(actors)))
            source_breadth = min(1.0, len({o.source_family for o in items}) / 3.0)

            raw = 2.4 * weighted_attention + 1.1 * novelty + 1.1 * momentum + 0.8 * independence + 0.5 * source_breadth - 2.55
            alpha = _clamp(_sigmoid(raw))
            confidence = _clamp(
                0.30 * min(1.0, len(actors) / 5.0)
                + 0.25 * independence
                + 0.20 * source_breadth
                + 0.25 * min(1.0, len(items) / 8.0)
            )
            if alpha < self.settings.scoring.min_signal_score:
                continue
            reasons = self._reasons(items, scores, novelty, momentum, independence, source_breadth)
            signals.append(
                FrontierSignal(
                    target_id=target_id,
                    sector=self.profile.id,
                    technical_alpha=round(alpha, 6),
                    confidence=round(confidence, 6),
                    expert_count=len(actors),
                    independent_cluster_count=len(cluster_keys),
                    novelty=round(novelty, 6),
                    momentum=round(momentum, 6),
                    reasons=reasons,
                    metrics={
                        "weighted_attention": round(weighted_attention, 6),
                        "independence": round(independence, 6),
                        "source_breadth": round(source_breadth, 6),
                        "builder_scores": {k: v.score for k, v in scores.items()},
                        "action_counts": self._action_counts(items),
                    },
                    evidence_ids=sorted({o.observation_id for o in items}),
                    detected_at=now,
                )
            )
        return sorted(signals, key=lambda s: (s.technical_alpha, s.confidence), reverse=True)

    def _attention(self, items: list[Observation], scores: dict[str, BuilderScore], now: datetime) -> float:
        total = 0.0
        norm = 0.0
        for obs in items:
            if not obs.actor_id:
                continue
            builder = scores[obs.actor_id].score
            action = self.settings.scoring.action_weights.get(obs.action, 0.2)
            age_days = max(0.0, (now - obs.occurred_at).total_seconds() / 86400.0)
            recency = 0.5 ** (age_days / self.settings.scoring.recency_half_life_days)
            temporal_quality = 0.75 if obs.quality.get("temporal_precision") == "snapshot_only" else 1.0
            total += builder * action * recency * temporal_quality
            norm += action
        if norm == 0:
            return 0.0
        # Saturate rather than allowing many weak actions to dominate indefinitely.
        return _clamp(1.0 - math.exp(-(total / max(0.5, norm * 0.35))))

    def _novelty(self, target_id: str, now: datetime) -> float:
        entity = self.store.get_entity(target_id)
        if not entity:
            return 0.5
        attrs = entity.attrs
        created_at = attrs.get("created_at") or attrs.get("publication_date")
        age_component = 0.5
        if created_at:
            try:
                created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                age_days = max(0.0, (now - created).days)
                age_component = math.exp(-age_days / max(1.0, self.settings.scoring.young_repo_days))
            except Exception:
                pass
        stars = float(attrs.get("stars") or 0)
        saturation = 1.0 / (1.0 + math.log1p(stars) / 5.0)
        return _clamp(0.65 * age_component + 0.35 * saturation)

    @staticmethod
    def _momentum(items: list[Observation], now: datetime) -> float:
        last7 = sum(1 for o in items if o.occurred_at >= now - timedelta(days=7))
        prev23 = sum(1 for o in items if now - timedelta(days=30) <= o.occurred_at < now - timedelta(days=7))
        recent_rate = last7 / 7.0
        old_rate = prev23 / 23.0
        ratio = (recent_rate + 0.05) / (old_rate + 0.05)
        volume = min(1.0, last7 / 6.0)
        acceleration = _clamp(math.log1p(ratio) / math.log(5.0))
        return _clamp(0.55 * volume + 0.45 * acceleration)

    def _cluster_key(self, actor_id: str) -> str:
        entity = self.store.get_entity(actor_id)
        company = str((entity.attrs if entity else {}).get("company") or "").strip().lower()
        if company:
            return "company:" + company.lstrip("@").replace(" ", "_")
        return actor_id

    @staticmethod
    def _action_counts(items: Iterable[Observation]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for item in items:
            counts[item.action] += 1
        return dict(sorted(counts.items()))

    @staticmethod
    def _reasons(
        items: list[Observation], scores: dict[str, BuilderScore], novelty: float, momentum: float,
        independence: float, source_breadth: float,
    ) -> list[str]:
        reasons: list[str] = []
        strong = sum(1 for s in scores.values() if s.score >= 0.6)
        if strong:
            reasons.append(f"{strong} high-scoring builders interacted with the target")
        if independence >= 0.8:
            reasons.append("attention is distributed across largely independent builder clusters")
        if novelty >= 0.65:
            reasons.append("target is relatively young or unsaturated")
        if momentum >= 0.6:
            reasons.append("recent interaction rate is accelerating")
        if source_breadth >= 0.66:
            reasons.append("signal is corroborated across multiple source families")
        actions = SignalEngine._action_counts(items)
        high_commitment = sum(actions.get(a, 0) for a in {"fork", "pull_request", "push", "dependency", "authored"})
        if high_commitment:
            reasons.append(f"contains {high_commitment} higher-commitment technical actions")
        return reasons or ["weighted expert attention crossed the configured threshold"]
