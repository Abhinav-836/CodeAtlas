"""
Code metrics calculation.
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import math


def code_metrics(files: List[str]) -> Dict[str, Any]:
    """
    Calculate comprehensive code metrics.
    
    Args:
        files: List of file paths
        
    Returns:
        Dictionary of metrics
    """
    if not files:
        return {
            "file_count": 0,
            "total_lines": 0,
            "total_size_kb": 0,
            "risk": "none",
            "risk_score": 0,
            "languages": [],
            "file_types": {},
        }
    
    # Basic metrics
    total_lines = 0
    total_size = 0
    file_types = {}
    languages = set()
    
    # Complexity metrics
    large_files = 0
    complex_files = []
    
    for file_path in files:
        try:
            # File size
            size = os.path.getsize(file_path)
            total_size += size
            
            # Count lines (for text files)
            ext = Path(file_path).suffix.lower()
            if ext in {'.py', '.js', '.ts', '.java', '.go', '.rb', '.php', 
                       '.cpp', '.c', '.h', '.cs', '.swift', '.kt', '.rs',
                       '.html', '.css', '.xml', '.json', '.yml', '.yaml',
                       '.md', '.txt', '.rst'}:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = sum(1 for _ in f)
                    total_lines += lines
                    
                    # Check for large files
                    if lines > 1000:
                        large_files += 1
                        complex_files.append({
                            'file': file_path,
                            'lines': lines,
                            'size_kb': size / 1024
                        })
            
            # File type categorization
            file_type = _categorize_file_type(file_path)
            file_types[file_type] = file_types.get(file_type, 0) + 1
            
            # Language detection
            language = _detect_language(file_path)
            if language:
                languages.add(language)
                
        except (IOError, UnicodeDecodeError, PermissionError):
            continue
    
    # Calculate derived metrics
    metrics = {
        "file_count": len(files),
        "total_lines": total_lines,
        "total_size_kb": round(total_size / 1024, 2),
        "avg_file_size_kb": round(total_size / len(files) / 1024, 2) if files else 0,
        "avg_lines_per_file": round(total_lines / len(files), 2) if files else 0,
        "large_files_count": large_files,
        "large_files_percentage": round(large_files / len(files) * 100, 2) if files else 0,
        "file_types": file_types,
        "languages": sorted(list(languages)),
    }
    
    # Calculate risk
    risk_level, risk_score = _calculate_risk_score(metrics, complex_files)
    metrics["risk"] = risk_level
    metrics["risk_score"] = risk_score
    
    # Add complexity metrics if we have Python files
    python_files = [f for f in files if f.endswith('.py')]
    if python_files:
        py_metrics = _analyze_python_complexity(python_files)
        metrics["python_metrics"] = py_metrics
    
    return metrics


def _categorize_file_type(file_path: str) -> str:
    """Categorize file by type."""
    ext = Path(file_path).suffix.lower()
    
    mapping = {
        # Source code
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.rs': 'rust',
        
        # Web
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        
        # Data
        '.json': 'json',
        '.xml': 'xml',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.toml': 'toml',
        '.csv': 'csv',
        
        # Config
        '.env': 'env',
        '.ini': 'ini',
        '.cfg': 'config',
        '.conf': 'config',
        '.properties': 'properties',
        
        # Documentation
        '.md': 'markdown',
        '.rst': 'rst',
        '.txt': 'text',
        
        # Images
        '.png': 'image',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.gif': 'image',
        '.svg': 'image',
        '.ico': 'image',
        
        # Binary
        '.pdf': 'pdf',
        '.zip': 'archive',
        '.tar': 'archive',
        '.gz': 'archive',
    }
    
    return mapping.get(ext, 'other')


def _detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    ext = Path(file_path).suffix.lower()
    
    language_map = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.java': 'Java',
        '.go': 'Go',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.cpp': 'C++',
        '.c': 'C',
        '.cs': 'C#',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.rs': 'Rust',
        '.scala': 'Scala',
        '.hs': 'Haskell',
        '.lua': 'Lua',
        '.pl': 'Perl',
        '.r': 'R',
        '.m': 'Objective-C',
        '.mm': 'Objective-C++',
    }
    
    return language_map.get(ext, '')


def _calculate_risk_score(metrics: Dict[str, Any], complex_files: List[Dict]) -> Tuple[str, int]:
    """Calculate risk score based on metrics."""
    risk_score = 0
    
    # 1. File count risk (max 20 points)
    file_count = metrics["file_count"]
    if file_count > 1000:
        risk_score += 20
    elif file_count > 500:
        risk_score += 15
    elif file_count > 200:
        risk_score += 10
    elif file_count > 100:
        risk_score += 5
    
    # 2. Large files risk (max 25 points)
    large_files_pct = metrics["large_files_percentage"]
    if large_files_pct > 20:
        risk_score += 25
    elif large_files_pct > 10:
        risk_score += 15
    elif large_files_pct > 5:
        risk_score += 10
    elif large_files_pct > 0:
        risk_score += 5
    
    # 3. Language diversity risk (max 15 points)
    language_count = len(metrics["languages"])
    if language_count > 5:
        risk_score += 15
    elif language_count > 3:
        risk_score += 10
    elif language_count > 1:
        risk_score += 5
    
    # 4. File type concentration risk (max 20 points)
    file_types = metrics.get("file_types", {})
    if file_types:
        main_type_count = max(file_types.values())
        concentration = main_type_count / file_count
        
        if concentration > 0.8:  # Too concentrated
            risk_score += 20
        elif concentration > 0.6:
            risk_score += 15
        elif concentration > 0.4:
            risk_score += 10
    
    # 5. Complexity risk from complex files (max 20 points)
    if complex_files:
        avg_lines = sum(f['lines'] for f in complex_files) / len(complex_files)
        if avg_lines > 2000:
            risk_score += 20
        elif avg_lines > 1000:
            risk_score += 15
        elif avg_lines > 500:
            risk_score += 10
    
    # Cap score at 100
    risk_score = min(risk_score, 100)
    
    # Determine risk level
    if risk_score >= 80:
        risk_level = "critical"
    elif risk_score >= 60:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "medium"
    elif risk_score >= 20:
        risk_level = "low"
    else:
        risk_level = "none"
    
    return risk_level, risk_score


def _analyze_python_complexity(python_files: List[str]) -> Dict[str, Any]:
    """Analyze Python-specific complexity metrics."""
    if not python_files:
        return {}
    
    import ast
    from typing import Dict, Any
    
    total_functions = 0
    total_classes = 0
    total_imports = 0
    total_decorators = 0
    file_complexities = []
    
    for file_path in python_files[:50]:  # Limit analysis for performance
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
                # Count nodes
                functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
                decorators = []
                
                # Count decorators
                for node in ast.walk(tree):
                    if hasattr(node, 'decorator_list'):
                        decorators.extend(node.decorator_list)
                
                # Calculate file complexity (simplified)
                file_complexity = len(functions) + len(classes) * 2
                
                file_complexities.append({
                    'file': file_path,
                    'functions': len(functions),
                    'classes': len(classes),
                    'imports': len(imports),
                    'decorators': len(decorators),
                    'complexity_score': file_complexity,
                })
                
                total_functions += len(functions)
                total_classes += len(classes)
                total_imports += len(imports)
                total_decorators += len(decorators)
                
        except (SyntaxError, UnicodeDecodeError, IOError):
            continue
    
    if not file_complexities:
        return {}
    
    # Calculate averages
    avg_complexity = sum(fc['complexity_score'] for fc in file_complexities) / len(file_complexities)
    
    # Find most complex files
    file_complexities.sort(key=lambda x: x['complexity_score'], reverse=True)
    most_complex = file_complexities[:5]
    
    return {
        'total_python_files': len(python_files),
        'analyzed_python_files': len(file_complexities),
        'total_functions': total_functions,
        'total_classes': total_classes,
        'total_imports': total_imports,
        'total_decorators': total_decorators,
        'avg_complexity_score': round(avg_complexity, 2),
        'avg_functions_per_file': round(total_functions / len(file_complexities), 2) if file_complexities else 0,
        'avg_classes_per_file': round(total_classes / len(file_complexities), 2) if file_complexities else 0,
        'most_complex_files': most_complex,
    }