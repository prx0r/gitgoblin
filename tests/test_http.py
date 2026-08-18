from __future__ import annotations

import json

import httpx
import pytest

from gitgoblin.http import HTTPError, ResilientHTTP


def test_http_cache_avoids_second_network_call(tmp_path):
    calls = {'n': 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls['n'] += 1
        return httpx.Response(200, json={'value': calls['n']})

    http = ResilientHTTP(user_agent='test', transport=httpx.MockTransport(handler), cache_dir=tmp_path)
    assert http.get_json('https://example.com/data', cache_ttl_seconds=3600) == {'value': 1}
    assert http.get_json('https://example.com/data', cache_ttl_seconds=3600) == {'value': 1}
    assert calls['n'] == 1


def test_http_retries_429_then_succeeds(tmp_path, monkeypatch):
    calls = {'n': 0}
    monkeypatch.setattr('gitgoblin.http.time.sleep', lambda _: None)

    def handler(_: httpx.Request) -> httpx.Response:
        calls['n'] += 1
        if calls['n'] == 1:
            return httpx.Response(429, headers={'retry-after': '0'}, text='slow down')
        return httpx.Response(200, json={'ok': True})

    http = ResilientHTTP(user_agent='test', max_retries=1, transport=httpx.MockTransport(handler), cache_dir=tmp_path)
    assert http.get_json('https://example.com/data') == {'ok': True}
    assert calls['n'] == 2


def test_http_raises_after_bounded_retries(tmp_path, monkeypatch):
    monkeypatch.setattr('gitgoblin.http.time.sleep', lambda _: None)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text='unavailable')

    http = ResilientHTTP(user_agent='test', max_retries=1, transport=httpx.MockTransport(handler), cache_dir=tmp_path)
    with pytest.raises(HTTPError):
        http.get_text('https://example.com/down')
