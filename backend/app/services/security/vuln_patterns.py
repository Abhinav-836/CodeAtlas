"""
Vulnerability pattern scanning.

Precision-first design:
- Python files are parsed with `ast` so we only flag real Call nodes on
  dangerous bare names, not `obj.eval(...)`, `re.compile(...)`, or a
  variable that happens to be named `exec`.
- Non-Python files use a small set of conservative regexes designed to
  avoid matching common idioms.
- Minified / vendored / generated files are skipped entirely.

What this scanner is good at: catching obvious footguns (bare `eval`,
`pickle.loads` on untrusted input, `shell=True`, hardcoded key shapes).
What it is NOT: a dataflow analyzer. `x = user_input; eval(x)` and
`eval("1+1")` look identical to it. Treat findings as leads.
"""
import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------
# Non-Python patterns. Deliberately conservative - each one requires a
# specific shape, not a keyword.
# ---------------------------------------------------------------------
INSECURE_PATTERNS: List[Tuple[str, str, str, str]] = [
    # (regex, vuln_type, severity, description)

    # --- Command injection (only when shell=True is present) ---
    (r"subprocess\.(?:run|call|Popen|check_output)\s*\([^)]*shell\s*=\s*True",
     "shell_injection", "high", "subprocess call with shell=True"),

    # --- Insecure TLS (only in requests/httpx calls) ---
    (r"(?:requests|httpx)\.(?:get|post|put|delete|patch|request)\s*\([^)]*verify\s*=\s*False",
     "insecure_tls", "high", "HTTPS verification disabled"),

    # --- Hardcoded cloud keys in string literals ---
    (r'["\']AKIA[0-9A-Z]{16}["\']',
     "aws_key", "critical", "Hardcoded AWS access key ID"),
    (r'["\'](?:sk|pk)_(?:live|test)_[a-zA-Z0-9]{20,}["\']',
     "stripe_key", "critical", "Hardcoded Stripe key"),

    # --- Node.js child_process injection ---
    (r"child_process\.exec\s*\(",
     "node_exec", "high", "child_process.exec (shell invocation)"),
    (r"child_process\.execSync\s*\(",
     "node_exec", "high", "child_process.execSync (shell invocation)"),

    # --- Insecure deserialization (non-Python) ---
    (r"\bunserialize\s*\(",
     "php_unserialize", "high", "PHP unserialize on untrusted input"),
]

# ---------------------------------------------------------------------
# Python AST: functions that are only dangerous when called as a bare
# identifier (not as a method / not as `re.compile` / etc.)
# ---------------------------------------------------------------------
DANGEROUS_PYTHON_CALLS: Dict[str, Tuple[str, str, str]] = {
    # name -> (vuln_type, severity, description)
    "eval":     ("code_execution", "high", "eval() on potentially untrusted input"),
    "exec":     ("code_execution", "high", "exec() on potentially untrusted input"),
    "compile":  ("code_execution", "medium", "compile() on potentially untrusted input"),
    "__import__": ("dynamic_import", "high", "Dynamic import via __import__"),
}

DANGEROUS_PYTHON_METHODS: Dict[str, Tuple[str, str, str]] = {
    # dotted-name -> (vuln_type, severity, description)
    "pickle.loads":         ("insecure_deserialization", "high", "pickle.loads on untrusted input"),
    "pickle.load":          ("insecure_deserialization", "high", "pickle.load on untrusted input"),
    "cPickle.loads":        ("insecure_deserialization", "high", "cPickle.loads on untrusted input"),
    "cPickle.load":         ("insecure_deserialization", "high", "cPickle.load on untrusted input"),
    "marshal.loads":        ("insecure_deserialization", "high", "marshal.loads on untrusted input"),
    "yaml.load":            ("insecure_deserialization", "medium", "yaml.load without SafeLoader"),
    "os.system":            ("command_injection", "high", "os.system (shell invocation)"),
    "os.popen":             ("command_injection", "high", "os.popen (shell invocation)"),
    "subprocess.Popen":     ("command_injection", "medium", "subprocess.Popen - verify shell=False"),
    "subprocess.call":      ("command_injection", "medium", "subprocess.call - verify shell=False"),
    "subprocess.run":       ("command_injection", "medium", "subprocess.run - verify shell=False"),
}

# Names that, if called as a bare identifier, are the *Python builtin* -
# but which are safe when they appear as a dotted attribute. This list
# documents the intent even though the AST walker already handles it.
SAFE_DOTTED_NAMES = {"re.compile", "regex.compile", "pattern.compile"}


def scan_vulnerabilities(files: List[str]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for file_path in files:
        if not _should_scan_file(file_path):
            continue
        try:
            findings.extend(_scan_file_for_vulns(file_path))
        except Exception:
            continue

    # Deduplicate: same (file, line, pattern) reported once.
    seen = set()
    unique: List[Dict[str, Any]] = []
    for f in findings:
        key = (f.get("file"), f.get("line"), f.get("pattern"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)

    return unique


def _should_scan_file(file_path: str) -> bool:
    path_lower = file_path.lower().replace("\\", "/")

    skip_substrings = [
        "/node_modules/",
        "/dist/",
        "/build/",
        "/vendor/",
        "/.venv/",
        "/venv/",
        "/__pycache__/",
        "/.git/",
        ".min.js",
        ".min.css",
        ".umd.js",
        ".bundle.js",
        ".chunk.js",
    ]
    for s in skip_substrings:
        if s in path_lower:
            return False

    ext = Path(file_path).suffix.lower()
    scannable = {
        ".py",
        ".js", ".jsx", ".ts", ".tsx",
        ".rb", ".php",
        ".yml", ".yaml",
    }
    return ext in scannable


def _scan_file_for_vulns(file_path: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    ext = Path(file_path).suffix.lower()

    if ext == ".py":
        findings.extend(_scan_python_with_ast(file_path))
        # Still run the regex pass: catches `shell=True`, `verify=False`
        # which are easier to spot textually.
        findings.extend(_scan_with_patterns(file_path))
    else:
        findings.extend(_scan_with_patterns(file_path))

    return findings


# ---------------------------------------------------------------------
# Python AST scan
# ---------------------------------------------------------------------
def _scan_python_with_ast(file_path: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, IOError, OSError):
        return findings

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return findings

    lines = content.split("\n")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        # Bare-name call: eval(...), exec(...), __import__(...)
        if isinstance(func, ast.Name):
            meta = DANGEROUS_PYTHON_CALLS.get(func.id)
            if meta:
                vuln_type, severity, desc = meta
                findings.append({
                    "file": file_path,
                    "line": node.lineno,
                    "pattern": f"{func.id}()",
                    "type": vuln_type,
                    "severity": severity,
                    "description": desc,
                    "context": _line_at(lines, node.lineno),
                })
            continue

        # Dotted call: pickle.loads(...), os.system(...)
        if isinstance(func, ast.Attribute):
            dotted = _get_full_attribute_name(func)
            if dotted in SAFE_DOTTED_NAMES:
                continue
            meta = DANGEROUS_PYTHON_METHODS.get(dotted)
            if meta:
                vuln_type, severity, desc = meta
                # subprocess.* with shell=True is caught by the regex pass
                # at higher severity - skip the AST version to avoid dupes.
                if dotted.startswith("subprocess."):
                    continue
                findings.append({
                    "file": file_path,
                    "line": node.lineno,
                    "pattern": dotted,
                    "type": vuln_type,
                    "severity": severity,
                    "description": desc,
                    "context": _line_at(lines, node.lineno),
                })
                continue

    return findings


def _get_full_attribute_name(node: ast.Attribute) -> str:
    parts = []
    cur: Any = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def _line_at(lines: List[str], lineno: int) -> str:
    if 0 < lineno <= len(lines):
        return lines[lineno - 1].strip()[:200]
    return ""


# ---------------------------------------------------------------------
# Regex scan (non-Python + Python extras like shell=True)
# ---------------------------------------------------------------------
def _scan_with_patterns(file_path: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except (IOError, OSError, UnicodeDecodeError):
        return findings

    # Skip anything obviously huge - perf guard
    if len(content) > 2 * 1024 * 1024:
        return findings

    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "*", "/*")):
            continue

        for pattern, vuln_type, severity, description in INSECURE_PATTERNS:
            if re.search(pattern, line):
                findings.append({
                    "file": file_path,
                    "line": line_num,
                    "pattern": vuln_type,
                    "type": "pattern_match",
                    "severity": severity,
                    "description": description,
                    "context": line.strip()[:200],
                })

    return findings


# ---------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------
def summarize_vulnerabilities(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not findings:
        return {
            "total_findings": 0,
            "by_severity": {},
            "by_type": {},
            "critical_findings": [],
            "high_findings": [],
        }

    by_severity: Dict[str, int] = {}
    by_type: Dict[str, int] = {}

    for finding in findings:
        severity = finding.get("severity", "medium")
        vuln_type = finding.get("type", "unknown")
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_type[vuln_type] = by_type.get(vuln_type, 0) + 1

    return {
        "total_findings": len(findings),
        "by_severity": by_severity,
        "by_type": by_type,
        "critical_findings": [f for f in findings if f.get("severity") == "critical"][:10],
        "high_findings": [f for f in findings if f.get("severity") == "high"][:10],
    }