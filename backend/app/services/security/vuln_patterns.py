"""
Vulnerability pattern scanning.
"""
import re
import ast
from pathlib import Path
from typing import List, Dict, Any


INSECURE_PATTERNS = [
    # Dangerous functions
    (r'\beval\s*\(', 'eval', 'high'),
    (r'\bexec\s*\(', 'exec', 'high'),
    (r'\bcompile\s*\(', 'compile', 'medium'),
    (r'\b__import__\s*\(', '__import__', 'high'),
    
    # Pickle vulnerabilities
    (r'pickle\.loads\s*\(', 'pickle.loads', 'high'),
    (r'pickle\.load\s*\(', 'pickle.load', 'high'),
    (r'cPickle\.', 'cPickle', 'high'),
    
    # Command injection
    (r'os\.system\s*\(', 'os.system', 'high'),
    (r'subprocess\.Popen\s*\(', 'subprocess.Popen', 'high'),
    (r'subprocess\.call\s*\(', 'subprocess.call', 'high'),
    (r'subprocess\.run\s*\(', 'subprocess.run', 'high'),
    
    # SQL injection patterns
    (r'cursor\.execute\s*\(\s*f?"[^"]*\%s', 'SQL string formatting', 'high'),
    (r'cursor\.execute\s*\(\s*"[^"]*"\s*\%\s*\(', 'SQL % formatting', 'high'),
    (r'\.format\s*\(\s*[^)]*\)\s*\)\s*\)?', 'String formatting in SQL', 'medium'),
    
    # Hardcoded secrets in code (partial)
    (r'["\'](pk|sk)_[a-zA-Z0-9_\-]{20,}["\']', 'Stripe key', 'critical'),
    (r'["\']AKIA[0-9A-Z]{16}["\']', 'AWS key ID', 'critical'),
    (r'["\'][0-9a-zA-Z/+]{40}["\']', 'AWS secret key', 'critical'),
    
    # Insecure randomness
    (r'random\.randint\s*\(', 'random.randint', 'low'),
    (r'random\.choice\s*\(', 'random.choice', 'low'),
    
    # SSL/TLS issues
    (r'verify\s*=\s*False', 'SSL verify=False', 'high'),
    (r'requests\.get.*verify\s*=\s*False', 'Requests SSL verify=False', 'high'),
]


def scan_vulnerabilities(files: List[str]) -> List[Dict[str, Any]]:
    """
    Scan files for vulnerability patterns.
    
    Args:
        files: List of file paths
        
    Returns:
        List of vulnerability findings
    """
    findings = []
    
    for file_path in files:
        if not _should_scan_file(file_path):
            continue
            
        try:
            file_findings = _scan_file_for_vulns(file_path)
            findings.extend(file_findings)
        except Exception:
            continue
    
    return findings


def _should_scan_file(file_path: str) -> bool:
    """Check if file should be scanned for vulnerabilities."""
    ext = Path(file_path).suffix.lower()
    
    # Only scan source code and config files
    scannable_extensions = {
        '.py', '.js', '.ts', '.java', '.go', '.rb', '.php',
        '.cpp', '.c', '.h', '.cs', '.swift', '.kt',
        '.yml', '.yaml', '.json', '.xml', '.ini', '.cfg', '.conf',
    }
    
    return ext in scannable_extensions


def _scan_file_for_vulns(file_path: str) -> List[Dict[str, Any]]:
    """Scan a file for vulnerability patterns."""
    findings = []
    ext = Path(file_path).suffix.lower()
    
    if ext == '.py':
        # Use AST for Python files
        findings.extend(_scan_python_with_ast(file_path))
    
    # Always do string pattern matching
    findings.extend(_scan_with_patterns(file_path))
    
    return findings


def _scan_python_with_ast(file_path: str) -> List[Dict[str, Any]]:
    """Scan Python file with AST for better accuracy."""
    findings = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
            
        for node in ast.walk(tree):
            # Check for eval/exec calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    
                    if func_name in ['eval', 'exec', 'compile']:
                        findings.append({
                            'file': file_path,
                            'line': node.lineno,
                            'pattern': func_name,
                            'type': 'dangerous_function',
                            'severity': 'high',
                            'context': _get_ast_context(node, content),
                        })
                
                # Check for module.function calls
                elif isinstance(node.func, ast.Attribute):
                    module_name = _get_full_attribute_name(node.func)
                    
                    dangerous_calls = {
                        'pickle.loads': 'high',
                        'pickle.load': 'high',
                        'os.system': 'high',
                        'subprocess.Popen': 'high',
                        'subprocess.call': 'high',
                        'subprocess.run': 'high',
                        'random.randint': 'low',
                        'random.choice': 'low',
                    }
                    
                    for dangerous_call, severity in dangerous_calls.items():
                        if module_name == dangerous_call:
                            findings.append({
                                'file': file_path,
                                'line': node.lineno,
                                'pattern': dangerous_call,
                                'type': 'dangerous_function',
                                'severity': severity,
                                'context': _get_ast_context(node, content),
                            })
            
            # Check for string formatting in potentially dangerous contexts
            if isinstance(node, ast.Call):
                # This is simplified - real implementation would track variables
                pass
    
    except (SyntaxError, UnicodeDecodeError, IOError):
        pass
    
    return findings


def _scan_with_patterns(file_path: str) -> List[Dict[str, Any]]:
    """Scan file with regex patterns."""
    findings = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for pattern, vuln_type, severity in INSECURE_PATTERNS:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    
                    for match in matches:
                        # Skip if in comment (for supported languages)
                        if _is_in_comment(line, file_path):
                            continue
                            
                        findings.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': vuln_type,
                            'type': 'pattern_match',
                            'severity': severity,
                            'context': line.strip()[:200],
                            'match': match.group(0),
                        })
    
    except Exception:
        pass
    
    return findings


def _get_full_attribute_name(node: ast.Attribute) -> str:
    """Get full attribute name like 'module.function'."""
    parts = []
    
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    
    if isinstance(node, ast.Name):
        parts.append(node.id)
    
    return '.'.join(reversed(parts))


def _get_ast_context(node: ast.AST, content: str) -> str:
    """Get context line from AST node."""
    try:
        lines = content.split('\n')
        if node.lineno - 1 < len(lines):
            return lines[node.lineno - 1].strip()[:200]
    except (AttributeError, IndexError):
        pass
    
    return ''


def _is_in_comment(line: str, file_path: str) -> bool:
    """Check if text is inside a comment."""
    ext = Path(file_path).suffix.lower()
    
    # Remove comments for checking
    if ext == '.py':
        # Python comments
        comment_pos = line.find('#')
        if comment_pos != -1:
            line = line[:comment_pos]
    
    elif ext in ['.js', '.ts', '.java', '.cpp', '.c', '.cs']:
        # C-style comments
        line = re.sub(r'//.*', '', line)
        line = re.sub(r'/\*.*?\*/', '', line)
    
    elif ext in ['.rb']:
        # Ruby comments
        comment_pos = line.find('#')
        if comment_pos != -1:
            line = line[:comment_pos]
    
    # Check if pattern still exists after removing comments
    return line.strip() == ''


def summarize_vulnerabilities(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize vulnerability findings."""
    if not findings:
        return {
            'total_findings': 0,
            'by_severity': {},
            'by_type': {},
            'critical_findings': [],
        }
    
    by_severity = {}
    by_type = {}
    
    for finding in findings:
        severity = finding.get('severity', 'medium')
        vuln_type = finding.get('type', 'unknown')
        
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_type[vuln_type] = by_type.get(vuln_type, 0) + 1
    
    # Get critical findings
    critical_findings = [f for f in findings if f.get('severity') == 'critical'][:10]
    
    return {
        'total_findings': len(findings),
        'by_severity': by_severity,
        'by_type': by_type,
        'critical_findings': critical_findings,
        'high_findings': [f for f in findings if f.get('severity') == 'high'][:10],
    }