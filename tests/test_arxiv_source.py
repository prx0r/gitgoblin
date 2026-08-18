from __future__ import annotations

import httpx

from gitgoblin.http import ResilientHTTP
from gitgoblin.settings import AppSettings
from gitgoblin.sources.arxiv import ArxivCollector


ATOM = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2608.00001v1</id>
    <updated>2026-08-01T00:00:00Z</updated>
    <published>2026-08-01T00:00:00Z</published>
    <title>Durable Agents</title>
    <summary>Checkpointed agent execution.</summary>
    <author><name>Ada Example</name></author>
    <category term="cs.AI" />
  </entry>
</feed>'''


def test_arxiv_collector_parses_atom(tmp_path):
    http = ResilientHTTP(user_agent="test", transport=httpx.MockTransport(lambda r: httpx.Response(200, text=ATOM)), cache_dir=tmp_path / "cache")
    collector = ArxivCollector(AppSettings(database_path=str(tmp_path / "x.db")), http=http)
    entities, obs = collector.collect("agents", sector="ai")
    assert entities[0].name == "Durable Agents"
    assert obs[0].action == "authored"
    assert "cs.ai" in obs[0].tags
