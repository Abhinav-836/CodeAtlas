"""
Git repository loader with proper error handling.
"""
import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from datetime import datetime, timedelta


def clone_repo(url: str, branch: str = "main", timeout: int = 60, depth: int = 1) -> Optional[Dict[str, Any]]:
    """
    Clone a Git repository with proper error handling.
    
    Args:
        url: Git repository URL
        branch: Branch to clone
        timeout: Clone timeout in seconds
        depth: Clone depth (1 for shallow)
        
    Returns:
        Dictionary with clone info or None if failed
    """
    result = {
        'url': url,
        'branch': branch,
        'success': False,
        'error': None,
        'path': None,
        'size_kb': 0,
        'duration_seconds': 0
    }
    
    try:
        # Validate URL
        if not _is_valid_git_url(url):
            result['error'] = f"Invalid Git URL: {url}"
            return result
        
        # Parse repo name from URL
        repo_name = _extract_repo_name(url)
        if not repo_name:
            result['error'] = f"Could not extract repo name from URL: {url}"
            return result
        
        # Create temp directory for cloning
        temp_dir = tempfile.mkdtemp(prefix="codeatlas_")
        clone_path = Path(temp_dir) / repo_name
        
        # Prepare clone command
        cmd = ['git', 'clone']
        if depth and depth > 0:
            cmd.extend(['--depth', str(depth)])
        if branch:
            cmd.extend(['--branch', branch])
        cmd.extend([url, str(clone_path)])
        
        # Execute clone with timeout
        import time
        start_time = time.time()
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=temp_dir
        )
        
        result['duration_seconds'] = round(time.time() - start_time, 2)
        
        if process.returncode != 0:
            result['error'] = f"Git clone failed: {process.stderr[:200]}"
            shutil.rmtree(temp_dir, ignore_errors=True)
            return result
        
        # Check if clone directory exists and has content
        if not clone_path.exists():
            result['error'] = "Clone directory not created"
            shutil.rmtree(temp_dir, ignore_errors=True)
            return result
        
        # Calculate size
        size_kb = _calculate_directory_size(clone_path) / 1024
        
        # Move to final location
        final_dir = Path("storage/repos") / repo_name
        if final_dir.exists():
            shutil.rmtree(final_dir, ignore_errors=True)
        
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(clone_path), str(final_dir))
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Verify final directory
        if not final_dir.exists():
            result['error'] = "Failed to move repository to final location"
            return result
        
        # Success
        result.update({
            'success': True,
            'path': str(final_dir),
            'size_kb': round(size_kb, 2),
            'repo_name': repo_name,
        })
        
        return result
        
    except subprocess.TimeoutExpired:
        result['error'] = f"Clone timeout after {timeout} seconds"
    except PermissionError as e:
        result['error'] = f"Permission error: {str(e)}"
    except OSError as e:
        result['error'] = f"OS error: {str(e)}"
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
    
    # Cleanup on failure
    if 'temp_dir' in locals() and Path(temp_dir).exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return result


def _is_valid_git_url(url: str) -> bool:
    """Check if URL is a valid Git repository URL."""
    if not url or not isinstance(url, str):
        return False
    
    url_lower = url.lower()
    
    # Common Git URL patterns
    patterns = [
        'https://github.com/',
        'https://gitlab.com/',
        'https://bitbucket.org/',
        'git@github.com:',
        'git@gitlab.com:',
        'git@bitbucket.org:',
    ]
    
    return any(url_lower.startswith(pattern) for pattern in patterns)


def _extract_repo_name(url: str) -> str:
    """Extract repository name from URL."""
    try:
        # Parse URL
        parsed = urlparse(url)
        
        if parsed.netloc:  # HTTPS URL
            path = parsed.path.strip('/')
            if path.endswith('.git'):
                path = path[:-4]
            name = Path(path).name
        else:  # SSH URL
            # git@github.com:user/repo.git
            if ':' in url:
                path_part = url.split(':', 1)[1]
                if path_part.endswith('.git'):
                    path_part = path_part[:-4]
                name = Path(path_part).name
            else:
                name = Path(url).stem
    except Exception:
        name = Path(url).stem
    
    # Clean up the name
    name = name.replace(' ', '_').replace('/', '_')
    
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    
    return name or 'repository'


def _calculate_directory_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total_size = 0
    
    for root, dirs, files in os.walk(path):
        # Skip .git directory
        dirs[:] = [d for d in dirs if d != '.git']
        
        for file in files:
            file_path = Path(root) / file
            try:
                total_size += file_path.stat().st_size
            except OSError:
                continue
    
    return total_size


def cleanup_old_repos(max_age_days: int = 30) -> int:
    """
    Clean up old cloned repositories.
    
    Args:
        max_age_days: Delete repos older than this many days
        
    Returns:
        Number of repositories deleted
    """
    repos_dir = Path("storage/repos")
    if not repos_dir.exists():
        return 0
    
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    deleted_count = 0
    
    for item in repos_dir.iterdir():
        if item.is_dir():
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < cutoff_time:
                    shutil.rmtree(item, ignore_errors=True)
                    deleted_count += 1
            except Exception:
                continue
    
    return deleted_count