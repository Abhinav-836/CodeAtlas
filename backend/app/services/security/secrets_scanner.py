"""
Secret scanning for code repositories.
"""
import re
import os
from pathlib import Path
from typing import List, Dict, Any

# Common secret patterns
SECRET_PATTERNS = [
    # API Keys
    (r'(?i)(api[_-]?key["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,50})(["\'])', 'API_KEY'),
    (r'(?i)(secret[_-]?key["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,50})(["\'])', 'SECRET_KEY'),
    
    # Tokens
    (r'(?i)(access[_-]?token["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,100})(["\'])', 'ACCESS_TOKEN'),
    (r'(?i)(refresh[_-]?token["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,100})(["\'])', 'REFRESH_TOKEN'),
    
    # Passwords
    (r'(?i)(password["\']?\s*[:=]\s*["\'])([^"\']{6,50})(["\'])', 'PASSWORD'),
    (r'(?i)(passwd["\']?\s*[:=]\s*["\'])([^"\']{6,50})(["\'])', 'PASSWORD'),
    
    # Database credentials
    (r'(?i)(database[_-]?url["\']?\s*[:=]\s*["\'])([^"\']+://[^"\']+)(["\'])', 'DATABASE_URL'),
    (r'(?i)(postgres[_-]?url["\']?\s*[:=]\s*["\'])([^"\']+://[^"\']+)(["\'])', 'DATABASE_URL'),
    
    # AWS credentials
    (r'(?i)(aws[_-]?access[_-]?key["\']?\s*[:=]\s*["\'])([A-Z0-9]{20})(["\'])', 'AWS_ACCESS_KEY'),
    (r'(?i)(aws[_-]?secret[_-]?key["\']?\s*[:=]\s*["\'])([a-zA-Z0-9/+]{40})(["\'])', 'AWS_SECRET_KEY'),
    
    # SSH keys
    (r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----', 'SSH_PRIVATE_KEY'),
    
    # Crypto wallets
    (r'(?i)(private[_-]?key["\']?\s*[:=]\s*["\'])(0x[a-fA-F0-9]{64})(["\'])', 'CRYPTO_PRIVATE_KEY'),
]

# Common false positives to ignore
FALSE_POSITIVES = [
    r'EXAMPLE_KEY', r'SAMPLE_KEY', r'YOUR_KEY_HERE', r'PUT_YOUR_KEY_HERE',
    r'00000000-0000-0000-0000-000000000000',  # UUID zeros
    r'test_key', r'dummy_key', r'fake_key',
    r'password123', r'admin123', r'changeme',
]

# Files to exclude from scanning
EXCLUDED_FILES = [
    'package-lock.json', 'yarn.lock',  # These contain hashes, not secrets
    '.min.js', '.min.css',             # Minified files
    '*.pyc', '*.pyo',                  # Python bytecode
    '.git/', 'node_modules/',          # Dependencies
]

# File extensions to scan
SCANNABLE_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.go', '.rb', '.php',
    '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf',
    '.env', '.properties',
    '.txt', '.md', '.rst',
}


def scan_secrets(files: List[str]) -> List[Dict[str, Any]]:
    """
    Scan files for hardcoded secrets.
    
    Args:
        files: List of file paths to scan
        
    Returns:
        List of found secrets with metadata
    """
    findings = []
    
    for file_path in files:
        # Skip excluded files
        if _should_skip_file(file_path):
            continue
            
        try:
            file_findings = _scan_file(file_path)
            findings.extend(file_findings)
        except (IOError, UnicodeDecodeError, PermissionError):
            # Skip files we can't read
            continue
    
    return findings


def _scan_file(file_path: str) -> List[Dict[str, Any]]:
    """Scan a single file for secrets."""
    findings = []
    file_ext = Path(file_path).suffix.lower()
    
    # Skip if extension not in our list
    if file_ext not in SCANNABLE_EXTENSIONS and not file_path.endswith('.env'):
        return findings
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # Skip very large files
            if len(content) > 10 * 1024 * 1024:  # 10MB
                return findings
                
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line_findings = _scan_line(line, line_num, file_path)
                findings.extend(line_findings)
                
    except Exception:
        # Skip files we can't process
        return findings
    
    return findings


def _scan_line(line: str, line_num: int, file_path: str) -> List[Dict[str, Any]]:
    """Scan a single line for secrets."""
    findings = []
    
    for pattern, secret_type in SECRET_PATTERNS:
        matches = re.finditer(pattern, line)
        
        for match in matches:
            # Extract the secret value (group 2 in our patterns)
            secret_value = match.group(2) if len(match.groups()) >= 2 else match.group(0)
            
            # Skip false positives
            if _is_false_positive(secret_value):
                continue
                
            # Calculate risk score
            risk_score = _calculate_risk_score(secret_type, secret_value)
            
            # Create finding
            finding = {
                'file': file_path,
                'line': line_num,
                'type': secret_type,
                'value_preview': _mask_secret(secret_value),
                'risk_score': risk_score,
                'risk_level': _get_risk_level(risk_score),
                'context': line.strip()[:200],  # First 200 chars for context
                'full_match': match.group(0),
            }
            
            findings.append(finding)
    
    return findings


def _should_skip_file(file_path: str) -> bool:
    """Check if file should be skipped."""
    path_str = file_path.lower()
    
    # Check excluded patterns
    for pattern in EXCLUDED_FILES:
        if pattern.endswith('/'):
            if pattern[:-1] in path_str:
                return True
        elif pattern in path_str:
            return True
    
    # Check file size (skip > 5MB)
    try:
        if os.path.getsize(file_path) > 5 * 1024 * 1024:
            return True
    except OSError:
        return True
    
    return False


def _is_false_positive(secret_value: str) -> bool:
    """Check if a match is likely a false positive."""
    secret_lower = secret_value.lower()
    
    for fp_pattern in FALSE_POSITIVES:
        if re.search(fp_pattern, secret_lower, re.IGNORECASE):
            return True
    
    # Common placeholder patterns
    if re.match(r'^(xxx+|test|example|dummy|fake|placeholder)', secret_lower):
        return True
    
    # Too short to be a real secret
    if len(secret_value) < 8:
        return True
    
    return False


def _calculate_risk_score(secret_type: str, secret_value: str) -> int:
    """Calculate risk score for a found secret."""
    score = 50  # Base score
    
    # Adjust based on secret type
    type_weights = {
        'SSH_PRIVATE_KEY': 40,
        'CRYPTO_PRIVATE_KEY': 40,
        'AWS_SECRET_KEY': 30,
        'SECRET_KEY': 25,
        'ACCESS_TOKEN': 20,
        'API_KEY': 15,
        'PASSWORD': 10,
        'DATABASE_URL': 15,
    }
    
    score += type_weights.get(secret_type, 0)
    
    # Adjust based on secret length and complexity
    if len(secret_value) >= 32:
        score += 10
    if re.search(r'[A-Z]', secret_value) and re.search(r'[a-z]', secret_value):
        score += 5
    if re.search(r'\d', secret_value):
        score += 5
    if re.search(r'[^A-Za-z0-9]', secret_value):
        score += 5
    
    return min(score, 100)  # Cap at 100


def _get_risk_level(score: int) -> str:
    """Convert risk score to level."""
    if score >= 80:
        return 'critical'
    elif score >= 60:
        return 'high'
    elif score >= 40:
        return 'medium'
    elif score >= 20:
        return 'low'
    else:
        return 'info'


def _mask_secret(secret: str) -> str:
    """Mask secret for safe display."""
    if len(secret) <= 8:
        return '***'
    
    # Show first 4 and last 4 characters, mask the middle
    first_part = secret[:4]
    last_part = secret[-4:] if len(secret) > 8 else ''
    mask_length = len(secret) - 8
    
    if mask_length > 0:
        return f"{first_part}{'*' * mask_length}{last_part}"
    else:
        return f"{first_part}{'*' * (len(secret) - 4)}"


def summarize_findings(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize secret scanning findings."""
    if not findings:
        return {
            'total_findings': 0,
            'risk_level': 'none',
            'by_type': {},
            'by_risk': {},
        }
    
    by_type = {}
    by_risk = {}
    
    for finding in findings:
        # Count by type
        secret_type = finding['type']
        by_type[secret_type] = by_type.get(secret_type, 0) + 1
        
        # Count by risk level
        risk_level = finding['risk_level']
        by_risk[risk_level] = by_risk.get(risk_level, 0) + 1
    
    # Determine overall risk level
    if by_risk.get('critical', 0) > 0:
        overall_risk = 'critical'
    elif by_risk.get('high', 0) > 0:
        overall_risk = 'high'
    elif by_risk.get('medium', 0) > 0:
        overall_risk = 'medium'
    elif by_risk.get('low', 0) > 0:
        overall_risk = 'low'
    else:
        overall_risk = 'info'
    
    return {
        'total_findings': len(findings),
        'risk_level': overall_risk,
        'by_type': by_type,
        'by_risk': by_risk,
        'critical_findings': [f for f in findings if f['risk_level'] == 'critical'][:5],
        'high_findings': [f for f in findings if f['risk_level'] == 'high'][:5],
    }