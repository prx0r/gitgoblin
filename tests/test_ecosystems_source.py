from __future__ import annotations

import httpx

from gitgoblin.http import ResilientHTTP
from gitgoblin.sources.ecosystems import EcosystemsCollector


def test_ecosystems_collector_maps_repository(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert "repos.ecosyste.ms" in request.url.host
        return httpx.Response(
            200,
            json={
                "full_name": "newco/frontier",
                "html_url": "https://github.com/newco/frontier",
                "stargazers_count": 123,
                "forks_count": 11,
                "open_issues_count": 3,
                "created_at": "2026-08-01T00:00:00Z",
                "pushed_at": "2026-08-18T00:00:00Z",
                "license": "MIT",
                "language": "Rust",
                "topics": ["agents", "storage"],
                "last_synced_at": "2026-08-18T00:05:00Z",
            },
        )

    http = ResilientHTTP(user_agent="test", transport=httpx.MockTransport(handler), cache_dir=settings.artifact_dir)
    collector = EcosystemsCollector(settings, http=http)
    entities, observations = collector.collect("newco/frontier", sector="ai")

    assert len(entities) == 1
    assert entities[0].entity_id == "github:repo:newco/frontier"
    assert entities[0].attrs["stars"] == 123
    assert observations[0].quality["upstream_data_license"] == "CC-BY-SA-4.0"
    assert observations[0].evidence.artifact_sha256


