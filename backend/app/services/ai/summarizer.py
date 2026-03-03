"""
AI-powered summarization utilities for CodeAtlas.
"""

import json
import logging
from typing import Dict, Any

from app.services.ai.llm_client import call_llm, call_llm_async

logger = logging.getLogger(__name__)


async def summarize_codebase(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate AI-powered summary of the analyzed codebase.
    """
    try:
        metrics = analysis_data.get("metrics", {})
        security = analysis_data.get("security", {})
        architecture = analysis_data.get("architecture", {})

        prompt = f"""
Analyze this codebase and provide a professional summary.

Repository Path: {analysis_data.get('path', 'Unknown')}
Total Files: {analysis_data.get('summary', {}).get('total_files', 0)}
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
            "model_used": analysis_data.get("llm_model", "gpt-4o-mini"),
        }

    except Exception as e:
        logger.error(f"AI summarization failed: {e}")
        return {
            "ai_summary": "AI summary unavailable",
            "error": str(e),
        }


def generate_readme_content(analysis_data: Dict[str, Any]) -> str:
    """
    Generate README.md content using AI.
    """
    prompt = f"""
Generate a professional README.md for this codebase.

Analysis Data:
{json.dumps(analysis_data, indent=2)}

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
    """
    prompt = f"""
Explain the following file in simple terms.

File: {file_path}

```python
{code_content[:2000]}
"""