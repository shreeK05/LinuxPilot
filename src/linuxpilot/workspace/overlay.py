"""
Overlay Manager
Manages overlayfs mounts for transactional file operations
"""

import os
import subprocess
from pathlib import Path
from typing import Optional
import logging

from linuxpilot.config import settings

logger = logging.getLogger(__name__)


class OverlayManager:
    """
    Manages overlayfs mounts for transactional file operations
    Implements the "Atomicity" property of ACID
    """
    
    def __init__(self, workspace_base: Path = None, real_data_base: Path = None):
        self.workspace_base = workspace_base or settings.WORKSPACE_BASE
        self.real_data_base = real_data_base or settings.REAL_DATA_BASE
        
        # Ensure workspace base exists
        self.workspace_base.mkdir(parents=True, exist_ok=True)
    
    def create_task_workspace(self, task_id: str, allowed_path: str) -> dict:
        """
        Create a workspace for a specific task
        
        Args:
            task_id: Unique task identifier
            allowed_path: Path to the real data directory to overlay
        
        Returns:
            Dictionary with workspace paths
        """
        task_dir = self.workspace_base / "tasks" / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Create overlay directories
        upper_dir = task_dir / "upper"
        work_dir = task_dir / "work"
        checkpoints_dir = task_dir / "checkpoints"
        journal_dir = task_dir / "journal"
        trash_dir = task_dir / "trash"
        
        for d in [upper_dir, work_dir, checkpoints_dir, journal_dir, trash_dir]:
            d.mkdir(exist_ok=True)
        
        # Get absolute path to real data
        real_path = Path(allowed_path).expanduser().resolve()
        
        # Mount point for the overlay
        mount_point = task_dir / "mount"
        mount_point.mkdir(exist_ok=True)
        
        workspace_info = {
            "task_id": task_id,
            "task_dir": str(task_dir),
            "upper_dir": str(upper_dir),
            "work_dir": str(work_dir),
            "checkpoints_dir": str(checkpoints_dir),
            "journal_dir": str(journal_dir),
            "trash_dir": str(trash_dir),
            "lower_dir": str(real_path),
            "mount_point": str(mount_point),
            "mounted": False,
        }
        
        logger.info(f"Created workspace for task {task_id}")
        return workspace_info
    
    def mount_overlay(self, workspace_info: dict) -> bool:
        """
        Mount the overlayfs
        
        Args:
            workspace_info: Workspace information from create_task_workspace
        
        Returns:
            True if mount successful
        """
        if workspace_info["mounted"]:
            logger.warning("Overlay already mounted")
            return True
        
        try:
            # Build mount command
            lower = workspace_info["lower_dir"]
            upper = workspace_info["upper_dir"]
            work = workspace_info["work_dir"]
            mount_point = workspace_info["mount_point"]
            
            cmd = [
                "mount",
                "-t", "overlay",
                "overlay",
                "-o",
                f"lowerdir={lower},upperdir={upper},workdir={work}",
                mount_point,
            ]
            
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            
            workspace_info["mounted"] = True
            logger.info(f"Mounted overlay at {mount_point}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to mount overlay: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error mounting overlay: {e}")
            return False
    
    def unmount_overlay(self, workspace_info: dict) -> bool:
        """
        Unmount the overlayfs
        
        Args:
            workspace_info: Workspace information
        
        Returns:
            True if unmount successful
        """
        if not workspace_info["mounted"]:
            logger.warning("Overlay not mounted")
            return True
        
        try:
            mount_point = workspace_info["mount_point"]
            
            cmd = ["umount", mount_point]
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            
            workspace_info["mounted"] = False
            logger.info(f"Unmounted overlay from {mount_point}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to unmount overlay: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error unmounting overlay: {e}")
            return False
    
    def discard_task(self, workspace_info: dict) -> bool:
        """
        Discard all changes for a task (delete upper layer)
        This implements the "discard" operation - real data never touched
        
        Args:
            workspace_info: Workspace information
        
        Returns:
            True if discard successful
        """
        try:
            # Unmount first
            if workspace_info["mounted"]:
                self.unmount_overlay(workspace_info)
            
            # Delete the entire task directory
            task_dir = Path(workspace_info["task_dir"])
            
            # Remove mount point first
            mount_point = Path(workspace_info["mount_point"])
            if mount_point.exists():
                mount_point.rmdir()
            
            # Remove task directory
            import shutil
            shutil.rmtree(task_dir)
            
            logger.info(f"Discarded task {workspace_info['task_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to discard task: {e}")
            return False
    
    def get_upper_size(self, workspace_info: dict) -> int:
        """
        Get the size of the upper layer (changes only)
        
        Args:
            workspace_info: Workspace information
        
        Returns:
            Size in bytes
        """
        try:
            upper_dir = Path(workspace_info["upper_dir"])
            total_size = 0
            
            for item in upper_dir.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
            
            return total_size
            
        except Exception as e:
            logger.error(f"Failed to calculate upper size: {e}")
            return 0
