"""
Recursive file scanner.
"""
import os
from pathlib import Path
from typing import List

from app.utils.ignore_matcher import IgnoreMatcher


def scan_files(path: str, apply_ignore_rules: bool = True) -> List[str]:
    """
    Scan all files in a directory recursively.

    Args:
        path: Directory path to scan
        apply_ignore_rules: If True, filter out files matched by IgnoreMatcher

    Returns:
        List of absolute file paths
    """
    files: List[str] = []
    path_obj = Path(path).resolve()

    print(f"\n🔍 [DEBUG] scan_files called with path: {path}")

    if not path_obj.exists():
        print(f"❌ [DEBUG] Path does not exist: {path}")
        return files

    if not path_obj.is_dir():
        print(f"❌ [DEBUG] Path is not a directory: {path}")
        return files

    print(f"📁 [DEBUG] Scanning directory: {path_obj}")

    matcher = IgnoreMatcher() if apply_ignore_rules else None

    # os.walk recursively yields every subdirectory.
    for root, dirs, filenames in os.walk(path_obj):
        # Prune obvious heavy/irrelevant dirs early so we don't descend into them.
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".")
            and d not in {"__pycache__", "node_modules", ".git", "venv", ".venv", "env"}
        ]

        for filename in filenames:
            if filename.startswith("."):
                continue

            file_path = os.path.join(root, filename)

            if matcher is not None and matcher.should_ignore(file_path):
                continue

            files.append(file_path)

    print(f"✅ [DEBUG] Total files found: {len(files)}")
    return files