import os
import shutil
import hashlib
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field

class FileSnapshotRecord(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    action_id: str
    original_path: str
    resulting_path: Optional[str] = None
    snapshot_path: Optional[str] = None
    original_hash: Optional[str] = None
    size_bytes: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    operation_type: str
    restoration_status: str = "PENDING" # PENDING, RESTORED, FAILED, UNAVAILABLE

class TaskSnapshot(BaseModel):
    task_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    files: list[FileSnapshotRecord] = Field(default_factory=list)
    status: str = "ACTIVE"
    rollback_status: Optional[str] = None

class SnapshotManager:
    def __init__(self, snapshot_dir: str = "~/.linuxpilot/snapshots"):
        self.snapshot_dir = Path(snapshot_dir).expanduser().resolve()
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        # In-memory mapping of task_id -> TaskSnapshot
        # In a full system, this goes to the DB.
        self._task_snapshots: Dict[str, TaskSnapshot] = {}

    def _hash_file(self, path: Path) -> str:
        sha256 = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for block in iter(lambda: f.read(65536), b""):
                    sha256.update(block)
            return sha256.hexdigest()
        except Exception:
            return "unknown"

    def get_task_snapshot(self, task_id: str) -> Optional[TaskSnapshot]:
        return self._task_snapshots.get(task_id)

    def get_or_create_task_snapshot(self, task_id: str) -> TaskSnapshot:
        if task_id not in self._task_snapshots:
            self._task_snapshots[task_id] = TaskSnapshot(task_id=task_id)
        return self._task_snapshots[task_id]

    def create_snapshot(self, task_id: str, action_id: str, operation_type: str, file_path: Path, resulting_path: Path = None) -> FileSnapshotRecord:
        """
        Takes a snapshot of a single file before it is modified or deleted.
        Throws exception if the snapshot fails, blocking execution.
        """
        record = FileSnapshotRecord(
            task_id=task_id,
            action_id=action_id,
            operation_type=operation_type,
            original_path=str(file_path),
            resulting_path=str(resulting_path) if resulting_path else None,
            restoration_status="UNAVAILABLE"
        )
        
        task_snap = self.get_or_create_task_snapshot(task_id)
        
        if operation_type == "CREATE":
            # For creation, the file doesn't exist yet, we just track that we created it
            # so rollback can delete it.
            record.restoration_status = "PENDING"
            task_snap.files.append(record)
            return record

        if not file_path.exists():
            raise RuntimeError(f"Cannot snapshot non-existent path: {file_path}")

        if file_path.is_dir():
            # Directories cannot be backed up via file-copy.
            # Record metadata-only snapshot so RENAME/MOVE can still be tracked for rollback.
            record.restoration_status = "METADATA_ONLY"
            task_snap.files.append(record)
            return record

            
        try:
            record.size_bytes = file_path.stat().st_size
            record.original_hash = self._hash_file(file_path)
            
            # Copy to snapshot dir
            snapshot_path = self.snapshot_dir / f"{record.snapshot_id}_{file_path.name}"
            shutil.copy2(file_path, snapshot_path)
            record.snapshot_path = str(snapshot_path)
            record.restoration_status = "PENDING"
            
            task_snap.files.append(record)
        except Exception as e:
            record.restoration_status = f"FAILED: {str(e)}"
            raise RuntimeError(f"Snapshot creation failed: {str(e)}")
            
        return record
