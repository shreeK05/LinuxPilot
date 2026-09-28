"""
Diff Analyzer
Analyzes changes in the overlay layer for diff review
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ChangeKind:
    """Kinds of file changes"""
    ADD = "add"
    MODIFY = "modify"
    DELETE = "delete"
    REPLACE_DIR = "replace_dir"


class DiffAnalyzer:
    """
    Analyzes changes in the overlay layer
    Provides git-like diff for desktop changes
    """
    
    def __init__(self, workspace_info: dict):
        self.workspace_info = workspace_info
        self.upper_dir = Path(workspace_info["upper_dir"])
        self.lower_dir = Path(workspace_info["lower_dir"])
    
    def analyze(self) -> List[Dict[str, Any]]:
        """
        Analyze changes in the upper layer
        
        Returns:
            List of change dictionaries
        """
        changes = []
        
        # Walk the upper directory
        for item in self.upper_dir.rglob("*"):
            if not item.exists():
                continue
            
            rel_path = item.relative_to(self.upper_dir)
            lower_path = self.lower_dir / rel_path
            
            # Check for whiteout (deleted file)
            if item.is_char_device() and item.stat().st_rdev == 0:
                changes.append({
                    "kind": ChangeKind.DELETE,
                    "path": str(rel_path),
                    "description": f"Deleted: {rel_path}",
                })
                continue
            
            # Check for opaque directory (replaced directory)
            if item.is_dir():
                xattr = self._get_xattr(item, "trusted.overlay.opaque")
                if xattr == "y" or xattr == b"y":
                    changes.append({
                        "kind": ChangeKind.REPLACE_DIR,
                        "path": str(rel_path),
                        "description": f"Replaced directory: {rel_path}",
                    })
                    continue
            
            # Regular file or directory
            if item.is_file():
                if lower_path.exists():
                    changes.append({
                        "kind": ChangeKind.MODIFY,
                        "path": str(rel_path),
                        "description": f"Modified: {rel_path}",
                    })
                else:
                    changes.append({
                        "kind": ChangeKind.ADD,
                        "path": str(rel_path),
                        "description": f"Added: {rel_path}",
                    })
            elif item.is_dir():
                if not lower_path.exists():
                    changes.append({
                        "kind": ChangeKind.ADD,
                        "path": str(rel_path),
                        "description": f"Added directory: {rel_path}",
                    })
        
        # Check for deleted files that might not have whiteouts
        # (walk lower and check if missing in upper)
        for item in self.lower_dir.rglob("*"):
            if not item.exists():
                continue
            
            rel_path = item.relative_to(self.lower_dir)
            upper_path = self.upper_dir / rel_path
            
            if not upper_path.exists():
                # Check if this was explicitly deleted (has whiteout)
                whiteout_path = self.upper_dir / rel_path
                if not whiteout_path.exists():
                    changes.append({
                        "kind": ChangeKind.DELETE,
                        "path": str(rel_path),
                        "description": f"Deleted: {rel_path}",
                    })
        
        return sorted(changes, key=lambda x: x["path"])
    
    def _get_xattr(self, path: Path, attr: str) -> str:
        """
        Get extended attribute from a file
        """
        try:
            import xattr
            return xattr.getxattr(str(path), attr)
        except ImportError:
            # xattr not available, return None
            return None
        except Exception:
            return None
    
    def get_summary(self, changes: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Get a summary of changes
        
        Returns:
            Dictionary with counts by kind
        """
        summary = {
            ChangeKind.ADD: 0,
            ChangeKind.MODIFY: 0,
            ChangeKind.DELETE: 0,
            ChangeKind.REPLACE_DIR: 0,
        }
        
        for change in changes:
            summary[change["kind"]] += 1
        
        return summary
    
    def format_diff(self, changes: List[Dict[str, Any]]) -> str:
        """
        Format changes as a human-readable diff
        
        Returns:
            Formatted diff string
        """
        lines = []
        
        for change in changes:
            kind_symbol = {
                ChangeKind.ADD: "+",
                ChangeKind.MODIFY: "~",
                ChangeKind.DELETE: "-",
                ChangeKind.REPLACE_DIR: "R",
            }
            
            symbol = kind_symbol.get(change["kind"], "?")
            lines.append(f"{symbol} {change['description']}")
        
        return "\n".join(lines)
