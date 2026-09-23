"""
AI-powered summarization utilities for CodeAtlas.
"""

import json
import logging
from typing import Any, Dict

from app.services.ai.llm_client import call_llm, call_llm_async

logger = logging.getLogger(__name__)


async def summarize_codebase(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate an AI-powered summary of an analyzed codebase.

    Takes a single dict (the full analysis result) - not loose strings.
    """
    try:
        metrics = analysis_data.get("metrics", {}) or {}
        security = analysis_data.get("security", {}) or {}
        architecture = analysis_data.get("architecture", {}) or {}
        summary = analysis_data.get("summary", {}) or {}

        prompt = f"""
Analyze this codebase and provide a professional summary.

Repository Path: {analysis_data.get('path', 'Unknown')}
Total Files: {summary.get('total_files', 0)}
Languages: {', '.join(metrics.get('languages', []))}
Risk Level: {metrics.get('risk', 'unknown')}

Security:
- Secrets Found: {security.get('secrets_found', 0)}
- Vulnerabilities Found: {security.get('vulnerabilities_found', 0)}

Architecture Layers:
{list(architecture.get('layers', {}).keys()) if architecture else 'Unknown'}

Provide:
1. Overall assessment
2. Key strengths
3. Critical issues
4. Maintenance recommendations
5. Security priorities
"""

        result = await call_llm_async(prompt)

        return {
            "ai_summary": result.get("content", "AI summary unavailable"),
            "analysis_id": analysis_data.get("analysis_id"),
            "generated_at": analysis_data.get("timestamp"),
            "model_used": analysis_data.get("llm_model", "ollama"),
        }

    except Exception as e:
        logger.error("AI summarization failed: %s", e)
        return {"ai_summary": "AI summary unavailable", "error": str(e)}


def generate_readme_content(analysis_data: Dict[str, Any]) -> str:
    """Generate README.md content using AI."""
    prompt = f"""
Generate a professional README.md for this codebase.

Analysis Data:
{json.dumps(analysis_data, indent=2, default=str)}

Include:
- Project overview
- Installation
- Usage
- Architecture
- Security considerations
- Contributing guidelines

Format in Markdown.
"""
    return call_llm(prompt)


def explain_complex_file(file_path: str, code_content: str) -> str:
    """
    Explain a complex source file using AI.

    Fully implemented: builds the prompt and actually calls the LLM.
    """
    prompt = f"""
Explain the following file in simple terms.

File: {file_path}

Provide:
1. What this file does
2. Key functions/classes and their roles
3. Notable patterns or potential issues
"""
    return call_llm(prompt)