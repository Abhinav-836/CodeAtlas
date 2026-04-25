"""
LLM client abstraction for CodeAtlas with Ollama support.
Handles sync, async, and streaming AI responses using local models.
"""

import asyncio
import logging
import json
import aiohttp
import requests
from typing import Dict, Any, AsyncGenerator, Optional, List
from app.core.config import settings
import os

logger = logging.getLogger(__name__)


class LLMClient:
    """Ollama-based LLM client for CodeAtlas."""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL or "http://localhost:11434"
        self.model = settings.LLM_MODEL or "gpt-oss:20b-cloud"
        self.timeout = settings.LLM_TIMEOUT or 60
        self.api_key = os.getenv("OLLAMA_API_KEY", "")

    def _prepare_messages(self, prompt: str, system_message: Optional[str] = None) -> List[Dict[str, str]]:
        """Prepare messages in Ollama format."""
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        return messages
    
    def call(self, prompt: str, **kwargs) -> str:
        """
        Synchronous LLM call.
        Used for quick responses like README generation.
        """
        try:
            messages = self._prepare_messages(
                prompt, 
                kwargs.get("system_message")
            )
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.3),
                        "num_predict": kwargs.get("max_tokens", 800),
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            else:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                return self._get_fallback_response(prompt)
                
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama. Is it running?")
            return self._get_fallback_response(prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._get_fallback_response(prompt)
    
    async def call_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Async LLM call.
        Used for AI summaries and heavy analysis.
        """
        headers = {
        "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            messages = self._prepare_messages(
                prompt,
                kwargs.get("system_message")
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": kwargs.get("model", self.model),
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": kwargs.get("temperature", 0.3),
                            "num_predict": kwargs.get("max_tokens", 800),
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("message", {}).get("content", "")
                        return {
                            "success": True,
                            "content": content,
                            "model": self.model
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama error: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"Ollama error: {response.status}",
                            "content": self._get_fallback_response(prompt)
                        }
                        
        except aiohttp.ClientConnectorError:
            logger.error("Cannot connect to Ollama. Is it running?")
            return {
                "success": False,
                "error": "Ollama not reachable",
                "content": self._get_fallback_response(prompt)
            }
        except Exception as e:
            logger.error(f"Async LLM call failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": self._get_fallback_response(prompt)
            }
    
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        Stream LLM response token-by-token.
        Useful for UI streaming.
        """
        try:
            messages = self._prepare_messages(
                prompt,
                kwargs.get("system_message")
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": kwargs.get("model", self.model),
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": kwargs.get("temperature", 0.3),
                            "num_predict": kwargs.get("max_tokens", 800),
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data:
                                    content = data["message"].get("content", "")
                                    if content:
                                        yield content
                                if data.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            yield ""
    
    def _get_fallback_response(self, prompt: str) -> str:
        """Provide fallback responses when LLM is unavailable."""
        prompt_lower = prompt.lower()
        
        if "readme" in prompt_lower:
            return "# Project\n\nGenerated by CodeAtlas (AI unavailable). Please install Ollama for AI-powered documentation."
        elif "summary" in prompt_lower or "analyze" in prompt_lower:
            return "AI analysis unavailable. Please ensure Ollama is running with the gpt-oss model."
        elif "security" in prompt_lower:
            return "Security analysis unavailable. Please check the raw security findings in the report."
        else:
            return "AI response unavailable. Please check Ollama connection."


# Global LLM client instance
llm_client = LLMClient()


# Legacy function wrappers for backward compatibility
def call_llm(prompt: str, **kwargs) -> str:
    """Legacy wrapper for sync calls."""
    return llm_client.call(prompt, **kwargs)


async def call_llm_async(prompt: str, **kwargs) -> Dict[str, Any]:
    """Legacy wrapper for async calls."""
    return await llm_client.call_async(prompt, **kwargs)


async def stream_llm_response(prompt: str) -> AsyncGenerator[str, None]:
    """Legacy wrapper for streaming."""
    async for chunk in llm_client.stream(prompt):
        yield chunk
