"""
AI-powered summarization utilities for CodeAtlas.

The system prompt is tuned for a non-technical reader: short sentences,
bullet lists, no giant tables. A repair pass fixes the common LLM failure
mode where a markdown table is emitted as a single long line - that
produces a wall of pipe characters when rendered.
"""
import json
import logging
import re
from typing import Any, Dict

from app.services.ai.llm_client import call_llm, call_llm_async

logger = logging.getLogger(__name__)


SUMMARY_SYSTEM_PROMPT = (
    "You are CodeAtlas AI, a code review assistant writing for a busy "
    "developer who wants the highlights, not an essay. "
    "Rules:\n"
    "- Keep it short. Aim for under 400 words total.\n"
    "- Use short paragraphs and bullet lists. Never emit a markdown table.\n"
    "- Lead with the single most important thing they should fix.\n"
    "- Name concrete files when relevant.\n"
    "- Do not restate the numbers in the input - the user already saw them.\n"
    "- Never invent issues that aren't in the input.\n"
)


def _repair_markdown(text: str) -> str:
    """
    Fix LLM output that has collapsed a markdown table into one line.
    Also strips any table syntax entirely if repair doesn't work -
    bullet lists are always readable.
    """
    if not text:
        return text

    # 1. Split runaway table rows: "| a | b | |---|---| | c | d |"
    if "|" in text and "---|" in text.replace(" ", ""):
        # Insert a newline before every "|" that starts a new row.
        # Pattern: "| something | | next-something |" -> split at "| |".
        text = re.sub(r"\|\s*\|", "|\n|", text)

    # 2. Anything still containing table pipes on one very long line:
    # collapse to a plain sentence so it doesn't produce a pipe wall.
    lines = text.split("\n")
    fixed = []
    for line in lines:
        if line.count("|") > 6 and len(line) > 300:
            # Convert "| a | b | c |" into "a - b - c"
            cells = [c.strip() for c in line.strip("|").split("|") if c.strip()]
            fixed.append(" - ".join(cells))
        else:
            fixed.append(line)
    return "\n".join(fixed)


async def summarize_codebase(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate an AI-powered summary of an analyzed codebase.

    Takes a single dict (the full analysis result).
    """
    try:
        metrics = analysis_data.get("metrics", {}) or {}
        security = analysis_data.get("security", {}) or {}
        complexity = analysis_data.get("complexity", {}) or {}
        summary = analysis_data.get("summary", {}) or {}

        prompt = f"""
Summarize the following code analysis for a developer. Be brief.
Lead with the single most important issue.

Repository: {analysis_data.get('path', 'Unknown')}
Total files: {summary.get('total_files', 0)}
Primary language: {(analysis_data.get('languages') or {}).get('primary_language', 'Unknown')}
Other languages: {', '.join(list((analysis_data.get('languages') or {}).get('detected_languages', {}).keys())[:5])}

Secrets found (working tree + git history): {security.get('secrets_found', 0)}
Vulnerabilities found: {security.get('vulnerabilities_found', 0)}
Vulnerability breakdown by severity: {json.dumps(security.get('by_severity', {}))}

Average complexity (primary language): {complexity.get('avg_complexity_score', 0)}
Complexity confidence: {complexity.get('confidence', 'unknown')}

Write:
1. One sentence describing the biggest risk or, if none, the biggest opportunity.
2. Three to five bullet points of what to fix, most urgent first.
3. One closing sentence of encouragement if the codebase is in good shape.

Do not include a table. Do not restate file counts.
"""

        result = await call_llm_async(
            prompt,
            system_message=SUMMARY_SYSTEM_PROMPT,
            temperature=0.3,
        )

        raw = result.get("content", "AI summary unavailable")
        return {
            "ai_summary": _repair_markdown(raw),
            "analysis_id": analysis_data.get("analysis_id"),
            "generated_at": analysis_data.get("timestamp"),
            "model_used": analysis_data.get("llm_model", "ollama"),
        }

    except Exception as e:
        logger.error("AI summarization failed: %s", e)
        return {"ai_summary": "AI summary unavailable", "error": str(e)}


def generate_readme_content(analysis_data: Dict[str, Any]) -> str:
    prompt = f"""
Write a README.md for this project. Use clear headings. Keep it
practical - no marketing filler. Include: overview, install, usage,
project structure, and a short "what this does" section.

Analysis summary:
{json.dumps(analysis_data, indent=2, default=str)[:4000]}
"""
    raw = call_llm(prompt, system_message=SUMMARY_SYSTEM_PROMPT)
    return _repair_markdown(raw)


def explain_complex_file(file_path: str, code_content: str) -> str:
    prompt = f"""
Explain this file in plain English for a developer who has never seen it.

File: {file_path}

{code_content[:2000]}

Answer in this order:
- What this file does (one sentence).
- The main functions or classes and their job (bullets).
- Any obvious code smells or risks (bullets, or "none obvious").
"""
    raw = call_llm(prompt, system_message=SUMMARY_SYSTEM_PROMPT)
    return _repair_markdown(raw)