"""
LLM client abstraction for CodeAtlas with Ollama support.
Handles sync, async, and streaming AI responses.
"""

import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Ollama-based LLM client for CodeAtlas."""

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL or "http://localhost:11434"
        self.model = settings.LLM_MODEL or "gpt-oss:120b-cloud"
        self.timeout = settings.LLM_TIMEOUT or 60
        self.api_key = getattr(settings, "OLLAMA_API_KEY", "") or os.getenv("OLLAMA_API_KEY", "")

    def _headers(self) -> Dict[str, str]:
        """Auth header for Ollama Cloud. Local Ollama ignores it."""
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    def _prepare_messages(
        self, prompt: str, system_message: Optional[str] = None
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        return messages

    # ── Synchronous ────────────────────────────────────────────────
    def call(self, prompt: str, **kwargs) -> str:
        try:
            messages = self._prepare_messages(prompt, kwargs.get("system_message"))
            response = requests.post(
                f"{self.base_url}/api/chat",
                headers=self._headers(),
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.3),
                        "num_predict": kwargs.get("max_tokens", 800),
                    },
                },
                timeout=self.timeout,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            logger.error("Ollama error: %s - %s", response.status_code, response.text)
            return self._get_fallback_response(prompt)
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama. Is it running?")
            return self._get_fallback_response(prompt)
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return self._get_fallback_response(prompt)

    # ── Async ──────────────────────────────────────────────────────
    async def call_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            messages = self._prepare_messages(prompt, kwargs.get("system_message"))
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    headers=self._headers(),
                    json={
                        "model": kwargs.get("model", self.model),
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": kwargs.get("temperature", 0.3),
                            "num_predict": kwargs.get("max_tokens", 800),
                        },
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("message", {}).get("content", "")
                        return {"success": True, "content": content, "model": self.model}
                    error_text = await response.text()
                    logger.error("Ollama error: %s - %s", response.status, error_text)
                    return {
                        "success": False,
                        "error": f"Ollama error: {response.status}",
                        "content": self._get_fallback_response(prompt),
                    }
        except aiohttp.ClientConnectorError:
            logger.error("Cannot connect to Ollama. Is it running?")
            return {
                "success": False,
                "error": "Ollama not reachable",
                "content": self._get_fallback_response(prompt),
            }
        except Exception as e:
            logger.error("Async LLM call failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "content": self._get_fallback_response(prompt),
            }

    # ── Streaming ──────────────────────────────────────────────────
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        Stream LLM response token-by-token.

        Ollama's /api/chat with stream=true emits one JSON object per line,
        so we buffer raw bytes and split on newlines ourselves rather than
        relying on aiohttp's line iteration (which yields nothing here).
        """
        try:
            messages = self._prepare_messages(prompt, kwargs.get("system_message"))
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    headers=self._headers(),
                    json={
                        "model": kwargs.get("model", self.model),
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": kwargs.get("temperature", 0.3),
                            "num_predict": kwargs.get("max_tokens", 800),
                        },
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("Ollama stream error: %s - %s", response.status, error_text)
                        return

                    buffer = b""
                    async for chunk in response.content.iter_chunked(512):
                        buffer += chunk
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line.decode("utf-8"))
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                continue

                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done"):
                                return

                    # Flush any trailing partial line
                    if buffer.strip():
                        try:
                            data = json.loads(buffer.decode("utf-8"))
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            pass

        except Exception as e:
            logger.error("LLM streaming failed: %s", e)
            return

    # ── Fallback ───────────────────────────────────────────────────
    def _get_fallback_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "readme" in prompt_lower:
            return (
                "# Project\n\nGenerated by CodeAtlas (AI unavailable). "
                "Please install Ollama for AI-powered documentation."
            )
        if "summary" in prompt_lower or "analyze" in prompt_lower:
            return "AI analysis unavailable. Please ensure Ollama is running with the configured model."
        if "security" in prompt_lower:
            return "Security analysis unavailable. Please check the raw security findings in the report."
        return "AI response unavailable. Please check Ollama connection."


# Global instance
llm_client = LLMClient()


# Legacy wrappers
def call_llm(prompt: str, **kwargs) -> str:
    return llm_client.call(prompt, **kwargs)


async def call_llm_async(prompt: str, **kwargs) -> Dict[str, Any]:
    return await llm_client.call_async(prompt, **kwargs)


async def stream_llm_response(prompt: str) -> AsyncGenerator[str, None]:
    async for chunk in llm_client.stream(prompt):
        yield chunk