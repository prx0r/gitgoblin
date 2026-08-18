from __future__ import annotations

import math
from datetime import datetime, timezone

from gitgoblin.db import Store
from gitgoblin.models import BuilderScore
from gitgoblin.settings import SectorProfile


def _sat_log(value: float, scale: float) -> float:
    return min(1.0, math.log1p(max(0.0, value)) / math.log1p(scale))


class ExpertiseScorer:
    """Scores demonstrated technical depth while intentionally limiting popularity weight."""

    def __init__(self, store: Store, profile: SectorProfile) -> None:
        self.store = store
        self.profile = profile

    def score(self, builder_id: str, *, include_test: bool = False) -> BuilderScore:
        entity = self.store.get_entity(builder_id)
        observations = [o for o in self.store.observations(sector=self.profile.id, include_test=include_test) if o.actor_id == builder_id]
        attrs = entity.attrs if entity else {}
        owned = [o for o in observations if o.action in {"owns", "fork_owns"}]
        original = [o for o in owned if o.action == "owns"]
        languages = {str(o.value.get("language") or "").lower() for o in original}
        preferred = {x.lower() for x in self.profile.expertise_languages}

        # Popularity is capped and receives only 15% of the final score.
        reputation = _sat_log(float(attrs.get("followers") or 0), 5000)
        activity = _sat_log(sum(1 for o in observations if o.action in {"push", "pull_request", "issue", "create"}), 120)
        originality = len(original) / max(1, len(owned)) if owned else 0.35
        repo_quality = 0.0
        if original:
            stars = sum(float(o.value.get("stars") or 0) for o in original)
            repo_quality = _sat_log(stars / len(original), 1000)
        language_fit = 0.5
        if preferred and languages:
            language_fit = len(preferred & languages) / len(preferred | languages)
        experience = self._experience(attrs.get("created_at"))

        components = {
            "reputation": reputation,
            "activity": activity,
            "originality": originality,
            "repo_quality": repo_quality,
            "language_fit": language_fit,
            "experience": experience,
        }
        score = (
            0.15 * reputation
            + 0.20 * activity
            + 0.20 * originality
            + 0.20 * repo_quality
            + 0.15 * language_fit
            + 0.10 * experience
        )
        # A configured human seed starts with a modest prior, never an automatic "expert" label.
        if builder_id.removeprefix("github:user:") in {x.lower() for x in self.profile.seed_builders}:
            score = min(1.0, score + 0.08)
            components["seed_prior"] = 0.08
        return BuilderScore(builder_id=builder_id, score=round(score, 6), components=components)

    @staticmethod
    def _experience(created_at: str | None) -> float:
        if not created_at:
            return 0.4
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            years = max(0.0, (datetime.now(timezone.utc) - created).days / 365.25)
            return min(1.0, years / 10.0)
        except Exception:
            return 0.4
