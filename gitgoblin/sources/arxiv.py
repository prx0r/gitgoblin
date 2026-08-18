from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote
from xml.etree import ElementTree as ET

from gitgoblin.http import ResilientHTTP
from gitgoblin.models import Entity, Observation, evidence_for_payload
from gitgoblin.settings import AppSettings

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


class ArxivCollector:
    source_name = "arxiv"
    source_family = "preprint"
    base_url = "https://export.arxiv.org/api/query"

    def __init__(self, settings: AppSettings, http: ResilientHTTP | None = None) -> None:
        self.http = http or ResilientHTTP(
            user_agent=settings.user_agent,
            timeout=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
        )

    def collect(self, query: str, *, sector: str, max_results: int = 50) -> tuple[list[Entity], list[Observation]]:
        search = f'all:"{query}"'
        text = self.http.get_text(
            self.base_url,
            params={"search_query": search, "start": 0, "max_results": max_results, "sortBy": "submittedDate", "sortOrder": "descending"},
        )
        root = ET.fromstring(text)
        entities: dict[str, Entity] = {}
        observations: list[Observation] = []
        for entry in root.findall(f"{ATOM}entry"):
            raw_id = (entry.findtext(f"{ATOM}id") or "").strip()
            if not raw_id:
                continue
            arxiv_id = raw_id.rsplit("/", 1)[-1]
            entity_id = f"arxiv:paper:{arxiv_id.lower()}"
            title = " ".join((entry.findtext(f"{ATOM}title") or "Untitled").split())
            published = entry.findtext(f"{ATOM}published")
            authors = [a.findtext(f"{ATOM}name") or "unknown" for a in entry.findall(f"{ATOM}author")]
            categories = [c.attrib.get("term", "") for c in entry.findall(f"{ATOM}category")]
            payload = {
                "id": raw_id,
                "title": title,
                "published": published,
                "authors": authors,
                "categories": categories,
                "summary": " ".join((entry.findtext(f"{ATOM}summary") or "").split()),
            }
            entities[entity_id] = Entity(
                entity_id=entity_id,
                entity_type="paper",
                name=title,
                source="arxiv",
                url=raw_id,
                attrs={"authors": authors, "categories": categories, "query": query},
            )
            observations.append(
                Observation(
                    source="arxiv",
                    source_family=self.source_family,
                    entity_type="paper",
                    entity_id=entity_id,
                    actor_id=f"arxiv:author:{authors[0].lower()}" if authors else None,
                    action="authored",
                    target_id=entity_id,
                    occurred_at=datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc),
                    value={"authors": authors, "categories": categories, "query": query, "summary": payload["summary"]},
                    tags=categories,
                    sector=sector,
                    evidence=evidence_for_payload(payload, raw_id, arxiv_id),
                )
            )
        return list(entities.values()), observations
