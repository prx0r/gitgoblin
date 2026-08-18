from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

from gitgoblin.http import ResilientHTTP
from gitgoblin.models import Entity, Observation, evidence_for_payload
from gitgoblin.settings import AppSettings


class RSSCollector:
    """Generic RSS/Atom collector for technical blogs and industry-specific feeds."""

    source_name = "rss"
    source_family = "technical_publication"

    def __init__(self, settings: AppSettings, http: ResilientHTTP | None = None) -> None:
        self.http = http or ResilientHTTP(
            user_agent=settings.user_agent,
            timeout=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
            rate_limits=settings.rate_limits,
        )

    def collect(self, feed_url: str, *, sector: str, keywords: list[str] | None = None) -> tuple[list[Entity], list[Observation]]:
        text = self.http.get_text(feed_url, source="rss")
        root = ET.fromstring(text)
        keywords = [k.lower() for k in (keywords or [])]
        entries = root.findall(".//item")
        atom = False
        if not entries:
            atom = True
            ns = "{http://www.w3.org/2005/Atom}"
            entries = root.findall(f".//{ns}entry")
        entities, observations = [], []
        for entry in entries:
            if atom:
                ns = "{http://www.w3.org/2005/Atom}"
                title = entry.findtext(f"{ns}title") or "Untitled"
                link_node = entry.find(f"{ns}link")
                link = link_node.attrib.get("href") if link_node is not None else None
                published = entry.findtext(f"{ns}published") or entry.findtext(f"{ns}updated")
                summary = entry.findtext(f"{ns}summary") or ""
            else:
                title = entry.findtext("title") or "Untitled"
                link = entry.findtext("link")
                published = entry.findtext("pubDate")
                summary = entry.findtext("description") or ""
            haystack = f"{title} {summary}".lower()
            matched = [k for k in keywords if k in haystack]
            if keywords and not matched:
                continue
            when = self._parse_date(published)
            payload = {"title": title, "link": link, "published": published, "summary": summary[:4000]}
            eid = f"rss:item:{evidence_for_payload(payload).artifact_sha256[:20]}"
            entities.append(Entity(entity_id=eid, entity_type="publication", name=title, source="rss", url=link, attrs={"feed_url": feed_url}))
            observations.append(
                Observation(
                    source="rss",
                    source_family=self.source_family,
                    entity_type="publication",
                    entity_id=eid,
                    action="published",
                    target_id=eid,
                    occurred_at=when,
                    value={"feed_url": feed_url, "matched_keywords": matched},
                    tags=matched,
                    sector=sector,
                    evidence=evidence_for_payload(payload, link or feed_url),
                )
            )
        return entities, observations

    @staticmethod
    def _parse_date(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            if value.endswith("Z"):
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                return parsedate_to_datetime(value)
            except Exception:
                return datetime.now(timezone.utc)
