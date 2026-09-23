"""
Secret scanning for code repositories.
"""
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,50})(["\'])', "API_KEY"),
    (r'(?i)(secret[_-]?key["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,50})(["\'])', "SECRET_KEY"),
    (r'(?i)(access[_-]?token["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,100})(["\'])', "ACCESS_TOKEN"),
    (r'(?i)(refresh[_-]?token["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,100})(["\'])', "REFRESH_TOKEN"),
    (r'(?i)(password["\']?\s*[:=]\s*["\'])([^"\']{6,50})(["\'])', "PASSWORD"),
    (r'(?i)(passwd["\']?\s*[:=]\s*["\'])([^"\']{6,50})(["\'])', "PASSWORD"),
    (r'(?i)(database[_-]?url["\']?\s*[:=]\s*["\'])([^"\']+://[^"\']+)(["\'])', "DATABASE_URL"),
    (r'(?i)(postgres[_-]?url["\']?\s*[:=]\s*["\'])([^"\']+://[^"\']+)(["\'])', "DATABASE_URL"),
    (r'(?i)(aws[_-]?access[_-]?key["\']?\s*[:=]\s*["\'])([A-Z0-9]{20})(["\'])', "AWS_ACCESS_KEY"),
    (r'(?i)(aws[_-]?secret[_-]?key["\']?\s*[:=]\s*["\'])([a-zA-Z0-9/+]{40})(["\'])', "AWS_SECRET_KEY"),
    (r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----", "SSH_PRIVATE_KEY"),
    (r'(?i)(private[_-]?key["\']?\s*[:=]\s*["\'])(0x[a-fA-F0-9]{64})(["\'])', "CRYPTO_PRIVATE_KEY"),
]

FALSE_POSITIVES = [
    r"EXAMPLE_KEY", r"SAMPLE_KEY", r"YOUR_KEY_HERE", r"PUT_YOUR_KEY_HERE",
    r"00000000-0000-0000-0000-000000000000",
    r"test_key", r"dummy_key", r"fake_key",
    r"password123", r"admin123", r"changeme",
]

# Paths we never scan. Minified bundles, vendored code, lockfiles, etc.
EXCLUDED_PATH_SUBSTRINGS = [
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".min.js",
    ".min.css",
    ".umd.js",
    ".bundle.js",
    ".chunk.js",
    ".pyc",
    ".pyo",
    "/.git/",
    "/node_modules/",
    "/dist/",
    "/build/",
    "/vendor/",
    "/.venv/",
    "/venv/",
    "/__pycache__/",
]

SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".go", ".rb", ".php",
    ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf",
    ".env", ".properties",
    ".txt", ".md", ".rst",
}


def scan_secrets(files: List[str]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for file_path in files:
        if _should_skip_file(file_path):
            continue
        try:
            findings.extend(_scan_file(file_path))
        except (IOError, UnicodeDecodeError, PermissionError):
            continue
    return findings


def _scan_file(file_path: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    file_ext = Path(file_path).suffix.lower()

    if file_ext not in SCANNABLE_EXTENSIONS and not file_path.endswith(".env"):
        return findings

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            if len(content) > 10 * 1024 * 1024:
                return findings

            for line_num, line in enumerate(content.split("\n"), 1):
                findings.extend(_scan_line(line, line_num, file_path))
    except Exception:
        return findings

    return findings


def _scan_line(
    line: str,
    line_num: int,
    file_path: str,
    commit: str = None,
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    matched_spans: List[tuple] = []

    for pattern, secret_type in SECRET_PATTERNS:
        for match in re.finditer(pattern, line):
            secret_value = match.group(2) if len(match.groups()) >= 2 else match.group(0)
            if _is_false_positive(secret_value):
                continue

            risk_score = _calculate_risk_score(secret_type, secret_value)
            finding = {
                "file": file_path,
                "line": line_num,
                "type": secret_type,
                "value_preview": _mask_secret(secret_value),
                "risk_score": risk_score,
                "risk_level": _get_risk_level(risk_score),
                "context": line.strip()[:200],
                "full_match": match.group(0),
            }
            if commit:
                finding["commit"] = commit

            findings.append(finding)
            matched_spans.append(match.span())

    # Supplementary high-entropy pass
    for match in re.finditer(r"""['"]([A-Za-z0-9+/_\-]{20,})['"]""", line):
        span = match.span(1)
        if any(span[0] >= s and span[1] <= e for s, e in matched_spans):
            continue

        candidate = match.group(1)
        if _is_false_positive(candidate):
            continue
        if _shannon_entropy(candidate) < 4.3:
            continue

        risk_score = _calculate_risk_score("HIGH_ENTROPY_STRING", candidate)
        finding = {
            "file": file_path,
            "line": line_num,
            "type": "HIGH_ENTROPY_STRING",
            "value_preview": _mask_secret(candidate),
            "risk_score": risk_score,
            "risk_level": _get_risk_level(risk_score),
            "context": line.strip()[:200],
            "full_match": match.group(0),
        }
        if commit:
            finding["commit"] = commit
        findings.append(finding)

    return findings


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    probs = [value.count(c) / len(value) for c in set(value)]
    return -sum(p * math.log2(p) for p in probs)


def _should_skip_file(file_path: str) -> bool:
    path_lower = file_path.lower().replace("\\", "/")
    for substr in EXCLUDED_PATH_SUBSTRINGS:
        if substr in path_lower:
            return True

    try:
        if os.path.getsize(file_path) > 5 * 1024 * 1024:
            return True
    except OSError:
        return True
    return False


def _is_false_positive(secret_value: str) -> bool:
    secret_lower = secret_value.lower()
    for fp_pattern in FALSE_POSITIVES:
        if re.search(fp_pattern, secret_lower, re.IGNORECASE):
            return True
    if re.match(r"^(xxx+|test|example|dummy|fake|placeholder)", secret_lower):
        return True
    if len(secret_value) < 8:
        return True
    return False


def _calculate_risk_score(secret_type: str, secret_value: str) -> int:
    score = 50
    type_weights = {
        "SSH_PRIVATE_KEY": 40,
        "CRYPTO_PRIVATE_KEY": 40,
        "AWS_SECRET_KEY": 30,
        "SECRET_KEY": 25,
        "ACCESS_TOKEN": 20,
        "API_KEY": 15,
        "PASSWORD": 10,
        "DATABASE_URL": 15,
        "HIGH_ENTROPY_STRING": 5,
    }
    score += type_weights.get(secret_type, 0)
    if len(secret_value) >= 32:
        score += 10
    if re.search(r"[A-Z]", secret_value) and re.search(r"[a-z]", secret_value):
        score += 5
    if re.search(r"\d", secret_value):
        score += 5
    if re.search(r"[^A-Za-z0-9]", secret_value):
        score += 5
    return min(score, 100)


def _get_risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "info"


def _mask_secret(secret: str) -> str:
    if len(secret) <= 8:
        return "***"
    first_part = secret[:4]
    last_part = secret[-4:]
    mask_length = len(secret) - 8
    if mask_length > 0:
        return f"{first_part}{'*' * mask_length}{last_part}"
    return f"{first_part}{'*' * (len(secret) - 4)}"


def scan_secrets_git_history(repo_path: str, max_commits: int = 200) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    repo = Path(repo_path)

    if not (repo / ".git").exists():
        return findings

    try:
        log = subprocess.run(
            ["git", "-C", str(repo), "log", f"-n{max_commits}", "--pretty=format:%H"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return findings

    commit_hashes = [c for c in log.stdout.splitlines() if c.strip()]

    for commit_hash in commit_hashes:
        try:
            diff = subprocess.run(
                ["git", "-C", str(repo), "show", commit_hash, "--unified=0", "--", "."],
                capture_output=True, text=True, errors="ignore", timeout=30,
            )
        except (subprocess.SubprocessError, OSError):
            continue

        current_file = None
        line_num = 0
        for line in diff.stdout.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:]
                continue
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                line_num = int(match.group(1)) if match else 0
                continue
            if not line.startswith("+") or line.startswith("+++"):
                continue

            content = line[1:]
            if current_file and _should_skip_file(current_file):
                line_num += 1
                continue

            findings.extend(
                _scan_line(content, line_num, current_file or "unknown", commit=commit_hash[:8])
            )
            line_num += 1

    return findings


def summarize_findings(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not findings:
        return {
            "total_findings": 0,
            "risk_level": "none",
            "by_type": {},
            "by_risk": {},
            "critical_findings": [],
            "high_findings": [],
        }

    by_type: Dict[str, int] = {}
    by_risk: Dict[str, int] = {}
    for finding in findings:
        by_type[finding["type"]] = by_type.get(finding["type"], 0) + 1
        by_risk[finding["risk_level"]] = by_risk.get(finding["risk_level"], 0) + 1

    if by_risk.get("critical", 0) > 0:
        overall_risk = "critical"
    elif by_risk.get("high", 0) > 0:
        overall_risk = "high"
    elif by_risk.get("medium", 0) > 0:
        overall_risk = "medium"
    elif by_risk.get("low", 0) > 0:
        overall_risk = "low"
    else:
        overall_risk = "info"

    return {
        "total_findings": len(findings),
        "risk_level": overall_risk,
        "by_type": by_type,
        "by_risk": by_risk,
        "critical_findings": [f for f in findings if f["risk_level"] == "critical"][:5],
        "high_findings": [f for f in findings if f["risk_level"] == "high"][:5],
    }