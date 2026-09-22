import shutil
import os
from pathlib import Path
from typing import Dict, Any
from app.adapters.linux.filesystem.snapshot import TaskSnapshot, FileSnapshotRecord
from app.adapters.linux.filesystem.security import FilesystemSecurityPolicy

class RollbackError(Exception):
    pass

class RollbackManager:
    """
    Restores files from application-level TaskSnapshots securely.
    """
    def __init__(self, allowed_roots=None):
        if allowed_roots is None:
            # For testing and Phase 3/7, fallback to allowing the workspace root
            # In a real environment, this would be injected via configuration
            allowed_roots = [str(Path("~/.linuxpilot/workspace").expanduser().resolve())]
        self.security = FilesystemSecurityPolicy(allowed_roots)

    def rollback_task(self, task_snapshot: TaskSnapshot) -> Dict[str, Any]:
        """
        Attempts to rollback all files in a TaskSnapshot.
        Returns a dict of successful and failed rollbacks to report partial failures.
        """
        if task_snapshot.status in ["ROLLED_BACK", "PARTIAL_ROLLBACK"]:
            raise RollbackError("Task snapshot already rolled back.")
            
        successes = []
        failures = []
        
        # We process in reverse order to unwind operations sequentially
        for file_snap in reversed(task_snapshot.files):
            try:
                self._rollback_file(file_snap)
                successes.append(file_snap.original_path)
            except Exception as e:
                failures.append({"path": file_snap.original_path, "error": str(e)})
                
        if failures:
            task_snapshot.status = "PARTIAL_ROLLBACK"
            task_snapshot.rollback_status = f"Failed to restore {len(failures)} files."
        else:
            task_snapshot.status = "ROLLED_BACK"
            task_snapshot.rollback_status = "SUCCESS"
            
        return {
            "successes": successes,
            "failures": failures
        }

    def _rollback_file(self, snapshot: FileSnapshotRecord):
        if snapshot.restoration_status != "PENDING":
            raise RollbackError(f"Rollback unavailable: {snapshot.restoration_status}")
            
        original_path = self.security.validate_path(snapshot.original_path)
        
        if snapshot.operation_type == "CREATE":
            # The file didn't exist before, so rollback means deleting it
            if original_path.exists():
                if original_path.is_file():
                    original_path.unlink()
                else:
                    raise RollbackError(f"Cannot rollback CREATE on non-file path {original_path}")
            snapshot.restoration_status = "RESTORED"
            return
            
        # For WRITE, DELETE, MOVE, RENAME
        if not snapshot.snapshot_path:
             raise RollbackError("No snapshot path available.")
             
        snapshot_path = Path(snapshot.snapshot_path)
        
        if not snapshot_path.exists():
            raise RollbackError(f"Snapshot file missing at {snapshot_path}")
            
        # If it was a MOVE/RENAME, delete the resulting path
        if snapshot.operation_type in ["MOVE", "RENAME"] and snapshot.resulting_path:
            res_path = self.security.validate_path(snapshot.resulting_path)
            if res_path.exists() and res_path.is_file():
                res_path.unlink()
                
        # Ensure parent directories exist
        original_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Restore original file
        shutil.copy2(snapshot_path, original_path)
        snapshot.restoration_status = "RESTORED"
