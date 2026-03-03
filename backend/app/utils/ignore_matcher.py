"""
IgnoreMatcher utility for filtering files and directories
similar to .gitignore behavior.
"""

from pathlib import Path
from typing import Iterable, Set
import fnmatch
import os


class IgnoreMatcher:
    """
    Matches file paths against ignore patterns.
    """

    DEFAULT_IGNORE_PATTERNS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "node_modules",
        "dist",
        "build",
        ".idea",
        ".vscode",
        "*.log",
        "*.tmp",
    }

    def __init__(self, ignore_patterns: Iterable[str] | None = None):
        self.ignore_patterns: Set[str] = set(ignore_patterns or [])
        self.ignore_patterns |= self.DEFAULT_IGNORE_PATTERNS

    def should_ignore(self, path: str | Path) -> bool:
        """
        Returns True if the given path should be ignored.
        """
        path = Path(path)
        path_str = str(path).replace(os.sep, "/")

        for pattern in self.ignore_patterns:
            # Directory name match
            if pattern in path.parts:
                return True

            # Wildcard match
            if fnmatch.fnmatch(path_str, pattern):
                return True

            # Partial path match
            if pattern in path_str:
                return True

        return False

    def filter_paths(self, paths: Iterable[str | Path]) -> list[Path]:
        """
        Filters a list of paths, returning only non-ignored ones.
        """
        return [Path(p) for p in paths if not self.should_ignore(p)]
