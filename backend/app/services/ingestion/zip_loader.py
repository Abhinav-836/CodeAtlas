"""
Secure ZIP file extraction.
"""
import zipfile
import os
import io
import uuid
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta


UPLOAD_DIR = "storage/uploads"
MAX_ZIP_SIZE = 100 * 1024 * 1024  # 100MB

# Zip-bomb protection. A 100MB upload can declare (and decompress to)
# many GB; on a 512MB Render instance that kills the whole service.
MAX_UNCOMPRESSED_TOTAL = 500 * 1024 * 1024   # 500MB extracted in total
MAX_UNCOMPRESSED_FILE = 50 * 1024 * 1024     # 50MB per file
MAX_ZIP_ENTRIES = 20000
MAX_COMPRESSION_RATIO = 200                  # per-file uncompressed/compressed
CHUNK_SIZE = 1024 * 1024


async def extract_zip(file, max_size_mb: int = 100) -> Optional[str]:
    """
    Securely extract a ZIP file.

    Returns the extracted directory path, or None on an internal failure.
    Raises ValueError for user-facing problems (too big, zip bomb,
    traversal, not a zip) so the route can return a clear 400.
    """
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        print(f"📦 Processing upload: {file.filename}")

        content = await file.read(max_size_mb * 1024 * 1024 + 1)
        if len(content) > max_size_mb * 1024 * 1024:
            raise ValueError(f"ZIP file exceeds {max_size_mb}MB limit")
        print(f"📦 File size: {len(content)} bytes")

        filename = _sanitize_filename(file.filename)
        if not filename.endswith('.zip'):
            raise ValueError("File must be a ZIP archive")

        extract_dir_name = Path(filename).stem + "_" + uuid.uuid4().hex[:8]
        extract_path = Path(UPLOAD_DIR) / extract_dir_name
        extract_path.mkdir(parents=True, exist_ok=False)
        print(f"📂 Extracting to: {extract_path}")

        extracted_files = await _extract_zip_safely(content, extract_path)

        if not extracted_files:
            print("⚠️ No files were extracted from the ZIP")
            shutil.rmtree(extract_path, ignore_errors=True)
            return None

        print(f"✅ Successfully extracted {len(extracted_files)} files")
        for f in extracted_files[:10]:
            print(f"  📄 {f}")
        if len(extracted_files) > 10:
            print(f"  ... and {len(extracted_files) - 10} more")

        return str(extract_path)

    except (ValueError, zipfile.BadZipFile) as e:
        print(f"❌ ZIP rejected: {str(e)}")
        if 'extract_path' in locals() and extract_path.exists():
            shutil.rmtree(extract_path, ignore_errors=True)
        raise ValueError(str(e) if not isinstance(e, zipfile.BadZipFile) else "File is not a valid ZIP archive")
    except Exception as e:
        print(f"❌ ZIP extraction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'extract_path' in locals() and extract_path.exists():
            shutil.rmtree(extract_path, ignore_errors=True)
        return None


async def _extract_zip_safely(zip_content: bytes, extract_path: Path) -> List[str]:
    """
    Extract ZIP content safely, preventing path traversal and zip bombs.

    Returns:
        List of extracted file paths (relative to extract_path)
    """
    extracted_files = []

    with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_ref:
        all_members = zip_ref.infolist()
        print(f"📦 ZIP contains {len(all_members)} entries")

        if len(all_members) > MAX_ZIP_ENTRIES:
            raise ValueError(f"ZIP has too many entries (max {MAX_ZIP_ENTRIES})")

        # Validate structure and declared sizes before writing anything.
        declared_total = 0
        for member in all_members:
            member_path = Path(member.filename)

            if member_path.is_absolute() or '..' in member_path.parts:
                print(f"⚠️ Path traversal detected: {member.filename}")
                raise ValueError(f"Potential path traversal detected: {member.filename}")

            if member.is_dir():
                continue
            if member.file_size > MAX_UNCOMPRESSED_FILE:
                raise ValueError(f"File too large inside ZIP: {member.filename}")
            # Ratio check only for big entries: tiny files (blank lines,
            # repeated whitespace) can legitimately compress 1000:1.
            if (
                member.file_size > 1024 * 1024
                and member.compress_size > 0
                and member.file_size / member.compress_size > MAX_COMPRESSION_RATIO
            ):
                raise ValueError(f"Suspicious compression ratio (zip bomb?): {member.filename}")
            declared_total += member.file_size

        if declared_total > MAX_UNCOMPRESSED_TOTAL:
            raise ValueError("ZIP expands beyond the 500MB extraction limit")

        written_total = 0

        for member in all_members:
            member_path = Path(member.filename)

            # Skip macOS metadata
            if member.filename.startswith('__MACOSX') or member.filename.startswith('._'):
                continue
            if member.is_dir():
                continue

            target_path = extract_path / member_path
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Extract in chunks and count real bytes - header sizes can lie.
            written_file = 0
            with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                while True:
                    chunk = source.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    written_file += len(chunk)
                    written_total += len(chunk)
                    if written_file > MAX_UNCOMPRESSED_FILE or written_total > MAX_UNCOMPRESSED_TOTAL:
                        raise ValueError("ZIP content exceeds the extraction size limit")
                    target.write(chunk)

            extracted_files.append(str(member_path))

    return extracted_files


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    if not filename:
        return "upload.zip"
    filename = Path(filename).name
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        filename = filename.replace(char, '_')
    if not filename.endswith('.zip'):
        filename += '.zip'
    return filename


def _is_dangerous_file(filename: str) -> bool:
    """Check if file type is potentially dangerous."""
    dangerous_extensions = {
        '.exe', '.bat', '.cmd', '.sh', '.bin', '.dll', '.so',
        '.pyc', '.pyo', '.pyd', '.php', '.jsp', '.asp'
    }
    return Path(filename).suffix.lower() in dangerous_extensions


def cleanup_old_zips(max_age_days: int = 7) -> int:
    """Delete extracted upload directories older than max_age_days."""
    upload_dir = Path(UPLOAD_DIR)
    if not upload_dir.exists():
        return 0

    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    deleted_count = 0
    for item in upload_dir.iterdir():
        if item.is_dir():
            try:
                if datetime.fromtimestamp(item.stat().st_mtime) < cutoff_time:
                    shutil.rmtree(item, ignore_errors=True)
                    deleted_count += 1
                    print(f"🧹 Cleaned up old upload: {item.name}")
            except Exception as e:
                print(f"⚠️ Failed to clean up {item}: {e}")
    return deleted_count


def count_files_in_directory(directory: str) -> int:
    """Count files in directory recursively."""
    count = 0
    for _root, _dirs, files in os.walk(directory):
        count += len(files)
    return count