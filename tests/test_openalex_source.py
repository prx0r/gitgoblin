from __future__ import annotations

import httpx

from gitgoblin.http import ResilientHTTP
from gitgoblin.settings import AppSettings
from gitgoblin.sources.openalex import OpenAlexCollector


def test_openalex_collector_normalizes_work_and_authors(tmp_path):
    payload = {
        "results": [{
            "id": "https://openalex.org/W123", "doi": "https://doi.org/10.1/test", "display_name": "Agent Storage",
            "publication_date": "2026-08-01", "cited_by_count": 7, "type": "article",
            "primary_topic": {"display_name": "Software Agents"}, "open_access": {"is_oa": True},
            "authorships": [{"author": {"id": "https://openalex.org/A9", "display_name": "Ada", "orcid": None}}]
        }],
        "meta": {"next_cursor": None}
    }
    http = ResilientHTTP(user_agent="test", transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)), cache_dir=tmp_path / "cache")
    collector = OpenAlexCollector(AppSettings(database_path=str(tmp_path / "x.db")), http=http)
    entities, obs = collector.collect("agents", sector="ai", max_pages=1)
    assert any(e.entity_id == "openalex:work:w123" for e in entities)
    assert any(e.entity_id == "openalex:author:a9" for e in entities)
    assert obs[0].action == "authored"
    assert obs[0].value["cited_by_count"] == 7
