"""
Secure ZIP file extraction.
"""
import zipfile
import os
import aiofiles
import io
import uuid
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta


UPLOAD_DIR = "storage/uploads"
MAX_ZIP_SIZE = 100 * 1024 * 1024  # 100MB


async def extract_zip(file, max_size_mb: int = 100) -> Optional[str]:
    """
    Securely extract a ZIP file.
    
    Args:
        file: Uploaded file object
        max_size_mb: Maximum ZIP size in MB
        
    Returns:
        Path to extracted directory or None if failed
    """
    try:
        # Create upload directory
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        print(f"📦 Processing upload: {file.filename}")
        
        # Read file content with size limit
        content = await file.read(max_size_mb * 1024 * 1024 + 1)
        
        if len(content) > max_size_mb * 1024 * 1024:
            raise ValueError(f"ZIP file exceeds {max_size_mb}MB limit")
        
        print(f"📦 File size: {len(content)} bytes")
        
        # Sanitize filename
        filename = _sanitize_filename(file.filename)
        if not filename.endswith('.zip'):
            raise ValueError("File must be a ZIP archive")
        
        # Create unique extraction directory
        extract_dir_name = Path(filename).stem + "_" + uuid.uuid4().hex[:8]
        extract_path = Path(UPLOAD_DIR) / extract_dir_name
        extract_path.mkdir(parents=True, exist_ok=False)
        
        print(f"📂 Extracting to: {extract_path}")
        
        # Extract securely and get list of extracted files
        extracted_files = await _extract_zip_safely(content, extract_path)
        
        if not extracted_files:
            print(f"⚠️ No files were extracted from the ZIP")
            shutil.rmtree(extract_path, ignore_errors=True)
            return None
        
        print(f"✅ Successfully extracted {len(extracted_files)} files")
        for f in extracted_files[:10]:  # Show first 10 files
            print(f"  📄 {f}")
        if len(extracted_files) > 10:
            print(f"  ... and {len(extracted_files) - 10} more")
        
        return str(extract_path)
        
    except Exception as e:
        print(f"❌ ZIP extraction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        # Clean up on failure
        if 'extract_path' in locals() and extract_path.exists():
            shutil.rmtree(extract_path, ignore_errors=True)
        return None


async def _extract_zip_safely(zip_content: bytes, extract_path: Path) -> List[str]:
    """
    Extract ZIP content safely, preventing path traversal attacks.
    
    Returns:
        List of extracted file paths (relative to extract_path)
    """
    extracted_files = []
    
    with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_ref:
        # Get list of all members first
        all_members = zip_ref.infolist()
        print(f"📦 ZIP contains {len(all_members)} entries")
        
        # Validate zip structure first
        for member in all_members:
            member_path = Path(member.filename)
            
            # Check for path traversal attempts
            if member_path.is_absolute() or '..' in member_path.parts:
                print(f"⚠️ Path traversal detected: {member.filename}")
                raise ValueError(f"Potential path traversal detected: {member.filename}")
        
        # Extract all files
        for member in all_members:
            member_path = Path(member.filename)
            
            # Skip macOS metadata and hidden files
            if member.filename.startswith('__MACOSX') or member.filename.startswith('._'):
                print(f"⏭️ Skipping macOS metadata: {member.filename}")
                continue
                
            # Skip directories (they'll be created as needed)
            if member.is_dir():
                continue
                
            # Build target path
            target_path = extract_path / member_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Extract file
            with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                target.write(source.read())
            
            # Add to list of extracted files
            extracted_files.append(str(member_path))
        
        # Also check if there are any files at the root level
        if not extracted_files:
            print("⚠️ No files extracted - checking if ZIP is empty or contains only directories")
    
    return extracted_files


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    if not filename:
        return "upload.zip"
    
    # Remove directory components
    filename = Path(filename).name
    
    # Remove dangerous characters
    dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Ensure it ends with .zip
    if not filename.endswith('.zip'):
        filename += '.zip'
    
    return filename


def _is_dangerous_file(filename: str) -> bool:
    """Check if file type is potentially dangerous."""
    dangerous_extensions = {
        '.exe', '.bat', '.cmd', '.sh', '.bin', '.dll', '.so',
        '.pyc', '.pyo', '.pyd', '.php', '.jsp', '.asp'
    }
    
    ext = Path(filename).suffix.lower()
    return ext in dangerous_extensions


def cleanup_old_zips(max_age_days: int = 7) -> int:
    """
    Clean up old extracted ZIP directories.
    
    Args:
        max_age_days: Delete directories older than this many days
        
    Returns:
        Number of directories deleted
    """
    upload_dir = Path(UPLOAD_DIR)
    if not upload_dir.exists():
        return 0
    
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    deleted_count = 0
    
    for item in upload_dir.iterdir():
        if item.is_dir():
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < cutoff_time:
                    shutil.rmtree(item, ignore_errors=True)
                    deleted_count += 1
                    print(f"🧹 Cleaned up old upload: {item.name}")
            except Exception as e:
                print(f"⚠️ Failed to clean up {item}: {e}")
                continue
    
    return deleted_count


def count_files_in_directory(directory: str) -> int:
    """Count files in directory recursively."""
    count = 0
    for root, dirs, files in os.walk(directory):
        count += len(files)
    return count