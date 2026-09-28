"""
Checkpoint Manager
Manages per-step checkpoints for rollback capability
"""

import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages checkpoints for rollback capability
    Implements checkpoint-based recovery
    """
    
    def __init__(self, workspace_info: dict):
        self.workspace_info = workspace_info
        self.checkpoints_dir = Path(workspace_info["checkpoints_dir"])
        self.upper_dir = Path(workspace_info["upper_dir"])
        self.work_dir = Path(workspace_info["work_dir"])
    
    def create_checkpoint(self, step_id: str) -> dict:
        """
        Create a checkpoint of the current state
        
        Args:
            step_id: ID of the step to checkpoint after
        
        Returns:
            Checkpoint information
        """
        checkpoint_dir = self.checkpoints_dir / step_id
        checkpoint_dir.mkdir(exist_ok=True)
        
        try:
            # Copy upper directory to checkpoint
            # Use reflink if available for efficiency
            upper_backup = checkpoint_dir / "upper"
            
            if upper_backup.exists():
                shutil.rmtree(upper_backup)
            
            shutil.copytree(
                self.upper_dir,
                upper_backup,
                copy_function=shutil.copy2,
            )
            
            # Record manifest hash for verification
            manifest_hash = self._compute_manifest_hash(upper_backup)
            
            checkpoint_info = {
                "step_id": step_id,
                "checkpoint_dir": str(checkpoint_dir),
                "upper_backup": str(upper_backup),
                "manifest_hash": manifest_hash,
            }
            
            logger.info(f"Created checkpoint for step {step_id}")
            return checkpoint_info
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            raise
    
    def restore_checkpoint(self, step_id: str) -> bool:
        """
        Restore to a previous checkpoint
        
        Args:
            step_id: Step ID to restore to
        
        Returns:
            True if restore successful
        """
        checkpoint_dir = self.checkpoints_dir / step_id
        upper_backup = checkpoint_dir / "upper"
        
        if not upper_backup.exists():
            logger.error(f"Checkpoint {step_id} not found")
            return False
        
        try:
            # Verify manifest hash before restore
            manifest_hash = self._compute_manifest_hash(upper_backup)
            # TODO: Compare with recorded hash
            
            # Unmount overlay first (should be done by caller)
            # Replace upper directory
            if self.upper_dir.exists():
                shutil.rmtree(self.upper_dir)
            
            shutil.copytree(
                upper_backup,
                self.upper_dir,
                copy_function=shutil.copy2,
            )
            
            # Recreate empty work directory
            if self.work_dir.exists():
                shutil.rmtree(self.work_dir)
            self.work_dir.mkdir(exist_ok=True)
            
            logger.info(f"Restored checkpoint for step {step_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore checkpoint: {e}")
            return False
    
    def _compute_manifest_hash(self, directory: Path) -> str:
        """
        Compute a manifest hash of all files in directory
        """
        import hashlib
        
        file_hashes = []
        
        for item in sorted(directory.rglob("*")):
            if item.is_file():
                with open(item, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                rel_path = item.relative_to(directory)
                file_hashes.append(f"{rel_path}:{file_hash}")
        
        manifest = "|".join(file_hashes)
        return hashlib.sha256(manifest.encode()).hexdigest()
    
    def list_checkpoints(self) -> list[str]:
        """List all available checkpoint step IDs"""
        checkpoints = []
        for item in self.checkpoints_dir.iterdir():
            if item.is_dir() and (item / "upper").exists():
                checkpoints.append(item.name)
        return sorted(checkpoints)
    
    def delete_checkpoint(self, step_id: str) -> bool:
        """Delete a checkpoint"""
        checkpoint_dir = self.checkpoints_dir / step_id
        try:
            shutil.rmtree(checkpoint_dir)
            logger.info(f"Deleted checkpoint {step_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete checkpoint: {e}")
            return False
