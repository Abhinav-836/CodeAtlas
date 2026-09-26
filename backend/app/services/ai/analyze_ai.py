"""
AI-powered analysis enhancements.
"""
import json
import logging
from typing import Any, Dict

from app.core.config import settings
from app.services.ai.llm_client import llm_client
from app.services.ai.summarizer import SUMMARY_SYSTEM_PROMPT, _repair_markdown

logger = logging.getLogger(__name__)


async def enhance_with_ai(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """Add AI-powered insights to the analysis result."""
    if not settings.ENABLE_AI_INSIGHTS:
        return analysis_result

    try:
        security = analysis_result.get("security", {}) or {}
        complexity = analysis_result.get("complexity", {}) or {}
        languages = analysis_result.get("languages", {}) or {}

        # Keep the payload tight - the LLM doesn't need the whole report.
        payload = {
            "repo": analysis_result.get("repo_name") or analysis_result.get("path"),
            "primary_language": languages.get("primary_language"),
            "other_languages": list(languages.get("detected_languages", {}).keys())[:5],
            "total_files": analysis_result.get("summary", {}).get("total_files", 0),
            "risk_level": analysis_result.get("overall_risk_level"),
            "secrets_found": security.get("secrets_found", 0),
            "vulnerabilities_found": security.get("vulnerabilities_found", 0),
            "severity_breakdown": security.get("by_severity", {}),
            "avg_complexity": complexity.get("avg_complexity_score", 0),
            "confidence": complexity.get("confidence"),
            "top_complex_files": [
                {"file": f.get("file"), "score": f.get("complexity_score")}
                for f in (complexity.get("most_complex_files") or [])[:3]
            ],
        }

        prompt = f"""
Read the following analysis and write a short executive summary for a
developer. Rules:
- Under 300 words.
- Lead with the single most urgent item.
- Use bullet lists. No tables.
- Reference file names where relevant.
- If the codebase is clean, say so and stop.

Analysis:
{json.dumps(payload, indent=2)}
"""

        response = await llm_client.call_async(
            prompt,
            system_message=SUMMARY_SYSTEM_PROMPT,
            temperature=0.3,
        )

        if response.get("success"):
            analysis_result["ai_insights"] = {
                "summary": _repair_markdown(response["content"]),
                "model": llm_client.model,
            }
        else:
            analysis_result["ai_insights"] = {
                "summary": response.get("content", "AI unavailable"),
                "model": llm_client.model,
                "fallback": True,
            }

    except Exception as e:
        logger.error("AI enhancement failed: %s", e)
        analysis_result["ai_insights"] = {"error": str(e)}

    return analysis_result