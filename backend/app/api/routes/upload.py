"""
File upload endpoints.

Every upload / clone is stamped with the caller's owner hash (see
app/core/owner.py). Only that owner can analyze, list or delete it.
"""
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.owner import (
    delete_folder_owner,
    get_owner,
    owns_folder,
    write_folder_owner,
)
from app.services.ingestion.zip_loader import extract_zip

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOADS_DIR = Path("storage/uploads")
MAX_FILE_SIZE = 100 * 1024 * 1024
ALLOWED_EXTENSIONS = {".zip"}
ALLOWED_MIME_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "multipart/x-zip",
}


@router.post("/zip")
async def upload_zip(
    file: UploadFile = File(...),
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    try:
        await _validate_upload_file(file)
        print(f"📤 Uploading: {file.filename} ({file.content_type})")

        try:
            extract_path = await extract_zip(file)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if not extract_path:
            raise HTTPException(
                status_code=400,
                detail="Failed to extract ZIP file. File might be corrupted or empty.",
            )

        write_folder_owner(extract_path, owner)

        return {
            "success": True,
            "filename": file.filename,
            "extracted_to": extract_path,
            "file_count": _count_files_in_directory(extract_path),
            "message": f"Successfully uploaded and extracted {file.filename}",
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def _validate_upload_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(400, detail="No filename provided")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            detail=f"File type '{file_ext}' not allowed. Only ZIP files are supported.",
        )

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            400,
            detail=f"MIME type '{file.content_type}' not allowed for ZIP uploads.",
        )

    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )
    await file.seek(0)


def _count_files_in_directory(directory: str) -> int:
    try:
        count = 0
        for _root, dirs, files in os.walk(directory):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in {"__pycache__", "node_modules", "venv", ".venv"}
            ]
            count += len(files)
        return count
    except Exception:
        return 0


def _extract_github_info(url: str) -> Optional[Dict[str, str]]:
    """
    Parse any GitHub URL. Returns None if unparseable.

    Does NOT guess a branch: `branch` is only set when the URL contains one
    (e.g. /tree/develop).
    """
    if not url:
        return None

    url = url.strip().rstrip("/")

    patterns = [
        (r"^https?://github\.com/([^/]+)/([^/#?]+)/tree/([^/#?]+)", 3),
        (r"^https?://github\.com/([^/]+)/([^/#?]+)/blob/([^/#?]+)", 3),
        (r"^https?://github\.com/([^/]+)/([^/#?]+)\.git", 2),
        (r"^https?://github\.com/([^/]+)/([^/#?]+)", 2),
        (r"^git@github\.com:([^/]+)/([^/#?]+)\.git", 2),
        (r"^git@github\.com:([^/]+)/([^/#?]+)", 2),
        (r"^gh repo clone ([^/]+)/([^/#?]+)", 2),
    ]

    for pattern, group_count in patterns:
        match = re.search(pattern, url)
        if match:
            groups = match.groups()
            username = groups[0]
            repo = groups[1].replace(".git", "")
            info: Dict[str, str] = {
                "repo_url": f"https://github.com/{username}/{repo}.git",
                "repo_name": repo,
                "username": username,
                "original_url": url,
            }
            if group_count == 3 and len(groups) > 2:
                info["branch"] = groups[2]
            return info

    simple_match = re.search(r"([^/]+)/([^/]+)", url)
    if simple_match:
        username, repo = simple_match.groups()
        repo = repo.replace(".git", "")
        return {
            "repo_url": f"https://github.com/{username}/{repo}.git",
            "repo_name": repo,
            "username": username,
            "original_url": url,
        }

    return None


@router.post("/github")
async def upload_github(
    repo_url: str,
    branch: Optional[str] = None,
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    try:
        from app.services.ingestion.repo_loader import clone_repo

        if not repo_url:
            raise HTTPException(400, detail="Repository URL is required")

        print(f"🌐 Received GitHub URL: {repo_url}")

        repo_info = _extract_github_info(repo_url)
        if repo_info:
            normalized_url = repo_info["repo_url"]
            repo_name = repo_info["repo_name"]
            # Precedence: explicit query param > URL-embedded branch > None
            branch_to_use = branch or repo_info.get("branch")
        else:
            normalized_url = repo_url
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            branch_to_use = branch

        print(f"📦 Cloning repository: {normalized_url} (branch: {branch_to_use or 'default'})")

        result = clone_repo(normalized_url, branch=branch_to_use)

        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error") if result else "Clone failed"

            # Retry without .git only when the URL looks like the problem.
            if (
                ".git" in normalized_url
                and "not found" in error_msg.lower()
                and "branch" not in error_msg.lower()
            ):
                alt_url = normalized_url.replace(".git", "")
                print(f"🔄 Retrying without .git: {alt_url}")
                result = clone_repo(alt_url, branch=branch_to_use)
                if result and result.get("success"):
                    normalized_url = alt_url

            if not result or not result.get("success"):
                raise HTTPException(400, detail=f"Failed to clone repository: {error_msg}")

        write_folder_owner(result["path"], owner)
        print(f"✅ Successfully cloned to: {result['path']}")

        return {
            "success": True,
            "repo_url": repo_url,
            "normalized_url": normalized_url,
            "repo_name": repo_name,
            "branch": result.get("branch", branch_to_use or "default"),
            "local_path": result["path"],
            "size_kb": result.get("size_kb", 0),
            "duration_seconds": result.get("duration_seconds", 0),
            "file_count": _count_files_in_directory(result["path"]),
            "message": f"Successfully cloned {repo_name}",
        }
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="GitPython not installed. Install with: pip install gitpython",
        )
    except Exception as e:
        print(f"❌ GitHub upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GitHub upload failed: {str(e)}")


@router.get("/uploads")
async def list_uploads(owner: str = Depends(get_owner)) -> Dict[str, Any]:
    """List only the caller's own ZIP uploads."""
    try:
        if not UPLOADS_DIR.exists():
            return {"uploads": [], "total": 0, "total_size_kb": 0}

        uploads = []
        total_size = 0.0
        for item in UPLOADS_DIR.iterdir():
            if not item.is_dir() or not owns_folder(str(item), owner):
                continue
            try:
                size_kb = _get_directory_size_kb(item)
                total_size += size_kb
                stat = item.stat()
                uploads.append(
                    {
                        "name": item.name,
                        "size_kb": round(size_kb, 2),
                        "size_human": _human_readable_size(size_kb * 1024),
                        "file_count": _count_files_in_directory(str(item)),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )
            except Exception as e:
                print(f"⚠️ Error processing upload {item}: {e}")

        uploads.sort(key=lambda x: x["modified"], reverse=True)
        return {
            "uploads": uploads[:50],
            "total": len(uploads),
            "total_size_kb": round(total_size, 2),
            "total_size_human": _human_readable_size(total_size * 1024),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list uploads: {str(e)}")


def _get_directory_size_kb(directory: Path) -> float:
    total_size = 0
    for root, dirs, files in os.walk(directory):
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".")
            and d not in {"__pycache__", "node_modules", "venv", ".venv", ".git"}
        ]
        for file in files:
            try:
                total_size += (Path(root) / file).stat().st_size
            except OSError:
                continue
    return total_size / 1024


def _human_readable_size(size_bytes: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


@router.delete("/uploads/{upload_name}")
async def delete_upload(
    upload_name: str,
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    if ".." in upload_name or "/" in upload_name or "\\" in upload_name:
        raise HTTPException(400, detail="Invalid upload name")

    upload_path = UPLOADS_DIR / upload_name
    try:
        upload_path.resolve().relative_to(UPLOADS_DIR.resolve())
    except ValueError:
        raise HTTPException(403, detail="Access denied")

    # Same 404 whether it doesn't exist or isn't yours - don't reveal
    # which upload names exist.
    if not upload_path.is_dir() or not owns_folder(str(upload_path), owner):
        raise HTTPException(404, detail=f"Upload {upload_name} not found")

    try:
        shutil.rmtree(upload_path, ignore_errors=True)
        delete_folder_owner(str(upload_path))
        return {
            "deleted": True,
            "upload_name": upload_name,
            "message": f"Upload {upload_name} deleted successfully",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete upload: {str(e)}")