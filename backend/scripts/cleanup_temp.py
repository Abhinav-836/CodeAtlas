"""
Cleanup temporary files safely.
"""
import os
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_directory(
    directory: Path,
    days_old: int = 7,
    dry_run: bool = False,
    file_pattern: str = "*",
    is_directory: bool = True
) -> dict:
    """
    Clean up old files or directories.
    
    Args:
        directory: Directory to clean
        days_old: Delete items older than this many days
        dry_run: If True, only show what would be deleted
        file_pattern: Glob pattern for files
        is_directory: True if cleaning directories, False for files
        
    Returns:
        Dictionary with cleanup results
    """
    if not directory.exists():
        logger.info(f"Directory not found: {directory}")
        return {"deleted": 0, "errors": 0, "total_freed_bytes": 0}
    
    cutoff_time = datetime.now() - timedelta(days=days_old)
    results = {
        "deleted": 0,
        "errors": 0,
        "total_freed_bytes": 0,
        "items": []
    }
    
    logger.info(f"Cleaning {directory} (older than {days_old} days)...")
    
    try:
        items = list(directory.iterdir()) if is_directory else list(directory.glob(file_pattern))
    except Exception as e:
        logger.error(f"Error listing items in {directory}: {e}")
        results["errors"] += 1
        return results
    
    for item in items:
        try:
            # Check if we should process this item
            if is_directory and not item.is_dir():
                continue
            if not is_directory and not item.is_file():
                continue
            
            # Get modification time
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            
            if mtime < cutoff_time:
                size_bytes = _get_item_size(item)
                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "size": size_bytes,
                    "size_human": _human_readable_size(size_bytes),
                    "modified": mtime.isoformat(),
                    "age_days": (datetime.now() - mtime).days
                }
                
                results["items"].append(item_info)
                logger.debug(f"Would delete: {item.name} ({item_info['size_human']}, {mtime})")
                
                if not dry_run:
                    try:
                        if is_directory:
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                        
                        results["deleted"] += 1
                        results["total_freed_bytes"] += size_bytes
                        logger.info(f"Deleted: {item.name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to delete {item}: {e}")
                        results["errors"] += 1
                        
        except Exception as e:
            logger.error(f"Error processing {item}: {e}")
            results["errors"] += 1
    
    return results


def cleanup_uploads(days_old: int = 7, dry_run: bool = False) -> dict:
    """Clean up old upload directories."""
    upload_dir = Path("storage/uploads")
    return cleanup_directory(upload_dir, days_old, dry_run, is_directory=True)


def cleanup_reports(days_old: int = 30, dry_run: bool = False) -> dict:
    """Clean up old report files."""
    reports_dir = Path("storage/reports")
    return cleanup_directory(reports_dir, days_old, dry_run, file_pattern="*.json", is_directory=False)


def cleanup_exports(days_old: int = 3, dry_run: bool = False) -> dict:
    """Clean up old export files."""
    exports_dir = Path("storage/exports")
    return cleanup_directory(exports_dir, days_old, dry_run, file_pattern="*", is_directory=False)


def cleanup_temp(days_old: int = 1, dry_run: bool = False) -> dict:
    """Clean up temporary directories."""
    temp_dirs = [
        Path("storage/temp"),
        Path("storage/cache"),
        Path("tmp/codeatlas")
    ]
    
    total_results = {
        "deleted": 0,
        "errors": 0,
        "total_freed_bytes": 0,
        "directories": []
    }
    
    for temp_dir in temp_dirs:
        if temp_dir.exists():
            results = cleanup_directory(temp_dir, days_old, dry_run, is_directory=True)
            total_results["deleted"] += results["deleted"]
            total_results["errors"] += results["errors"]
            total_results["total_freed_bytes"] += results["total_freed_bytes"]
            total_results["directories"].append({
                "path": str(temp_dir),
                **results
            })
    
    return total_results


def _get_item_size(path: Path) -> int:
    """Get size of file or directory in bytes."""
    try:
        if path.is_file():
            return path.stat().st_size
        else:
            total_size = 0
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
    except OSError:
        return 0


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human readable size."""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    for unit in units:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def print_summary(results: dict, name: str, dry_run: bool = False):
    """Print cleanup summary."""
    mode = "Dry run" if dry_run else "Cleanup"
    freed = _human_readable_size(results["total_freed_bytes"])
    
    print(f"\n{'='*60}")
    print(f"{mode} results for {name}:")
    print(f"{'='*60}")
    print(f"Deleted items: {results['deleted']}")
    print(f"Errors: {results['errors']}")
    print(f"Freed space: {freed}")
    
    if results.get("items"):
        print("\nDeleted items:")
        for item in results["items"][:10]:  # Show first 10
            print(f"  - {item['name']} ({item['size_human']}, {item['age_days']} days old)")
        if len(results["items"]) > 10:
            print(f"  ... and {len(results['items']) - 10} more")


def main():
    """Main cleanup script."""
    parser = argparse.ArgumentParser(
        description="Cleanup temporary files for CodeAtlas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all --dry-run      # Show what would be deleted
  %(prog)s --uploads --days 3   # Delete uploads older than 3 days
  %(prog)s --reports --days 30  # Delete reports older than 30 days
        """
    )
    
    parser.add_argument("--days", type=int, default=7,
                       help="Delete files older than N days (default: 7)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be deleted without actually deleting")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    group = parser.add_argument_group("Cleanup targets")
    group.add_argument("--uploads", action="store_true",
                      help="Clean up upload directories")
    group.add_argument("--reports", action="store_true",
                      help="Clean up report files")
    group.add_argument("--exports", action="store_true",
                      help="Clean up export files")
    group.add_argument("--temp", action="store_true",
                      help="Clean up temporary directories")
    group.add_argument("--all", action="store_true",
                      help="Clean up everything")
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    if not any([args.uploads, args.reports, args.exports, args.temp, args.all]):
        parser.print_help()
        return
    
    total_freed = 0
    total_deleted = 0
    
    try:
        if args.all or args.uploads:
            results = cleanup_uploads(args.days, args.dry_run)
            print_summary(results, "Uploads", args.dry_run)
            total_deleted += results["deleted"]
            total_freed += results["total_freed_bytes"]
        
        if args.all or args.reports:
            # Keep reports longer than uploads
            report_days = max(args.days * 4, 30)
            results = cleanup_reports(report_days, args.dry_run)
            print_summary(results, "Reports", args.dry_run)
            total_deleted += results["deleted"]
            total_freed += results["total_freed_bytes"]
        
        if args.all or args.exports:
            # Keep exports for shorter time
            export_days = min(args.days, 3)
            results = cleanup_exports(export_days, args.dry_run)
            print_summary(results, "Exports", args.dry_run)
            total_deleted += results["deleted"]
            total_freed += results["total_freed_bytes"]
        
        if args.all or args.temp:
            results = cleanup_temp(1, args.dry_run)  # Temp files only 1 day
            print_summary(results, "Temp files", args.dry_run)
            total_deleted += results["deleted"]
            total_freed += results["total_freed_bytes"]
        
        # Final summary
        print(f"\n{'='*60}")
        print("TOTAL SUMMARY:")
        print(f"{'='*60}")
        print(f"Total items deleted: {total_deleted}")
        print(f"Total space freed: {_human_readable_size(total_freed)}")
        
        if args.dry_run:
            print("\n⚠️  This was a DRY RUN. No files were actually deleted.")
            print("   Run without --dry-run to perform actual cleanup.")
        
    except KeyboardInterrupt:
        print("\n\nCleanup interrupted by user.")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())