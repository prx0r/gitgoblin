from __future__ import annotations

from urllib.parse import quote

from gitgoblin.http import ResilientHTTP
from gitgoblin.models import Entity, Observation, evidence_for_payload, utcnow
from gitgoblin.settings import AppSettings


class EcosystemsCollector:
    """Consume ecosyste.ms repository metadata without incorporating AGPL server code."""

    source_name = "ecosystems"
    source_family = "oss_index"
    base_url = "https://repos.ecosyste.ms/api/v1/hosts/GitHub/repositories"

    def __init__(self, settings: AppSettings, http: ResilientHTTP | None = None) -> None:
        self.http = http or ResilientHTTP(
            user_agent=settings.user_agent,
            timeout=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
        )

    def collect(self, full_name: str, *, sector: str) -> tuple[list[Entity], list[Observation]]:
        encoded = quote(full_name, safe="")
        url = f"{self.base_url}/{encoded}"
        repo = self.http.get_json(url, cache_ttl_seconds=3600)
        rid = f"github:repo:{full_name.lower()}"
        entity = Entity(
            entity_id=rid,
            entity_type="repository",
            name=full_name,
            source="ecosystems",
            url=repo.get("html_url") or f"https://github.com/{full_name}",
            attrs={
                "stars": repo.get("stargazers_count") or 0,
                "forks": repo.get("forks_count") or 0,
                "open_issues": repo.get("open_issues_count") or 0,
                "created_at": repo.get("created_at"),
                "pushed_at": repo.get("pushed_at"),
                "license": repo.get("license"),
                "language": repo.get("language"),
                "topics": repo.get("topics") or [],
                "last_synced_at": repo.get("last_synced_at"),
            },
        )
        obs = Observation(
            source="ecosystems",
            source_family=self.source_family,
            entity_type="repository",
            entity_id=rid,
            action="metadata_snapshot",
            target_id=rid,
            occurred_at=utcnow(),
            value=entity.attrs,
            tags=repo.get("topics") or [],
            sector=sector,
            evidence=evidence_for_payload(repo, url),
            quality={"upstream_data_license": "CC-BY-SA-4.0", "snapshot": True},
        )
        return [entity], [obs]
