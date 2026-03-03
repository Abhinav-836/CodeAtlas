import os
from pathlib import Path
from typing import List

def scan_files(path: str) -> List[str]:
    """
    Scan all files in a directory recursively.
    
    Args:
        path: Directory path to scan
        
    Returns:
        List of file paths
    """
    files = []
    path_obj = Path(path)
    
    print(f"\n🔍 [DEBUG] scan_files called with path: {path}")
    
    if not path_obj.exists():
        print(f"❌ [DEBUG] Path does not exist: {path}")
        return files
    
    if not path_obj.is_dir():
        print(f"❌ [DEBUG] Path is not a directory: {path}")
        return files
    
    print(f"📁 [DEBUG] Scanning directory: {path}")
    
    # Use os.walk to go through ALL subdirectories recursively
    file_count = 0
    for root, dirs, filenames in os.walk(path_obj):
        print(f"   📁 Scanning subdirectory: {root}")
        for filename in filenames:
            file_path = os.path.join(root, filename)
            files.append(file_path)
            file_count += 1
            if file_count <= 10:  # Show first 10 files
                print(f"      📄 Found: {file_path}")
    
    print(f"✅ [DEBUG] Total files found: {len(files)}")
    return files