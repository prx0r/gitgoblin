from __future__ import annotations

import os
from datetime import date, datetime, timezone, timedelta
from typing import Any

from gitgoblin.http import ResilientHTTP
from gitgoblin.models import Entity, Observation, evidence_for_payload
from gitgoblin.settings import AppSettings


class OpenAlexCollector:
    source_name = "openalex"
    source_family = "research_graph"
    base_url = "https://api.openalex.org"

    def __init__(self, settings: AppSettings, http: ResilientHTTP | None = None) -> None:
        self.http = http or ResilientHTTP(
            user_agent=settings.user_agent,
            timeout=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
            rate_limits=settings.rate_limits,
        )
        self.api_key = os.getenv("OPENALEX_API_KEY")

    def collect(self, query: str, *, sector: str, days: int = 30, max_pages: int = 2) -> tuple[list[Entity], list[Observation]]:
        since = (date.today() - timedelta(days=days)).isoformat()
        params = {
            "search": query,
            "filter": f"from_publication_date:{since}",
            "per_page": 100,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        entities: dict[str, Entity] = {}
        observations: list[Observation] = []
        cursor = "*"
        for _ in range(max_pages):
            params["cursor"] = cursor
            body = self.http.get_json(f"{self.base_url}/works", params=params, cache_ttl_seconds=1800, source="openalex")
            for work in body.get("results", []):
                wid = str(work.get("id") or work.get("doi"))
                if not wid:
                    continue
                entity_id = f"openalex:work:{wid.rsplit('/', 1)[-1].lower()}"
                entities[entity_id] = Entity(
                    entity_id=entity_id,
                    entity_type="paper",
                    name=work.get("display_name") or "Untitled",
                    source="openalex",
                    url=work.get("doi") or work.get("id"),
                    attrs={
                        "publication_date": work.get("publication_date"),
                        "cited_by_count": work.get("cited_by_count") or 0,
                        "primary_topic": ((work.get("primary_topic") or {}).get("display_name")),
                        "open_access": work.get("open_access") or {},
                    },
                )
                authors = []
                for authorship in work.get("authorships") or []:
                    author = authorship.get("author") or {}
                    aid_raw = author.get("id")
                    if not aid_raw:
                        continue
                    aid = f"openalex:author:{aid_raw.rsplit('/', 1)[-1].lower()}"
                    authors.append(aid)
                    entities.setdefault(
                        aid,
                        Entity(
                            entity_id=aid,
                            entity_type="researcher",
                            name=author.get("display_name") or aid,
                            source="openalex",
                            url=aid_raw,
                            attrs={"orcid": author.get("orcid")},
                        ),
                    )
                occurred = self._publication_dt(work.get("publication_date"))
                observations.append(
                    Observation(
                        source="openalex",
                        source_family=self.source_family,
                        entity_type="paper",
                        entity_id=entity_id,
                        actor_id=authors[0] if authors else None,
                        action="authored",
                        target_id=entity_id,
                        occurred_at=occurred,
                        value={
                            "authors": authors,
                            "cited_by_count": work.get("cited_by_count") or 0,
                            "type": work.get("type"),
                            "query": query,
                        },
                        tags=[x for x in [((work.get("primary_topic") or {}).get("display_name"))] if x],
                        sector=sector,
                        evidence=evidence_for_payload(work, work.get("id"), wid),
                        quality={"source_is_aggregated_graph": True},
                    )
                )
            cursor = (body.get("meta") or {}).get("next_cursor")
            if not cursor:
                break
        return list(entities.values()), observations

    @staticmethod
    def _publication_dt(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
