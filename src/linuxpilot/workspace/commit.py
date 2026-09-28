"""
Commit Manager
Manages write-ahead journal for crash-safe commits
"""

import json
import os
import shutil
from pathlib import Path
from typing import Optional, List
import logging
import hashlib

logger = logging.getLogger(__name__)


class ChangeKind:
    """Kinds of file changes"""
    ADD = "add"
    MODIFY = "modify"
    DELETE = "delete"
    REPLACE_DIR = "replace_dir"


class Change:
    """Represents a single file change"""
    def __init__(
        self,
        kind: str,
        rel_path: str,
        source: Optional[str] = None,
        target: Optional[str] = None,
    ):
        self.kind = kind
        self.rel_path = rel_path
        self.source = source
        self.target = target
    
    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "rel_path": self.rel_path,
            "source": self.source,
            "target": self.target,
        }


class CommitManager:
    """
    Manages write-ahead journal for crash-safe commits
    Implements the "Durability" property of ACID
    """
    
    def __init__(self, workspace_info: dict):
        self.workspace_info = workspace_info
        self.journal_dir = Path(workspace_info["journal_dir"])
        self.trash_dir = Path(workspace_info["trash_dir"])
        self.upper_dir = Path(workspace_info["upper_dir"])
        self.lower_dir = Path(workspace_info["lower_dir"])
        
        self.journal_dir.mkdir(exist_ok=True)
        self.trash_dir.mkdir(exist_ok=True)
    
    def begin_commit(self, task_id: str, changes: List[Change]) -> str:
        """
        Begin a commit with a write-ahead journal
        
        Args:
            task_id: Task identifier
            changes: List of changes to commit
        
        Returns:
            Journal file path
        """
        journal_file = self.journal_dir / f"{task_id}.wal"
        
        journal_data = {
            "task_id": task_id,
            "status": "in_progress",
            "changes": [c.to_dict() for c in changes],
            "current_index": 0,
        }
        
        with open(journal_file, "w") as f:
            json.dump(journal_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        
        logger.info(f"Started commit journal for task {task_id}")
        return str(journal_file)
    
    def apply_change(self, journal_file: str, change: Change) -> bool:
        """
        Apply a single change as part of commit
        
        Args:
            journal_file: Path to journal file
            change: Change to apply
        
        Returns:
            True if successful
        """
        try:
            journal_path = Path(journal_file)
            
            # Load journal
            with open(journal_path, "r") as f:
                journal = json.load(f)
            
            # Log change start
            journal["current_index"] += 1
            with open(journal_path, "w") as f:
                json.dump(journal, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            # Apply the change
            if change.kind == ChangeKind.DELETE:
                self._apply_delete(change)
            elif change.kind == ChangeKind.ADD:
                self._apply_add(change)
            elif change.kind == ChangeKind.MODIFY:
                self._apply_modify(change)
            elif change.kind == ChangeKind.REPLACE_DIR:
                self._apply_replace_dir(change)
            
            # Log change completion
            with open(journal_path, "r") as f:
                journal = json.load(f)
            
            journal["current_index"] += 1
            with open(journal_path, "w") as f:
                json.dump(journal, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply change: {e}")
            return False
    
    def _apply_delete(self, change: Change):
        """Apply a delete change"""
        lower_path = self.lower_dir / change.rel_path
        trash_path = self.trash_dir / change.rel_path
        
        # Move to trash first (atomic on same filesystem)
        trash_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(lower_path), str(trash_path))
    
    def _apply_add(self, change: Change):
        """Apply an add change"""
        upper_path = self.upper_dir / change.rel_path
        lower_path = self.lower_dir / change.rel_path
        
        # Copy from upper to lower
        lower_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(upper_path), str(lower_path))
    
    def _apply_modify(self, change: Change):
        """Apply a modify change"""
        # Move original to trash
        lower_path = self.lower_dir / change.rel_path
        trash_path = self.trash_dir / change.rel_path
        
        trash_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(lower_path), str(trash_path))
        
        # Copy modified version from upper
        upper_path = self.upper_dir / change.rel_path
        shutil.copy2(str(upper_path), str(lower_path))
    
    def _apply_replace_dir(self, change: Change):
        """Apply a directory replacement change"""
        # Move original to trash
        lower_path = self.lower_dir / change.rel_path
        trash_path = self.trash_dir / change.rel_path
        
        trash_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(lower_path), str(trash_path))
        
        # Copy directory from upper
        upper_path = self.upper_dir / change.rel_path
        shutil.copytree(str(upper_path), str(lower_path))
    
    def finalize_commit(self, journal_file: str) -> bool:
        """
        Mark the commit as complete in the journal
        
        Args:
            journal_file: Path to journal file
        
        Returns:
            True if successful
        """
        try:
            journal_path = Path(journal_file)
            
            with open(journal_path, "r") as f:
                journal = json.load(f)
            
            journal["status"] = "completed"
            
            with open(journal_path, "w") as f:
                json.dump(journal, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            logger.info(f"Finalized commit for task {journal['task_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to finalize commit: {e}")
            return False
    
    def rollback_commit(self, journal_file: str) -> bool:
        """
        Rollback an incomplete commit using trash
        
        Args:
            journal_file: Path to journal file
        
        Returns:
            True if successful
        """
        try:
            journal_path = Path(journal_file)
            
            with open(journal_path, "r") as f:
                journal = json.load(f)
            
            # Restore from trash in reverse order
            for change_dict in reversed(journal["changes"]):
                if journal["current_index"] <= 0:
                    break
                
                change = Change(
                    kind=change_dict["kind"],
                    rel_path=change_dict["rel_path"],
                )
                
                trash_path = self.trash_dir / change.rel_path
                lower_path = self.lower_dir / change.rel_path
                
                if trash_path.exists():
                    # Restore from trash
                    if lower_path.exists():
                        if lower_path.is_dir():
                            shutil.rmtree(str(lower_path))
                        else:
                            lower_path.unlink()
                    
                    trash_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(trash_path), str(lower_path))
                
                journal["current_index"] -= 1
            
            # Mark as rolled back
            journal["status"] = "rolled_back"
            
            with open(journal_path, "w") as f:
                json.dump(journal, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            logger.info(f"Rolled back commit for task {journal['task_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback commit: {e}")
            return False
    
    def recover(self) -> List[str]:
        """
        Recover from incomplete commits on startup
        Checks for in-progress journals and rolls them back
        
        Returns:
            List of recovered task IDs
        """
        recovered = []
        
        for journal_file in self.journal_dir.glob("*.wal"):
            try:
                with open(journal_file, "r") as f:
                    journal = json.load(f)
                
                if journal["status"] == "in_progress":
                    logger.warning(f"Found incomplete commit for task {journal['task_id']}")
                    self.rollback_commit(str(journal_file))
                    recovered.append(journal["task_id"])
                    
            except Exception as e:
                logger.error(f"Failed to recover journal {journal_file}: {e}")
        
        return recovered
