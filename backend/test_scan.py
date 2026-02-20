import os
import queue
from datetime import datetime

import sys
sys.path.insert(0, r"E:\Morshed's deletor\backend")

from database import SessionLocal, ScanResult, init_db

scan_status = {"status": "scanning", "files_processed": 0, "total_found": 0}

def get_category(extension):
    """Categorize files based on extensions."""
    ext = extension.lower()
    if ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv']:
        return "Media"
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']:
        return "Images"
    if ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt']:
        return "Documents"
    if ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
        return "Archives"
    if ext in ['.exe', '.msi', '.app', '.dmg']:
        return "Applications"
    return "Others"

def perform_scan(path: str, min_size_mb: float = 100.0):
    print(f"Starting perform_scan on {path}")
    db = SessionLocal()
    try:
        dirs_to_scan = queue.Queue()
        dirs_to_scan.put(path)
        visited_dirs = set()
        try:
            visited_dirs.add(os.path.realpath(path))
        except OSError:
            pass
        commit_counter = 0

        print("Entering scan loop...")
        while not dirs_to_scan.empty() and scan_status["status"] == "scanning":
            current_path = dirs_to_scan.get()
            print(f"Processing dir: {current_path}")

            try:
                with os.scandir(current_path) as it:
                    for entry in it:
                        try:
                            # Skip hidden files/directories, recycle bin, and symlinks
                            if entry.name.startswith('.') or entry.name.startswith('$') or entry.is_symlink():
                                continue
                        except OSError:
                            continue

                        try:
                            is_dir = entry.is_dir(follow_symlinks=False)
                            is_file = entry.is_file(follow_symlinks=False)
                        except OSError:
                            continue

                        if is_dir:
                            # Skip common system folders completely
                            if current_path == "C:\\" and entry.name in ["Windows", "Program Files", "Program Files (x86)", "System Volume Information", "PerfLogs", "Recovery"]:
                                continue
                            try:
                                real_p = os.path.realpath(entry.path)
                                if real_p not in visited_dirs:
                                    visited_dirs.add(real_p)
                                    dirs_to_scan.put(entry.path)
                            except OSError:
                                pass

                        elif is_file:
                            try:
                                # Quick size check using stat before full extraction
                                stat = entry.stat()
                                size_mb = stat.st_size / (1024 * 1024)

                                if size_mb > min_size_mb:
                                    print(f"Found large file: {entry.path} ({size_mb:.2f} MB)")
                                    # Skip db add for test script
                                    scan_status["total_found"] += 1

                                scan_status["files_processed"] += 1
                                if scan_status["files_processed"] % 1000 == 0:
                                    print(f"Files processed: {scan_status['files_processed']}")
                            except OSError:
                                pass  # Skip unreadable files
            except (OSError, PermissionError) as e:
                print(f"Skipping dir {current_path} due to exact error: {e}")
                pass  # Skip unreadable directories
            
            if scan_status["files_processed"] > 100000:
                print("Stopping early for test")
                break

        if scan_status["status"] == "scanning":
            scan_status["status"] = "completed"
            print("Scan completed successfully")
    except Exception as e:
        scan_status["status"] = f"error: {str(e)}"
        print(f"Error in scan: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    perform_scan("C:\\")
