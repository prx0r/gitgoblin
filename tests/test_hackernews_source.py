from __future__ import annotations

import httpx

from gitgoblin.http import ResilientHTTP
from gitgoblin.sources.hackernews import HackerNewsCollector


def test_hackernews_collector_filters_matching_stories(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith('/newstories.json'):
            return httpx.Response(200, json=[101, 102])
        if path.endswith('/item/101.json'):
            return httpx.Response(200, json={
                'id': 101, 'type': 'story', 'title': 'Durable agent runtime released',
                'url': 'https://example.com/agent', 'by': 'alice', 'time': 1787040000,
                'score': 42, 'descendants': 12,
            })
        return httpx.Response(200, json={
            'id': 102, 'type': 'story', 'title': 'Unrelated gardening post',
            'url': 'https://example.com/garden', 'by': 'bob', 'time': 1787040000,
            'score': 5, 'descendants': 1,
        })

    http = ResilientHTTP(user_agent='test', transport=httpx.MockTransport(handler), cache_dir=settings.artifact_dir)
    collector = HackerNewsCollector(settings, http=http)
    entities, observations = collector.collect(['agent', 'checkpoint'], sector='ai', max_items=10)

    assert [e.entity_id for e in entities] == ['hn:story:101']
    assert observations[0].actor_id == 'hn:user:alice'
    assert observations[0].tags == ['agent']
    assert observations[0].value['comments'] == 12
    assert observations[0].evidence.source_record_id == '101'
