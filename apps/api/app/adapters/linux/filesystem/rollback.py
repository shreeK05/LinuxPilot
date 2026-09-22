import shutil
import os
from pathlib import Path
from app.adapters.linux.filesystem.snapshot import FileSnapshotRecord

class RollbackError(Exception):
    pass

class RollbackManager:
    """
    Restores files from application-level snapshots.
    """
    def rollback(self, snapshot: FileSnapshotRecord) -> bool:
        if snapshot.restoration_status != "PENDING" or not snapshot.snapshot_path:
            raise RollbackError(f"Rollback unavailable for this snapshot: {snapshot.restoration_status}")
            
        original_path = Path(snapshot.original_path)
        snapshot_path = Path(snapshot.snapshot_path)
        
        if not snapshot_path.exists():
            raise RollbackError(f"Snapshot file missing at {snapshot_path}")
            
        try:
            # Ensure parent directories exist
            original_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If operation was DELETE or OVERWRITE, restore from snapshot
            # If operation was RENAME/MOVE, we should ideally move it back, but 
            # our snapshot system just takes a copy before any operation. 
            # So copying it back always restores the pre-operation state.
            shutil.copy2(snapshot_path, original_path)
            snapshot.restoration_status = "RESTORED"
            return True
            
        except Exception as e:
            snapshot.restoration_status = f"FAILED: {str(e)}"
            raise RollbackError(f"Failed to restore snapshot: {str(e)}")
