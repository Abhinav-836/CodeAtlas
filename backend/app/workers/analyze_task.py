"""
Analysis task implementation for code repositories.
"""
import ast
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import traceback

from app.services.ingestion.file_scanner import scan_files
from app.services.analysis.metrics import code_metrics
from app.services.analysis.architecture import infer_architecture
from app.services.security.secrets_scanner import scan_secrets, summarize_findings as summarize_secrets
from app.services.security.vuln_patterns import scan_vulnerabilities, summarize_vulnerabilities
from app.utils.ignore_matcher import IgnoreMatcher


def analyze_repo(repo_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze a code repository with comprehensive metrics.
    
    Args:
        repo_path: Path to repository
        options: Analysis options dictionary
        
    Returns:
        Analysis results dictionary
    """
    start_time = time.time()
    analysis_id = f"analysis_{int(start_time)}_{os.urandom(4).hex()}"
    
    try:
        print(f"🔍 Starting analysis {analysis_id} of: {repo_path}")
        
        # Validate path
        path_obj = Path(repo_path).resolve()
        if not path_obj.exists():
            return {
                "error": f"Path does not exist: {repo_path}",
                "status": "failed",
                "analysis_id": analysis_id,
                "timestamp": datetime.now().isoformat()
            }
        
        if not path_obj.is_dir():
            return {
                "error": f"Path is not a directory: {repo_path}",
                "status": "failed",
                "analysis_id": analysis_id,
                "timestamp": datetime.now().isoformat()
            }
        
        # Initialize result with metadata
        result = {
            "analysis_id": analysis_id,
            "path": str(path_obj),
            "repo_name": path_obj.name,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "options": options or {},
        }
        
        # Scan files with ignore rules
        print(f"📁 Scanning files in: {repo_path}")
        all_files = _scan_all_files(repo_path)
        
        if not all_files:
            return {
                "error": "No files found to analyze",
                "status": "completed",
                "analysis_id": analysis_id,
                "path": repo_path,
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"📊 Found {len(all_files)} files to analyze")
        
        # Basic file info
        result["summary"] = {
            "total_files": len(all_files),
            "files_analyzed": len(all_files),
            "scanned_at": datetime.now().isoformat(),
            "total_size_bytes": sum(Path(f).stat().st_size for f in all_files if Path(f).exists()),
        }
        
        # Calculate metrics
        print("📈 Calculating metrics...")
        result["metrics"] = code_metrics(all_files)
        
        # Analyze architecture
        print("🏗️  Analyzing architecture...")
        result["architecture"] = infer_architecture(all_files)
        
        # Security scanning
        print("🔒 Scanning for secrets...")
        secrets_found = scan_secrets(all_files)
        result["security"] = {
            "secrets_found": len(secrets_found),
            "secrets": secrets_found[:20],  # Limit for response size
        }
        
        # Add secrets summary
        secrets_summary = summarize_secrets(secrets_found)
        result["security"].update(secrets_summary)
        
        # Vulnerability scanning
        print("⚠️  Scanning for vulnerabilities...")
        vulns_found = scan_vulnerabilities(all_files)
        result["security"]["vulnerabilities_found"] = len(vulns_found)
        result["security"]["vulnerabilities"] = vulns_found[:20]
        
        # Add vulnerabilities summary
        vulns_summary = summarize_vulnerabilities(vulns_found)
        result["security"].update(vulns_summary)
        
        # Overall security risk - FIXED TYPE ERROR HERE
        security_risk = "none"
        risk_score = 0
        
        # Handle critical_findings properly (it might be a list or an int)
        critical_findings = result["security"].get("critical_findings", 0)
        if isinstance(critical_findings, list):
            critical_count = len(critical_findings)
        else:
            critical_count = critical_findings if isinstance(critical_findings, (int, float)) else 0
        
        if critical_count > 0:
            security_risk = "critical"
            risk_score = 90
        elif result["security"].get("vulnerabilities_found", 0) > 0:
            security_risk = "high"
            risk_score = 70
        elif result["security"].get("secrets_found", 0) > 5:
            security_risk = "medium"
            risk_score = 50
        elif result["security"].get("secrets_found", 0) > 0:
            security_risk = "low"
            risk_score = 30
            
        result["security"]["overall_risk"] = security_risk
        result["security"]["risk_score"] = risk_score
        
        # Language-specific analysis
        print("🌐 Analyzing language-specific features...")
        result["languages"] = _analyze_languages(all_files)
        
        # Python-specific analysis
        python_files = [f for f in all_files if f.lower().endswith('.py')]
        if python_files:
            print(f"🐍 Analyzing {len(python_files)} Python files...")
            result["python_analysis"] = _analyze_python_files(python_files)
        
        # JavaScript-specific analysis
        js_files = [f for f in all_files if f.lower().endswith(('.js', '.jsx', '.ts', '.tsx'))]
        if js_files:
            print(f"📜 Analyzing {len(js_files)} JavaScript/TypeScript files...")
            result["javascript_analysis"] = _analyze_javascript_files(js_files)
        
        # Calculate overall risk score
        result["overall_risk_score"] = _calculate_overall_risk_score(result)
        result["overall_risk_level"] = _get_risk_level(result["overall_risk_score"])
        
        # Performance metrics
        end_time = time.time()
        result["performance"] = {
            "analysis_duration_seconds": round(end_time - start_time, 2),
            "files_per_second": round(len(all_files) / (end_time - start_time), 2) if (end_time - start_time) > 0 else 0,
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
        }
        
        # Add recommendations
        result["recommendations"] = _generate_recommendations(result)
        
        print(f"✅ Analysis {analysis_id} completed in {result['performance']['analysis_duration_seconds']}s")
        return result
        
    except Exception as e:
        print(f"❌ Analysis {analysis_id} failed: {str(e)}")
        print(traceback.format_exc())
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "path": repo_path,
            "status": "failed",
            "analysis_id": analysis_id,
            "timestamp": datetime.now().isoformat(),
        }


def _scan_all_files(repo_path: str) -> List[str]:
    """Scan all files in repository, applying ignore rules."""
    all_files = []
    
    print(f"🔍 Scanning directory: {repo_path}")
    
    if not os.path.exists(repo_path):
        print(f"❌ Directory does not exist: {repo_path}")
        return all_files
    
    # Use os.walk to go through ALL subdirectories recursively
    for root, dirs, files in os.walk(repo_path):
        # Skip common ignore patterns but still scan subdirectories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
            '__pycache__', 'node_modules', '.git', 'venv', '.venv', 'env'
        }]
        
        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue
            
            file_path = os.path.join(root, file)
            all_files.append(file_path)
            # Uncomment for debugging
            # print(f"   📄 Found: {file_path}")
    
    print(f"✅ Total files found: {len(all_files)}")
    return all_files


def _analyze_python_files(python_files: List[str]) -> Dict[str, Any]:
    """Analyze Python files for complexity and structure."""
    result = {
        "python_files_count": len(python_files),
        "total_functions": 0,
        "total_classes": 0,
        "total_imports": 0,
        "total_lines": 0,
        "most_complex_files": [],
        "import_analysis": {},
        "file_stats": [],
    }
    
    file_complexities = []
    imports_counter = {}
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for file_path in python_files[:100]:  # Limit for performance
            futures.append(executor.submit(_analyze_single_python_file, file_path))
        
        for future in as_completed(futures):
            try:
                file_result = future.result(timeout=30)
                if file_result:
                    result["total_functions"] += file_result["functions"]
                    result["total_classes"] += file_result["classes"]
                    result["total_imports"] += file_result["imports"]
                    result["total_lines"] += file_result["lines"]
                    
                    # Track imports
                    for imp in file_result["import_list"]:
                        imports_counter[imp] = imports_counter.get(imp, 0) + 1
                    
                    if file_result["complexity_score"] > 0:
                        file_complexities.append(file_result)
                    
                    result["file_stats"].append({
                        "file": file_result["file"],
                        "functions": file_result["functions"],
                        "classes": file_result["classes"],
                        "imports": file_result["imports"],
                        "lines": file_result["lines"],
                        "complexity_score": file_result["complexity_score"],
                    })
            except Exception as e:
                print(f"Warning: Failed to analyze Python file: {e}")
                continue
    
    if file_complexities:
        # Calculate average complexity
        total_complexity = sum(fc["complexity_score"] for fc in file_complexities)
        result["avg_complexity_score"] = round(total_complexity / len(file_complexities), 2)
        
        # Get most complex files
        file_complexities.sort(key=lambda x: x["complexity_score"], reverse=True)
        result["most_complex_files"] = file_complexities[:10]
    
    # Sort imports by frequency
    result["import_analysis"] = {
        "most_common_imports": sorted(imports_counter.items(), key=lambda x: x[1], reverse=True)[:20],
        "unique_imports_count": len(imports_counter),
    }
    
    # Calculate averages
    if python_files:
        result["avg_functions_per_file"] = round(result["total_functions"] / len(python_files), 2)
        result["avg_classes_per_file"] = round(result["total_classes"] / len(python_files), 2)
        result["avg_lines_per_file"] = round(result["total_lines"] / len(python_files), 2)
    
    return result


def _analyze_single_python_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Analyze a single Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.count('\n') + 1
        tree = ast.parse(content)
        
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        
        # Extract import names
        import_list = []
        for node in imports:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_list.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    import_list.append(node.module)
        
        # Simple complexity score based on structure
        complexity = (len(functions) * 2) + (len(classes) * 3) + (len(imports) * 1)
        
        # Check for common patterns
        decorators = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.decorator_list)
        comprehensions = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)))
        lambdas = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Lambda))
        
        complexity += decorators + comprehensions + lambdas
        
        return {
            "file": file_path,
            "functions": len(functions),
            "classes": len(classes),
            "imports": len(imports),
            "import_list": import_list,
            "lines": lines,
            "complexity_score": complexity,
            "decorators": decorators,
            "comprehensions": comprehensions,
            "lambdas": lambdas,
        }
        
    except (SyntaxError, UnicodeDecodeError, IOError, RecursionError) as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        return None


def _analyze_javascript_files(js_files: List[str]) -> Dict[str, Any]:
    """Analyze JavaScript/TypeScript files."""
    result = {
        "javascript_files_count": len(js_files),
        "total_size_bytes": 0,
        "file_extensions": {},
    }
    
    extension_counter = {}
    for file_path in js_files:
        try:
            # Basic file analysis
            file_stat = Path(file_path).stat()
            result["total_size_bytes"] += file_stat.st_size
            
            # Count by extension
            ext = Path(file_path).suffix.lower()
            extension_counter[ext] = extension_counter.get(ext, 0) + 1
            
        except OSError:
            continue
    
    result["file_extensions"] = extension_counter
    
    return result


def _analyze_languages(all_files: List[str]) -> Dict[str, Any]:
    """Analyze programming languages used in the codebase."""
    language_extensions = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.jsx': 'JavaScript',
        '.ts': 'TypeScript',
        '.tsx': 'TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.cs': 'C#',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.sass': 'SASS',
        '.json': 'JSON',
        '.yml': 'YAML',
        '.yaml': 'YAML',
        '.xml': 'XML',
        '.md': 'Markdown',
        '.txt': 'Text',
        '.sql': 'SQL',
        '.sh': 'Shell',
        '.dockerfile': 'Docker',
    }
    
    language_stats = {}
    total_files = len(all_files)
    
    for file_path in all_files:
        ext = Path(file_path).suffix.lower()
        if ext in language_extensions:
            language = language_extensions[ext]
            language_stats[language] = language_stats.get(language, 0) + 1
    
    # Calculate percentages
    language_stats_with_pct = {}
    for lang, count in language_stats.items():
        percentage = (count / total_files) * 100 if total_files > 0 else 0
        language_stats_with_pct[lang] = {
            "count": count,
            "percentage": round(percentage, 2)
        }
    
    # Sort by count
    sorted_languages = dict(sorted(
        language_stats_with_pct.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    ))
    
    return {
        "detected_languages": sorted_languages,
        "primary_language": list(sorted_languages.keys())[0] if sorted_languages else "Unknown",
        "language_count": len(sorted_languages),
    }


def _calculate_overall_risk_score(result: Dict[str, Any]) -> int:
    """Calculate overall risk score based on various factors."""
    score = 0
    
    # Security factors (0-50 points)
    security = result.get("security", {})
    
    # Handle critical_findings properly
    critical_findings = security.get("critical_findings", 0)
    if isinstance(critical_findings, list):
        critical_count = len(critical_findings)
    else:
        critical_count = critical_findings if isinstance(critical_findings, (int, float)) else 0
    
    score += min(security.get("secrets_found", 0) * 2, 20)
    score += min(security.get("vulnerabilities_found", 0) * 5, 20)
    score += min(critical_count * 10, 10)
    
    # Complexity factors (0-30 points)
    python_analysis = result.get("python_analysis", {})
    if python_analysis:
        avg_complexity = python_analysis.get("avg_complexity_score", 0)
        if avg_complexity > 50:
            score += 20
        elif avg_complexity > 20:
            score += 10
        elif avg_complexity > 10:
            score += 5
    
    # Size factors (0-20 points)
    summary = result.get("summary", {})
    file_count = summary.get("total_files", 0)
    if file_count > 1000:
        score += 15
    elif file_count > 500:
        score += 10
    elif file_count > 100:
        score += 5
    
    return min(score, 100)


def _get_risk_level(score: int) -> str:
    """Convert risk score to risk level."""
    if score >= 80:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 40:
        return "medium"
    elif score >= 20:
        return "low"
    else:
        return "none"


def _generate_recommendations(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate recommendations based on analysis."""
    recommendations = []
    security = result.get("security", {})
    python_analysis = result.get("python_analysis", {})
    
    # Handle critical_findings properly
    critical_findings = security.get("critical_findings", 0)
    if isinstance(critical_findings, list):
        critical_count = len(critical_findings)
    else:
        critical_count = critical_findings if isinstance(critical_findings, (int, float)) else 0
    
    # Security recommendations
    if security.get("secrets_found", 0) > 0:
        recommendations.append({
            "category": "security",
            "priority": "high",
            "title": "Remove hardcoded secrets",
            "description": f"Found {security['secrets_found']} potential secrets in the codebase.",
            "action": "Review and remove or rotate exposed API keys, passwords, and tokens.",
        })
    
    if security.get("vulnerabilities_found", 0) > 0:
        recommendations.append({
            "category": "security",
            "priority": "high",
            "title": "Fix security vulnerabilities",
            "description": f"Found {security['vulnerabilities_found']} potential vulnerabilities.",
            "action": "Review and fix the identified security issues.",
        })
    
    if critical_count > 0:
        recommendations.append({
            "category": "security",
            "priority": "critical",
            "title": "Address critical security findings",
            "description": f"Found {critical_count} critical security issues.",
            "action": "Immediately review and fix critical security findings.",
        })
    
    # Complexity recommendations
    if python_analysis and python_analysis.get("avg_complexity_score", 0) > 20:
        recommendations.append({
            "category": "maintainability",
            "priority": "medium",
            "title": "Reduce code complexity",
            "description": f"High average complexity score: {python_analysis['avg_complexity_score']}",
            "action": "Consider refactoring complex functions and classes.",
        })
    
    # Size recommendations
    file_count = result.get("summary", {}).get("total_files", 0)
    if file_count > 1000:
        recommendations.append({
            "category": "architecture",
            "priority": "low",
            "title": "Consider modularization",
            "description": f"Large codebase with {file_count} files.",
            "action": "Consider splitting into smaller, focused modules or microservices.",
        })
    
    return recommendations