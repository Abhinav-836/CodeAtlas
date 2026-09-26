"""
Git repository loader with proper error handling.
"""
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def clone_repo(
    url: str,
    branch: Optional[str] = None,
    timeout: int = 60,
    depth: int = 1,
) -> Optional[Dict[str, Any]]:
    """
    Clone a Git repository.

    Args:
        url: Git repository URL
        branch: Branch to clone. If None, git clones the remote's default
                branch (works for repos whose default is `master`, `develop`,
                or anything else - not just `main`).
        timeout: Clone timeout in seconds
        depth: Clone depth (1 = shallow)

    Returns:
        Dict with clone info, or a dict with success=False and an error.
    """
    result: Dict[str, Any] = {
        "url": url,
        "branch": branch or "(default)",
        "success": False,
        "error": None,
        "path": None,
        "size_kb": 0,
        "duration_seconds": 0,
    }

    temp_dir: Optional[str] = None

    try:
        if not _is_valid_git_url(url):
            result["error"] = f"Invalid Git URL: {url}"
            return result

        repo_name = _extract_repo_name(url)
        if not repo_name:
            result["error"] = f"Could not extract repo name from URL: {url}"
            return result

        temp_dir = tempfile.mkdtemp(prefix="codeatlas_")
        clone_path = Path(temp_dir) / repo_name

        cmd = ["git", "clone"]
        if depth and depth > 0:
            cmd.extend(["--depth", str(depth)])
        # Only pass --branch when the caller explicitly asked for one.
        # Otherwise git uses the remote's default branch (master, main,
        # develop, whatever it is).
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([url, str(clone_path)])

        start_time = time.time()
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=temp_dir,
        )
        result["duration_seconds"] = round(time.time() - start_time, 2)

        if process.returncode != 0:
            result["error"] = f"Git clone failed: {process.stderr[:300]}"
            shutil.rmtree(temp_dir, ignore_errors=True)
            return result

        if not clone_path.exists():
            result["error"] = "Clone directory not created"
            shutil.rmtree(temp_dir, ignore_errors=True)
            return result

        # Read back the actual branch that was cloned. This is what makes
        # the response accurate even when we didn't specify --branch.
        actual_branch = _get_current_branch(clone_path) or branch or "unknown"
        result["branch"] = actual_branch

        size_kb = _calculate_directory_size(clone_path) / 1024

        final_dir = Path("storage/repos") / repo_name
        if final_dir.exists():
            shutil.rmtree(final_dir, ignore_errors=True)

        final_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(clone_path), str(final_dir))
        shutil.rmtree(temp_dir, ignore_errors=True)

        if not final_dir.exists():
            result["error"] = "Failed to move repository to final location"
            return result

        result.update(
            {
                "success": True,
                "path": str(final_dir),
                "size_kb": round(size_kb, 2),
                "repo_name": repo_name,
            }
        )
        return result

    except subprocess.TimeoutExpired:
        result["error"] = f"Clone timeout after {timeout} seconds"
    except PermissionError as e:
        result["error"] = f"Permission error: {str(e)}"
    except OSError as e:
        result["error"] = f"OS error: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"

    if temp_dir and Path(temp_dir).exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    return result


def _get_current_branch(repo_path: Path) -> Optional[str]:
    """Read the checked-out branch name from a cloned repo."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            branch = proc.stdout.strip()
            # `rev-parse --abbrev-ref HEAD` returns "HEAD" for detached
            # checkouts (e.g. when cloning a specific tag). Fall back.
            if branch and branch != "HEAD":
                return branch
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def _is_valid_git_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    url_lower = url.lower()
    patterns = [
        "https://github.com/",
        "https://gitlab.com/",
        "https://bitbucket.org/",
        "git@github.com:",
        "git@gitlab.com:",
        "git@bitbucket.org:",
    ]
    return any(url_lower.startswith(p) for p in patterns)


def _extract_repo_name(url: str) -> str:
    try:
        parsed = urlparse(url)
        if parsed.netloc:
            path = parsed.path.strip("/")
            if path.endswith(".git"):
                path = path[:-4]
            name = Path(path).name
        else:
            if ":" in url:
                path_part = url.split(":", 1)[1]
                if path_part.endswith(".git"):
                    path_part = path_part[:-4]
                name = Path(path_part).name
            else:
                name = Path(url).stem
    except Exception:
        name = Path(url).stem

    name = name.replace(" ", "_").replace("/", "_")
    for char in '<>:"/\\|?*':
        name = name.replace(char, "")
    return name or "repository"


def _calculate_directory_size(path: Path) -> int:
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d != ".git"]
        for file in files:
            try:
                total += (Path(root) / file).stat().st_size
            except OSError:
                continue
    return total


def cleanup_old_repos(max_age_days: int = 30) -> int:
    repos_dir = Path("storage/repos")
    if not repos_dir.exists():
        return 0

    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    deleted = 0
    for item in repos_dir.iterdir():
        if item.is_dir():
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < cutoff_time:
                    shutil.rmtree(item, ignore_errors=True)
                    deleted += 1
            except Exception:
                continue
    return deleted