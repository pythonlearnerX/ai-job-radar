"""fetch_url 的可靠性：重试、限速、断点续跑。"""

from __future__ import annotations

import time
import urllib.error
from unittest import mock

import pytest

from job_radar.fetcher import FetchError, fetch_url, load_seen, mark_seen


def _fake_response(body: bytes = b"ok", charset: str | None = "utf-8"):
    resp = mock.MagicMock()
    resp.read.return_value = body
    resp.headers.get_content_charset.return_value = charset
    resp.__enter__.return_value = resp
    return resp


def test_returns_text_and_url(monkeypatch):
    with mock.patch("urllib.request.urlopen", return_value=_fake_response("你好".encode("utf-8"))):
        job = fetch_url("https://example.com/a", delay=0, backoff=0)
    assert job.text == "你好"
    assert job.url == "https://example.com/a"


def test_retries_on_5xx_then_succeeds(monkeypatch):
    calls = []

    def fake(url, *args, **kwargs):
        calls.append(url)
        if len(calls) < 3:
            raise urllib.error.HTTPError(url, 503, "busy", {}, None)
        return _fake_response(b"ok")

    monkeypatch.setattr("urllib.request.urlopen", fake)
    job = fetch_url("https://example.com/b", delay=0, backoff=0, retries=3)
    assert job.text == "ok"
    assert len(calls) == 3


def test_4xx_is_not_retried(monkeypatch):
    calls = []

    def fake(url, *args, **kwargs):
        calls.append(url)
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", fake)
    with pytest.raises(FetchError):
        fetch_url("https://example.com/c", delay=0, backoff=0, retries=3)
    assert len(calls) == 1


def test_network_error_gives_up_after_retries(monkeypatch):
    calls = []

    def fake(url, *args, **kwargs):
        calls.append(url)
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake)
    with pytest.raises(FetchError):
        fetch_url("https://example.com/d", delay=0, backoff=0, retries=3)
    assert len(calls) == 3


def test_rate_limit_spaces_out_requests(monkeypatch):
    with mock.patch("urllib.request.urlopen", return_value=_fake_response()):
        started = time.monotonic()
        fetch_url("https://example.com/e", delay=0.2, backoff=0)
        fetch_url("https://example.com/f", delay=0.2, backoff=0)
        elapsed = time.monotonic() - started
    assert elapsed >= 0.18


def test_seen_file_roundtrip(tmp_path):
    path = tmp_path / "nested" / "seen.txt"
    assert load_seen(path) == set()

    mark_seen(path, "https://a.com/1")
    mark_seen(path, "https://a.com/2")
    mark_seen(path, "https://a.com/1")  # 重复写不报错

    assert load_seen(path) == {"https://a.com/1", "https://a.com/2"}
