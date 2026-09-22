from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class FileSnapshotRecord(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: str  # e.g., "WRITE", "DELETE", "RENAME", "MOVE", "CREATE"
    original_path: str
    resulting_path: Optional[str] = None
    snapshot_path: Optional[str] = None
    hash_sha256: Optional[str] = None
    status: str = "ACTIVE"  # ACTIVE, RESTORED, FAILED
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class TaskSnapshot(BaseModel):
    task_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    files: List[FileSnapshotRecord] = Field(default_factory=list)
    status: str = "ACTIVE"  # ACTIVE, COMMITTED, ROLLED_BACK, PARTIAL_ROLLBACK
    rollback_status: Optional[str] = None
