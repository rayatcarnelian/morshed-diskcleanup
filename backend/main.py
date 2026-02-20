from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from datetime import datetime
import time
import queue
from database import SessionLocal, ScanResult, init_db

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("../frontend/index.html")

# Initialize Database
init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_safe_path(filepath):
    """Check if a file is safe to automatically delete. Only temp directories are considered safe."""
    import tempfile
    
    safe_dirs = [
        tempfile.gettempdir().lower(),
        os.environ.get('TEMP', '').lower(),
        os.environ.get('TMP', '').lower(),
    ]
    # Filter out empty strings
    safe_dirs = [os.path.normpath(d) + os.sep for d in safe_dirs if d]

    filepath_lower = os.path.normpath(filepath).lower()
    for safe_dir in safe_dirs:
        if filepath_lower.startswith(safe_dir):
            return True
            
    # Fallback to standard explicit temp patterns just in case
    if "\\windows\\temp\\" in filepath_lower or "\\appdata\\local\\temp\\" in filepath_lower:
         return True
         
    return False

# Global scan status
scan_status = {"status": "idle", "files_processed": 0, "total_found": 0}

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
    """Background task to scan directory."""
    db = SessionLocal()
    try:
        dirs_to_scan = queue.Queue()
        dirs_to_scan.put(path)
        visited_dirs = set()
        
        try:
            visited_dirs.add(os.path.normcase(os.path.abspath(path)))
        except OSError:
            pass
        commit_counter = 0

        while not dirs_to_scan.empty() and scan_status["status"] == "scanning":
            current_path = dirs_to_scan.get()

            try:
                with os.scandir(current_path) as it:
                    for entry in it:
                        try:
                            # Skip hidden files/directories, recycle bin, and symlinks
                            is_link = entry.is_symlink()
                            if hasattr(entry, 'is_junction'):
                                is_link = is_link or entry.is_junction()
                                
                            if is_link or entry.name.startswith('.') or entry.name.startswith('$'):
                                continue
                                
                            is_dir = entry.is_dir(follow_symlinks=False)
                            is_file = entry.is_file(follow_symlinks=False)
                        except OSError:
                            continue

                        if is_dir:
                            # Skip common system folders completely
                            norm_curr = os.path.normcase(os.path.abspath(current_path))
                            if norm_curr in ["c:\\", "c:"]:
                                if entry.name.upper() in ["WINDOWS", "PROGRAM FILES", "PROGRAM FILES (X86)", "SYSTEM VOLUME INFORMATION", "PERFLOGS", "RECOVERY", "$RECYCLE.BIN"]:
                                    continue
                            try:
                                # Use normcase instead of slow realpath
                                norm_p = os.path.normcase(os.path.abspath(entry.path))
                                if norm_p not in visited_dirs:
                                    visited_dirs.add(norm_p)
                                    dirs_to_scan.put(entry.path)
                            except OSError:
                                pass

                        elif is_file:
                            try:
                                # Quick size check using stat before full extraction
                                stat = entry.stat()
                                size_mb = stat.st_size / (1024 * 1024)

                                if size_mb > min_size_mb:
                                    file_entry = ScanResult(
                                        filepath=entry.path,
                                        filename=entry.name,
                                        filesize_mb=round(size_mb, 2),
                                        filetype=os.path.splitext(entry.name)[1],
                                        category=get_category(os.path.splitext(entry.name)[1]),
                                        last_modified=datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                                        is_safe_to_delete=is_safe_path(entry.path)
                                    )
                                    db.add(file_entry)
                                    scan_status["total_found"] += 1

                                    # Batch commits
                                    commit_counter += 1
                                    if commit_counter >= 50:
                                        db.commit()
                                        commit_counter = 0

                                scan_status["files_processed"] += 1
                            except OSError:
                                pass  # Skip unreadable files
            except (OSError, PermissionError):
                pass  # Skip unreadable directories

        if commit_counter > 0:
            db.commit()
            
        if scan_status["status"] == "scanning":
            scan_status["status"] = "completed"
    except Exception as e:
        scan_status["status"] = f"error: {str(e)}"
    finally:
        db.close()

@app.post("/scan")
def scan_directory(
    path: str, 
    background_tasks: BackgroundTasks, 
    min_size_mb: float = 100.0, 
    db: Session = Depends(get_db)
):
    """Starts a directory scan in the background."""
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Path does not exist")

    # Reset status
    if scan_status["status"] == "scanning":
        return {"message": "A scan is already in progress.", "status": "scanning"}

    scan_status["status"] = "scanning"
    scan_status["files_processed"] = 0
    scan_status["total_found"] = 0
    
    # Clear previous scan results
    db.query(ScanResult).delete()
    db.commit()
    
    background_tasks.add_task(perform_scan, path, min_size_mb)
    
    return {"message": "Scan started in background", "status": "scanning"}

@app.get("/status")
def get_scan_status():
    """Returns the current scan status."""
    return scan_status

@app.get("/files")
def get_files(db: Session = Depends(get_db)):
    """Returns all scanned files sorted by size (descending)."""
    return db.query(ScanResult).order_by(ScanResult.filesize_mb.desc()).all()

import subprocess

@app.post("/open/{file_id}")
def open_file_location(file_id: int, db: Session = Depends(get_db)):
    """Opens the file's location in Windows Explorer."""
    file_record = db.query(ScanResult).filter(ScanResult.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found in database")

    try:
        if os.path.exists(file_record.filepath):
            # Tell Windows Explorer to open the folder and highlight the file
            subprocess.run(['explorer', '/select,', file_record.filepath])
            return {"message": "Opened file location"}
        else:
            raise HTTPException(status_code=404, detail="File no longer exists on disk")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    """Deletes a file by ID."""
    file_record = db.query(ScanResult).filter(ScanResult.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found in database")

    try:
        if os.path.exists(file_record.filepath):
            os.remove(file_record.filepath)
        
        db.delete(file_record)
        db.commit()
        return {"message": f"Successfully deleted {file_record.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete-all-safe")
def delete_all_safe(db: Session = Depends(get_db)):
    """Deletes all safe files from the scan results."""
    safe_files = db.query(ScanResult).filter(ScanResult.is_safe_to_delete == True).all()
    if not safe_files:
        return {"message": "No safe files found to delete."}

    deleted_count = 0
    try:
        for file_record in safe_files:
            if os.path.exists(file_record.filepath):
                os.remove(file_record.filepath)
            db.delete(file_record)
            deleted_count += 1
        
        db.commit()
        return {"message": f"Successfully deleted {deleted_count} safe files."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting files after {deleted_count} deletions: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
