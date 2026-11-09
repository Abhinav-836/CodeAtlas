"""
Daily limits that protect the Ollama Cloud bill.

Ollama Cloud charges per token and CodeAtlas has no accounts, so two limits
apply, both reset at midnight UTC:
  - ANALYSES_PER_IP_DAILY: analyses one visitor (by IP address) can start
  - AI_CALLS_DAILY_TOTAL:  AI calls the whole server will make; past it,
    analyses still run but without the AI summary
Set either to 0 to switch it off. Counters live in memory: they reset when
the server restarts (deploys), which is fine for a cost guard.
"""
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class DailyCounter:
    """Thread-safe counters per key that start again every UTC day."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = ""
        self._counts: Dict[str, int] = {}

    def _roll(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._day:
            self._day, self._counts = today, {}

    def take(self, key: str, limit: int) -> Tuple[bool, int]:
        """Use one unit for key. Returns (allowed, used). limit <= 0 means unlimited."""
        with self._lock:
            self._roll()
            used = self._counts.get(key, 0)
            if limit > 0 and used >= limit:
                return False, used
            self._counts[key] = used + 1
            return True, used + 1

    def reset(self) -> None:
        with self._lock:
            self._day, self._counts = "", {}


_analyses = DailyCounter()
_ai_calls = DailyCounter()


def analyses_per_ip_daily() -> int:
    return _int_env("ANALYSES_PER_IP_DAILY", 10)


def ai_calls_daily_total() -> int:
    return _int_env("AI_CALLS_DAILY_TOTAL", 300)


def client_ip(request: Request) -> str:
    """The visitor's IP. Render puts the real address first in X-Forwarded-For."""
    for header in ("cf-connecting-ip", "true-client-ip"):
        if request.headers.get(header):
            return request.headers[header].strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def take_analysis(request: Request) -> None:
    """FastAPI helper: count one analysis for this visitor, or raise 429."""
    limit = analyses_per_ip_daily()
    allowed, _ = _analyses.take(client_ip(request), limit)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"You've run {limit} analyses today, the daily limit. Please try again tomorrow.",
        )


def take_ai_call() -> Optional[str]:
    """Count one AI call for the server. Returns an error message when the daily total is used up."""
    allowed, _ = _ai_calls.take("all", ai_calls_daily_total())
    if not allowed:
        return "AI summaries are paused for today (daily limit reached). The rest of the analysis still works."
    return None


def reset_all() -> None:
    """For tests."""
    _analyses.reset()
    _ai_calls.reset()
