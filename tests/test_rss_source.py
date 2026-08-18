from __future__ import annotations

import httpx

from gitgoblin.http import ResilientHTTP
from gitgoblin.sources.rss import RSSCollector


RSS = """<?xml version=\"1.0\"?><rss version=\"2.0\"><channel>
<item><title>Durable agents at the edge</title><link>https://example.com/a</link>
<pubDate>Tue, 18 Aug 2026 10:00:00 GMT</pubDate><description>checkpoint storage for agent workers</description></item>
<item><title>Gardening notes</title><link>https://example.com/b</link>
<pubDate>Tue, 18 Aug 2026 11:00:00 GMT</pubDate><description>tomatoes</description></item>
</channel></rss>"""


def test_rss_collector_filters_and_hashes(settings):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=RSS)

    http = ResilientHTTP(user_agent="test", transport=httpx.MockTransport(handler), cache_dir=settings.artifact_dir)
    collector = RSSCollector(settings, http=http)
    entities, observations = collector.collect(
        "https://example.com/feed.xml", sector="ai", keywords=["agent", "checkpoint"]
    )

    assert len(entities) == 1
    assert entities[0].name == "Durable agents at the edge"
    assert observations[0].tags == ["agent", "checkpoint"]
    assert observations[0].action == "published"
    assert observations[0].evidence.source_url == "https://example.com/a"


