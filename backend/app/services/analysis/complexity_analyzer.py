"""
Unified multi-language complexity analyzer.

Backend tiers:
  1. Python            -> real AST
  2. JavaScript / TS   -> tree-sitter (if installed)
  3. Popular others    -> regex-based heuristics
  4. Everything else   -> file-level stats

Entry point: `analyze_files(files) -> dict`

Output shape (stable, versioned):

    {
      "per_language": { "Python": {...}, "JavaScript": {...}, ... },
      "primary_language": "JavaScript",
      "total_functions": 412,
      "total_classes": 37,
      "total_lines": 15324,
      "avg_complexity_score": 8.4,
      "most_complex_files": [
        {"file": "...", "language": "Python", "complexity_score": 54, ...}
      ],
      "confidence": "ast" | "parser" | "heuristic" | "file_stats"
    }
"""
from __future__ import annotations

import ast
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Optional JS/TS parser ───────────────────────────────────────────
try:
    from tree_sitter import Language, Parser
    import tree_sitter_javascript as _tsjs

    _JS_LANGUAGE = Language(_tsjs.language())
    _TS_AVAILABLE = True
except Exception:
    _JS_LANGUAGE = None
    _TS_AVAILABLE = False

try:
    import tree_sitter_typescript as _tsts

    _TS_LANGUAGE = Language(_tsts.language_typescript())
    _TSX_LANGUAGE = Language(_tsts.language_tsx())
except Exception:
    _TS_LANGUAGE = None
    _TSX_LANGUAGE = None


# ── Language detection ──────────────────────────────────────────────
LANGUAGE_BY_EXT: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".kt": "Kotlin", ".kts": "Kotlin",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell", ".bash": "Shell",
    ".lua": "Lua",
    ".pl": "Perl",
    ".r": "R",
}

# Language → (function regex, class regex or None, decision-token regexes)
_HEURISTIC_CONFIG: Dict[str, Dict[str, Any]] = {
    "Java": {
        "function": r"\b(?:public|private|protected|static|final|synchronized|abstract|native|strictfp|\s)*[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)\s*\{",
        "class": r"\b(?:class|interface|enum|record)\s+\w+",
        "decision": [r"\bif\s*\(", r"\belse\s+if\s*\(", r"\bfor\s*\(", r"\bwhile\s*\(", r"\bcase\s+", r"\bcatch\s*\(", r"&&", r"\|\|"],
    },
    "Go": {
        "function": r"\bfunc\s+(?:\([^)]*\)\s*)?(\w+)\s*\(",
        "class": r"\btype\s+\w+\s+struct\b",
        "decision": [r"\bif\s+", r"\belse\s+if\s+", r"\bfor\s+", r"\bcase\s+", r"\bselect\s*\{", r"&&", r"\|\|"],
    },
    "Rust": {
        "function": r"\bfn\s+(\w+)\s*[(<]",
        "class": r"\b(?:struct|enum|trait)\s+\w+",
        "decision": [r"\bif\s+", r"\belse\s+if\s+", r"\bmatch\s+", r"=>", r"\bwhile\s+", r"\bfor\s+", r"&&", r"\|\|"],
    },
    "C": {
        "function": r"^\s*(?:static\s+|inline\s+|extern\s+)*[\w\s\*]+?\b(\w+)\s*\([^;]*?\)\s*\{",
        "class": r"\b(?:struct|union|enum)\s+\w+",
        "decision": [r"\bif\s*\(", r"\belse\s+if\s*\(", r"\bfor\s*\(", r"\bwhile\s*\(", r"\bswitch\s*\(", r"\bcase\s+", r"&&", r"\|\|"],
    },
    "C++": {
        "function": r"^\s*(?:static\s+|inline\s+|virtual\s+|constexpr\s+|explicit\s+)*[\w:<>,\s\*&]+?\b(\w+)\s*\([^;]*?\)\s*(?:const\s*)?\{",
        "class": r"\b(?:class|struct|union|enum)\s+\w+",
        "decision": [r"\bif\s*\(", r"\belse\s+if\s*\(", r"\bfor\s*\(", r"\bwhile\s*\(", r"\bswitch\s*\(", r"\bcase\s+", r"\bcatch\s*\(", r"&&", r"\|\|"],
    },
    "C#": {
        "function": r"\b(?:public|private|protected|internal|static|virtual|override|async|sealed|partial|extern|unsafe|\s)+[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)\s*(?:where[^{]+)?\{",
        "class": r"\b(?:class|interface|struct|enum|record)\s+\w+",
        "decision": [r"\bif\s*\(", r"\belse\s+if\s*\(", r"\bfor\s*\(", r"\bforeach\s*\(", r"\bwhile\s*\(", r"\bswitch\s*\(", r"\bcase\s+", r"\bcatch\s*\(", r"&&", r"\|\|"],
    },
    "Ruby": {
        "function": r"\bdef\s+(\w+[?!]?)",
        "class": r"\bclass\s+\w+|\bmodule\s+\w+",
        "decision": [r"\bif\b", r"\belsif\b", r"\bunless\b", r"\bwhile\b", r"\buntil\b", r"\bcase\b", r"\bwhen\b", r"\brescue\b", r"&&", r"\|\|"],
    },
    "PHP": {
        "function": r"\bfunction\s+(\w+)\s*\(",
        "class": r"\b(?:class|interface|trait)\s+\w+",
        "decision": [r"\bif\s*\(", r"\belseif\s*\(", r"\belse\s+if\s*\(", r"\bfor\s*\(", r"\bforeach\s*\(", r"\bwhile\s*\(", r"\bswitch\s*\(", r"\bcase\s+", r"\bcatch\s*\(", r"&&", r"\|\|"],
    },
    "Kotlin": {
        "function": r"\bfun\s+(?:<[^>]+>\s*)?(\w+)\s*\(",
        "class": r"\b(?:class|object|interface)\s+\w+",
        "decision": [r"\bif\s*\(", r"\belse\s+if\s*\(", r"\bfor\s*\(", r"\bwhile\s*\(", r"\bwhen\s*\(", r"->\s*", r"\bcatch\s*\(", r"&&", r"\|\|"],
    },
    "Swift": {
        "function": r"\bfunc\s+(\w+)\s*[(<]",
        "class": r"\b(?:class|struct|enum|protocol|extension)\s+\w+",
        "decision": [r"\bif\s+", r"\belse\s+if\s+", r"\bfor\s+", r"\bwhile\s+", r"\bswitch\s+", r"\bcase\s+", r"\bguard\s+", r"\bcatch\s+", r"&&", r"\|\|"],
    },
    "Scala": {
        "function": r"\bdef\s+(\w+)\s*[(<\[]",
        "class": r"\b(?:class|trait|object)\s+\w+",
        "decision": [r"\bif\s*\(", r"\belse\s+if\s*\(", r"\bfor\s*\(", r"\bwhile\s*\(", r"\bmatch\s+", r"\bcase\s+", r"&&", r"\|\|"],
    },
    "Shell": {
        "function": r"\b(?:function\s+)?(\w+)\s*\(\s*\)\s*\{",
        "class": None,
        "decision": [r"\bif\s+\[", r"\belif\s+\[", r"\bfor\s+\w+\s+in\b", r"\bwhile\s+\[", r"\bcase\s+", r"\|\|", r"&&"],
    },
    "Lua": {
        "function": r"\bfunction\s+(?:\w+[.:])?(\w+)\s*\(",
        "class": None,
        "decision": [r"\bif\b", r"\belseif\b", r"\bfor\b", r"\bwhile\b", r"\brepeat\b", r"\band\b", r"\bor\b"],
    },
    "Perl": {
        "function": r"\bsub\s+(\w+)",
        "class": r"\bpackage\s+\w+",
        "decision": [r"\bif\s*\(", r"\belsif\s*\(", r"\bunless\s*\(", r"\bfor\s*\(", r"\bforeach\s*\(", r"\bwhile\s*\(", r"\bgiven\s*\(", r"\bwhen\s*\(", r"&&", r"\|\|"],
    },
    "R": {
        "function": r"(\w+)\s*<-\s*function\s*\(",
        "class": None,
        "decision": [r"\bif\s*\(", r"\belse\s+if\s*\(", r"\bfor\s*\(", r"\bwhile\s*\(", r"&&", r"\|\|"],
    },
}

_SKIP_PATH_SUBSTRINGS = [
    "/node_modules/", "/dist/", "/build/", "/vendor/", "/target/",
    "/.venv/", "/venv/", "/__pycache__/", "/.git/",
    ".min.js", ".min.css", ".bundle.js", ".chunk.js", ".umd.js",
    "-lock.json", "pnpm-lock.yaml", "yarn.lock",
]


def analyze_files(files: List[str]) -> Dict[str, Any]:
    """Analyze a mixed list of files. See module docstring for output shape."""
    buckets: Dict[str, List[str]] = {}
    for fp in files:
        if _skip(fp):
            continue
        lang = LANGUAGE_BY_EXT.get(Path(fp).suffix.lower())
        if lang:
            buckets.setdefault(lang, []).append(fp)

    if not buckets:
        return _empty_result()

    per_language: Dict[str, Dict[str, Any]] = {}
    for lang, lang_files in buckets.items():
        lang_files = lang_files[:200]
        if lang == "Python":
            per_language[lang] = _analyze_python(lang_files)
        elif lang in ("JavaScript", "TypeScript") and _TS_AVAILABLE:
            per_language[lang] = _analyze_js(lang_files, lang)
        elif lang in _HEURISTIC_CONFIG:
            per_language[lang] = _analyze_heuristic(lang_files, lang)
        else:
            per_language[lang] = _analyze_file_stats(lang_files)

    primary = max(per_language.items(), key=lambda x: len(buckets[x[0]]))[0]
    primary_data = per_language[primary]

    all_complex: List[Dict[str, Any]] = []
    for lang, data in per_language.items():
        for f in data.get("most_complex_files", []):
            f = dict(f)
            f["language"] = lang
            all_complex.append(f)
    all_complex.sort(key=lambda x: x.get("complexity_score", 0), reverse=True)

    return {
        "per_language": per_language,
        "primary_language": primary,
        "total_functions": sum(d.get("total_functions", 0) for d in per_language.values()),
        "total_classes": sum(d.get("total_classes", 0) for d in per_language.values()),
        "total_lines": sum(d.get("total_lines", 0) for d in per_language.values()),
        "avg_complexity_score": primary_data.get("avg_complexity_score", 0),
        "most_complex_files": all_complex[:10],
        "confidence": primary_data.get("confidence", "file_stats"),
    }


def _empty_result() -> Dict[str, Any]:
    return {
        "per_language": {}, "primary_language": None,
        "total_functions": 0, "total_classes": 0, "total_lines": 0,
        "avg_complexity_score": 0, "most_complex_files": [],
        "confidence": "file_stats",
    }


def _skip(file_path: str) -> bool:
    lower = file_path.lower().replace("\\", "/")
    return any(s in lower for s in _SKIP_PATH_SUBSTRINGS)


# ── Python ──────────────────────────────────────────────────────────
def _analyze_python(files: List[str]) -> Dict[str, Any]:
    stats: List[Dict[str, Any]] = []
    total_f = total_c = total_i = total_l = 0

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(_py_one, fp) for fp in files]
        for fut in as_completed(futures):
            try:
                s = fut.result(timeout=20)
            except Exception:
                s = None
            if not s:
                continue
            stats.append(s)
            total_f += s["functions"]
            total_c += s["classes"]
            total_i += s["imports"]
            total_l += s["lines"]

    for s in stats:
        s["complexity_score"] = s.pop("_total_complexity")
    stats.sort(key=lambda x: x["complexity_score"], reverse=True)

    return {
        "files": len(stats),
        "total_functions": total_f,
        "total_classes": total_c,
        "total_imports": total_i,
        "total_lines": total_l,
        "avg_complexity_score": _avg(stats),
        "most_complex_files": stats[:10],
        "confidence": "ast",
    }


def _py_one(fp: str) -> Optional[Dict[str, Any]]:
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            src = f.read()
        tree = ast.parse(src)
    except Exception:
        return None

    functions = classes = imports = total_cx = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions += 1
            total_cx += _py_fn_cx(node)
        elif isinstance(node, ast.ClassDef):
            classes += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports += 1

    return {
        "file": fp, "functions": functions, "classes": classes,
        "imports": imports, "lines": src.count("\n") + 1,
        "_total_complexity": total_cx,
    }


def _py_fn_cx(fn: ast.AST) -> int:
    cx = 1
    for child in ast.walk(fn):
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While,
                              ast.ExceptHandler, ast.With, ast.AsyncWith,
                              ast.Match)):
            cx += 1
        elif isinstance(child, ast.BoolOp):
            cx += len(child.values) - 1
        elif isinstance(child, ast.IfExp):
            cx += 1
    return cx


# ── JavaScript / TypeScript (tree-sitter) ───────────────────────────
_JS_FN_NODES = {
    "function_declaration", "function_expression", "arrow_function",
    "method_definition", "generator_function", "generator_function_declaration",
}
_JS_DECISION_NODES = {
    "if_statement", "for_statement", "for_in_statement", "while_statement",
    "do_statement", "switch_case", "catch_clause", "ternary_expression",
}


def _analyze_js(files: List[str], lang: str) -> Dict[str, Any]:
    stats: List[Dict[str, Any]] = []
    total_f = total_c = total_i = total_l = 0

    for fp in files:
        s = _js_one(fp, lang)
        if not s:
            continue
        stats.append(s)
        total_f += s["functions"]
        total_c += s["classes"]
        total_i += s["imports"]
        total_l += s["lines"]

    for s in stats:
        s["complexity_score"] = s.pop("_total_complexity")
    stats.sort(key=lambda x: x["complexity_score"], reverse=True)

    return {
        "files": len(stats),
        "total_functions": total_f,
        "total_classes": total_c,
        "total_imports": total_i,
        "total_lines": total_l,
        "avg_complexity_score": _avg(stats),
        "most_complex_files": stats[:10],
        "confidence": "parser",
    }


def _js_one(fp: str, lang: str) -> Optional[Dict[str, Any]]:
    try:
        language = _pick_js_lang(fp, lang)
        if language is None:
            return None
        parser = Parser(language)
        with open(fp, "rb") as f:
            src = f.read()
        tree = parser.parse(src)
    except Exception:
        return None

    functions = classes = imports = total_cx = 0

    def walk(node):
        nonlocal functions, classes, imports, total_cx
        t = node.type
        if t in ("import_statement", "import_declaration"):
            imports += 1
        elif t in ("class_declaration", "class_expression"):
            classes += 1
        if t in _JS_FN_NODES:
            functions += 1
            total_cx += _js_fn_cx(node)
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return {
        "file": fp, "functions": functions, "classes": classes,
        "imports": imports, "lines": src.count(b"\n") + 1,
        "_total_complexity": total_cx,
    }


def _pick_js_lang(fp: str, lang: str):
    ext = Path(fp).suffix.lower()
    if ext == ".tsx" and _TSX_LANGUAGE is not None:
        return _TSX_LANGUAGE
    if ext in (".ts", ".mts", ".cts") and _TS_LANGUAGE is not None:
        return _TS_LANGUAGE
    return _JS_LANGUAGE


def _js_fn_cx(fn_node) -> int:
    cx = 1
    stack = [fn_node]
    while stack:
        n = stack.pop()
        if n.type in _JS_DECISION_NODES:
            cx += 1
        elif n.type == "binary_expression":
            for child in n.children:
                if child.type == "operator":
                    text = child.text.decode("utf-8", errors="ignore")
                    if text in ("&&", "||", "??"):
                        cx += 1
                        break
        stack.extend(n.children)
    return cx


# ── Heuristic languages ─────────────────────────────────────────────
def _analyze_heuristic(files: List[str], lang: str) -> Dict[str, Any]:
    cfg = _HEURISTIC_CONFIG[lang]
    fn_re = re.compile(cfg["function"], re.MULTILINE)
    cls_re = re.compile(cfg["class"], re.MULTILINE) if cfg.get("class") else None
    dec_res = [re.compile(p) for p in cfg["decision"]]

    stats: List[Dict[str, Any]] = []
    total_f = total_c = total_l = 0

    for fp in files:
        s = _heuristic_one(fp, fn_re, cls_re, dec_res)
        if not s:
            continue
        stats.append(s)
        total_f += s["functions"]
        total_c += s["classes"]
        total_l += s["lines"]

    for s in stats:
        s["complexity_score"] = s.pop("_total_complexity")
    stats.sort(key=lambda x: x["complexity_score"], reverse=True)

    return {
        "files": len(stats),
        "total_functions": total_f,
        "total_classes": total_c,
        "total_imports": 0,
        "total_lines": total_l,
        "avg_complexity_score": _avg(stats),
        "most_complex_files": stats[:10],
        "confidence": "heuristic",
    }


def _heuristic_one(fp, fn_re, cls_re, dec_res) -> Optional[Dict[str, Any]]:
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            src = f.read()
    except Exception:
        return None
    lines = src.split("\n")
    if lines and sum(len(l) for l in lines[:200]) / max(len(lines[:200]), 1) > 200:
        return None

    functions = len(fn_re.findall(src))
    classes = len(cls_re.findall(src)) if cls_re else 0
    decisions = sum(len(r.findall(src)) for r in dec_res)

    return {
        "file": fp, "functions": functions, "classes": classes,
        "imports": 0, "lines": len(lines),
        "_total_complexity": decisions + functions,
    }


# ── Fallback: file-level stats only ────────────────────────────────
def _analyze_file_stats(files: List[str]) -> Dict[str, Any]:
    stats: List[Dict[str, Any]] = []
    total_l = 0
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                src = f.read()
        except Exception:
            continue
        lines = src.count("\n") + 1
        total_l += lines
        stats.append({
            "file": fp, "functions": 0, "classes": 0, "imports": 0,
            "lines": lines, "complexity_score": 0,
        })
    stats.sort(key=lambda x: x["lines"], reverse=True)
    return {
        "files": len(stats), "total_functions": 0, "total_classes": 0,
        "total_imports": 0, "total_lines": total_l,
        "avg_complexity_score": 0, "most_complex_files": stats[:10],
        "confidence": "file_stats",
    }


def _avg(stats: List[Dict[str, Any]]) -> float:
    if not stats:
        return 0.0
    return round(sum(s["complexity_score"] for s in stats) / len(stats), 2)