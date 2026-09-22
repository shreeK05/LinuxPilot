import os
import shutil
import hashlib
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class FileSnapshotRecord(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    action_id: str
    original_path: str
    snapshot_path: Optional[str] = None
    original_hash: Optional[str] = None
    size_bytes: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    operation_type: str
    restoration_status: str = "PENDING" # PENDING, RESTORED, FAILED, UNAVAILABLE

class SnapshotManager:
    def __init__(self, snapshot_dir: str = "~/.linuxpilot/snapshots"):
        self.snapshot_dir = Path(snapshot_dir).expanduser().resolve()
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def _hash_file(self, path: Path) -> str:
        sha256 = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for block in iter(lambda: f.read(65536), b""):
                    sha256.update(block)
            return sha256.hexdigest()
        except Exception:
            return "unknown"

    def create_snapshot(self, task_id: str, action_id: str, operation_type: str, file_path: Path) -> FileSnapshotRecord:
        """
        Takes a snapshot of a single file before it is modified or deleted.
        """
        record = FileSnapshotRecord(
            task_id=task_id,
            action_id=action_id,
            operation_type=operation_type,
            original_path=str(file_path),
            restoration_status="UNAVAILABLE"
        )
        
        if not file_path.exists() or not file_path.is_file():
            # If it's a directory or doesn't exist, we can't snapshot it easily in Phase 3
            # We'll just return a record saying UNAVAILABLE for contents, but we have the path.
            return record
            
        try:
            record.size_bytes = file_path.stat().st_size
            record.original_hash = self._hash_file(file_path)
            
            # Copy to snapshot dir
            snapshot_path = self.snapshot_dir / f"{record.snapshot_id}_{file_path.name}"
            shutil.copy2(file_path, snapshot_path)
            record.snapshot_path = str(snapshot_path)
            record.restoration_status = "PENDING"
            
        except Exception as e:
            record.restoration_status = f"FAILED: {str(e)}"
            
        return record
