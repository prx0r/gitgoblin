from __future__ import annotations

import json
from datetime import datetime

import httpx

from gitgoblin.http import ResilientHTTP
from gitgoblin.settings import AppSettings
from gitgoblin.sources.github import GitHubCollector


def test_github_collector_normalizes_real_endpoint_shapes(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/users/alice":
            return httpx.Response(200, json={
                "id": 1, "login": "alice", "html_url": "https://github.com/alice", "followers": 120,
                "following": 8, "public_repos": 2, "created_at": "2015-01-01T00:00:00Z", "company": "@A"
            })
        if path == "/users/alice/following":
            return httpx.Response(200, json=[{"id": 2, "login": "bob", "html_url": "https://github.com/bob"}])
        if path == "/users/alice/starred":
            return httpx.Response(200, json=[{
                "starred_at": "2026-08-01T12:00:00Z",
                "repo": {"id": 3, "full_name": "org/repo", "html_url": "https://github.com/org/repo", "stargazers_count": 44,
                         "forks_count": 3, "open_issues_count": 1, "size": 10, "created_at": "2026-07-01T00:00:00Z",
                         "pushed_at": "2026-08-10T00:00:00Z", "language": "Rust", "topics": ["agent"], "license": {"spdx_id": "MIT"}}
            }])
        if path == "/users/alice/events/public":
            return httpx.Response(200, json=[{
                "id": "evt1", "type": "ForkEvent", "actor": {"login": "alice"},
                "repo": {"name": "org/repo"}, "payload": {}, "created_at": "2026-08-02T00:00:00Z"
            }])
        if path == "/users/alice/repos":
            return httpx.Response(200, json=[{
                "id": 4, "full_name": "alice/tool", "html_url": "https://github.com/alice/tool", "fork": False,
                "stargazers_count": 80, "forks_count": 5, "open_issues_count": 0, "size": 20,
                "created_at": "2026-01-01T00:00:00Z", "pushed_at": "2026-08-01T00:00:00Z",
                "language": "Python", "topics": ["devtool"], "license": {"spdx_id": "Apache-2.0"}, "owner": {"login": "alice"}
            }])
        return httpx.Response(404, json={"path": path})

    settings = AppSettings(database_path=str(tmp_path / "x.db"))
    settings.github.pages_per_seed = 1
    http = ResilientHTTP(user_agent="test", transport=httpx.MockTransport(handler), cache_dir=tmp_path / "cache")
    entities, obs = GitHubCollector(settings, http=http).collect("alice", sector="ai", pages=1)
    actions = {o.action for o in obs}
    assert {"profile_snapshot", "follow", "star", "fork", "owns"} <= actions
    star = next(o for o in obs if o.action == "star")
    assert star.occurred_at.isoformat().startswith("2026-08-01T12:00:00")
    follow = next(o for o in obs if o.action == "follow")
    assert follow.quality["temporal_precision"] == "snapshot_only"
    repo = next(e for e in entities if e.entity_id == "github:repo:org/repo")
    assert repo.attrs["license_spdx"] == "MIT"
