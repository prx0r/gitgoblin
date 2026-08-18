from __future__ import annotations

from datetime import datetime, timezone

from gitgoblin.http import ResilientHTTP
from gitgoblin.models import Entity, Observation, evidence_for_payload
from gitgoblin.settings import AppSettings


class HackerNewsCollector:
    source_name = "hackernews"
    source_family = "developer_discourse"
    base_url = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, settings: AppSettings, http: ResilientHTTP | None = None) -> None:
        self.http = http or ResilientHTTP(
            user_agent=settings.user_agent,
            timeout=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
            rate_limits=settings.rate_limits,
        )

    def collect(self, keywords: list[str], *, sector: str, max_items: int = 80) -> tuple[list[Entity], list[Observation]]:
        ids = self.http.get_json(f"{self.base_url}/newstories.json", cache_ttl_seconds=120, source="hackernews")[:max_items]
        words = [k.lower() for k in keywords]
        entities: list[Entity] = []
        observations: list[Observation] = []
        for item_id in ids:
            item = self.http.get_json(f"{self.base_url}/item/{item_id}.json", cache_ttl_seconds=1800)
            if not item or item.get("type") != "story":
                continue
            haystack = " ".join([item.get("title") or "", item.get("url") or ""]).lower()
            matched = [w for w in words if w in haystack]
            if not matched:
                continue
            eid = f"hn:story:{item_id}"
            entities.append(
                Entity(
                    entity_id=eid,
                    entity_type="discussion",
                    name=item.get("title") or eid,
                    source="hackernews",
                    url=f"https://news.ycombinator.com/item?id={item_id}",
                    attrs={"score": item.get("score") or 0, "descendants": item.get("descendants") or 0, "url": item.get("url")},
                )
            )
            observations.append(
                Observation(
                    source="hackernews",
                    source_family=self.source_family,
                    entity_type="discussion",
                    entity_id=eid,
                    actor_id=f"hn:user:{item.get('by')}" if item.get("by") else None,
                    action="discussed",
                    target_id=eid,
                    occurred_at=datetime.fromtimestamp(item.get("time") or 0, tz=timezone.utc),
                    value={"score": item.get("score") or 0, "comments": item.get("descendants") or 0, "matched_keywords": matched, "external_url": item.get("url")},
                    tags=matched,
                    sector=sector,
                    evidence=evidence_for_payload(item, f"https://news.ycombinator.com/item?id={item_id}", str(item_id)),
                )
            )
        return entities, observations
