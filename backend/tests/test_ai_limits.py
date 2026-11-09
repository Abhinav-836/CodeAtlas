"""Daily limits that protect the Ollama bill (app/core/ai_limits.py)."""
import asyncio

import aiohttp

from app.core import ai_limits
from app.core.config import settings


def test_debug_is_off_unless_switched_on(app):
    assert settings.DEBUG is False
    assert not any(p.startswith("/api/ai") for p in app.openapi()["paths"])


def test_analyses_per_visitor(browser, monkeypatch):
    monkeypatch.setenv("ANALYSES_PER_IP_DAILY", "2")
    ai_limits.reset_all()
    path = browser.upload().json()["extracted_to"]

    def analyze(ip):
        headers = {**browser.headers, "X-Forwarded-For": ip}
        return browser.client.post("/api/analyze", params={"path": path}, headers=headers)

    assert [analyze("1.1.1.1").status_code for _ in range(3)] == [200, 200, 429]
    assert "daily limit" in analyze("1.1.1.1").json()["detail"]
    # A different visitor still has their own allowance
    assert analyze("2.2.2.2").status_code == 200
    ai_limits.reset_all()


def test_server_wide_ai_total_stops_calls(monkeypatch):
    from app.services.ai.llm_client import llm_client

    monkeypatch.setenv("AI_CALLS_DAILY_TOTAL", "1")
    ai_limits.reset_all()
    calls = []

    def fake_post(self, *a, **k):
        calls.append(1)
        raise RuntimeError("no network in tests")

    monkeypatch.setattr(aiohttp.ClientSession, "post", fake_post)
    asyncio.run(llm_client.call_async("hi"))
    second = asyncio.run(llm_client.call_async("hi"))
    assert len(calls) == 1
    assert second["success"] is False and "paused for today" in second["error"]
    ai_limits.reset_all()
