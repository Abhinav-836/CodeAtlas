"""
Ignore rules for file scanning.
"""
import fnmatch
import os
from pathlib import Path
from typing import List, Set, Pattern
import re


class IgnoreMatcher:
    """
    Matcher for ignoring files based on patterns.
    
    Supports .gitignore-style patterns with proper precedence.
    """
    
    def __init__(self, base_path: str):
        """
        Initialize ignore matcher.
        
        Args:
            base_path: Base directory path
        """
        self.base_path = Path(base_path).resolve()
        self.patterns: List[tuple[Pattern, bool, bool]] = []  # (pattern, is_negation, is_directory)
        
        # Load default patterns
        self._load_default_patterns()
        
        # Load .gitignore if exists
        self._load_gitignore()
    
    def _load_default_patterns(self):
        """Load default ignore patterns."""
        default_patterns = [
            # Version control
            '.git/', '.gitignore', '.gitmodules', '.gitattributes',
            '.hg/', '.hgignore', '.hgtags',
            '.svn/', '.bzr/', '_darcs/',
            
            # Build artifacts
            '__pycache__/', '*.pyc', '*.pyo', '*.pyd',
            '.Python/', 'pip-log.txt', 'pip-delete-this-directory.txt',
            '*.so', '*.dylib',
            
            # Python
            '*.egg-info/', '*.egg', '.eggs/', '.venv/', 'venv/',
            'env/', 'ENV/', '.env', '.python-version',
            
            # Node.js
            'node_modules/', 'npm-debug.log*', 'yarn-debug.log*', 'yarn-error.log*',
            
            # IDE
            '.vscode/', '.idea/', '*.swp', '*.swo', '*~',
            
            # OS
            '.DS_Store', 'Thumbs.db',
            
            # Logs and temp files
            '*.log', '*.tmp', '*.temp',
            
            # Coverage
            '.coverage', 'htmlcov/', '.cache/',
            
            # Documentation
            '_build/', 'build/', 'dist/', '*.egg',
            
            # Test
            '.tox/', '.pytest_cache/', '.mypy_cache/', '.hypothesis/',
        ]
        
        for pattern in default_patterns:
            self._add_pattern(pattern)
    
    def _load_gitignore(self):
        """Load patterns from .gitignore file."""
        gitignore_path = self.base_path / '.gitignore'
        
        if not gitignore_path.exists():
            return
        
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Handle negated patterns
                    is_negation = line.startswith('!')
                    if is_negation:
                        pattern = line[1:]
                    else:
                        pattern = line
                    
                    # Check if it's a directory pattern
                    is_directory = pattern.endswith('/')
                    if is_directory:
                        pattern = pattern[:-1]
                    
                    self._add_pattern(pattern, is_negation, is_directory)
        except (IOError, UnicodeDecodeError):
            pass
    
    def _add_pattern(self, pattern: str, is_negation: bool = False, is_directory: bool = False):
        """Add a pattern to the matcher."""
        # Convert gitignore pattern to regex
        regex_pattern = self._gitignore_to_regex(pattern)
        if regex_pattern:
            self.patterns.append((re.compile(regex_pattern), is_negation, is_directory))
    
    def _gitignore_to_regex(self, pattern: str) -> str:
        """
        Convert gitignore pattern to regex.
        
        Rules:
        - * matches any string
        - ? matches any single character
        - [abc] matches a, b, or c
        - ** matches any directory
        - / at start matches from root
        - / at end matches directories
        """
        # Escape regex special characters except *, ?, [, ]
        pattern = re.escape(pattern)
        
        # Unescape the special characters we want to keep
        pattern = pattern.replace(r'\*', '.*')
        pattern = pattern.replace(r'\?', '.')
        pattern = pattern.replace(r'\[', '[').replace(r'\]', ']')
        
        # Handle ** (matches across directories)
        pattern = pattern.replace(r'\*\*', '.*')
        
        # Handle directory separator
        pattern = pattern.replace(r'\/', '/')
        
        # If pattern starts with /, anchor to start
        if pattern.startswith('/'):
            pattern = '^' + pattern[1:]
        else:
            pattern = r'(^|/)' + pattern
        
        # If pattern ends with /, it matches directories
        if pattern.endswith('/'):
            pattern = pattern[:-1] + r'($|/)'
        else:
            pattern = pattern + r'($|/)'
        
        return pattern
    
    def should_ignore(self, file_path: str) -> bool:
        """
        Check if a file should be ignored.
        
        Args:
            file_path: Absolute file path
            
        Returns:
            True if file should be ignored
        """
        file_path_obj = Path(file_path).resolve()
        
        # Make path relative to base
        try:
            rel_path = file_path_obj.relative_to(self.base_path)
        except ValueError:
            # File is outside base directory
            return True
        
        rel_str = str(rel_path).replace('\\', '/')
        is_dir = file_path_obj.is_dir()
        
        # Track matches
        matches = []
        
        for pattern, is_negation, pattern_is_dir in self.patterns:
            # Skip if pattern is for directories only and this is a file
            if pattern_is_dir and not is_dir:
                continue
            
            if pattern.search(rel_str):
                matches.append((is_negation, pattern_is_dir))
        
        # Apply negation logic (later negations override earlier ones)
        # Gitignore: later lines override earlier ones
        should_ignore = False
        
        for is_negation, _ in reversed(matches):
            if is_negation:
                should_ignore = False
            else:
                should_ignore = True
        
        return should_ignore
    
    def filter_files(self, files: List[str]) -> List[str]:
        """
        Filter list of files, removing ignored ones.
        
        Args:
            files: List of file paths
            
        Returns:
            Filtered list
        """
        return [f for f in files if not self.should_ignore(f)]


def should_ignore(file_path: str, base_path: str = None) -> bool:
    """
    Quick check if a file should be ignored.
    
    Args:
        file_path: File path to check
        base_path: Base directory (defaults to file's parent)
        
    Returns:
        True if file should be ignored
    """
    if base_path is None:
        base_path = str(Path(file_path).parent)
    
    matcher = IgnoreMatcher(base_path)
    return matcher.should_ignore(file_path)