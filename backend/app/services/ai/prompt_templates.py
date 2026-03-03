
# ✅ 3️⃣ `app/services/ai/prompt_templates.py` (FULL FILE – FIXED)

"""
AI prompt templates for CodeAtlas analysis.
"""

import json

# ===== OVERALL ANALYSIS =====
OVERALL_SUMMARY_PROMPT = """
Analyze this codebase and provide an executive summary.

Repository:
- Path: {repo_info[path]}
- Total Files: {repo_info[files]}
- Languages: {', '.join(repo_info[languages]) if repo_info[languages] else 'Unknown'}

Risk Level: {risk_level}
Risk Score: {metrics[risk_score]}/100
File Types:
{json.dumps(metrics.get('file_types', {}), indent=2)}

Provide:
1. Overall health
2. Key strengths
3. Critical issues
4. Maintainability score (1–10)
5. One-line project description
"""

# ===== SECURITY =====
SECURITY_PROMPT = """
Perform a security review.

Secrets Found: {secrets_found}
Vulnerabilities Found: {vulnerabilities_found}
Risk Level: {risk_level}

Critical Findings:
{json.dumps(critical_findings[:3], indent=2) if critical_findings else 'None'}

High Severity Findings:
{json.dumps(high_findings[:3], indent=2) if high_findings else 'None'}

Provide:
1. Security posture
2. Immediate fixes
3. Missing best practices
4. Remediation timeline
5. Long-term strategy

Rate security maturity (1–5).
"""

# ===== ARCHITECTURE =====
ARCH_SUMMARY_PROMPT = """
Analyze the architecture.

Layers:
{json.dumps(layers, indent=2)}

File Distribution:
{json.dumps(file_distribution, indent=2)}

Provide:
1. Patterns detected
2. Coupling/cohesion
3. Scalability
4. Technical debt
5. Architecture score (1–10)
"""

# ===== CODE QUALITY =====
CODE_QUALITY_PROMPT = """
Assess code quality.

Files: {file_count}
Total Lines: {total_lines}
Large Files: {large_files}
Risk Score: {risk_score}/100
Python Complexity: {python_complexity}

Provide:
1. Quality overview
2. Maintainability issues
3. Complexity hotspots
4. Code smells
5. Technical debt estimate

Rate quality (1–10).
"""

# ===== RECOMMENDATIONS =====
RECOMMENDATIONS_PROMPT = """
Based on this analysis:
{analysis_summary}

Provide 5–8 recommendations.

Format:
Category:
Priority:
Title:
Description:
Action:
"""

# ===== README =====
README_GENERATION_PROMPT = """
Generate a complete README.md.

Analysis Summary:
{analysis_summary}

Include:
- Description
- Features
- Setup
- Usage
- Architecture
- Security
- Testing
- Deployment
- Contributing
- License
"""
