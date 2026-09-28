"""
Invariant Checker
Checks global invariants after each step
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from linuxpilot.models import ExecutionContext
from linuxpilot.config import settings

logger = logging.getLogger(__name__)


class InvariantChecker:
    """
    Checks global invariants after each step
    Ensures system consistency properties
    """
    
    def __init__(self, context: ExecutionContext):
        self.context = context
        self.baseline_manifest: Optional[Dict[str, str]] = None
    
    def initialize_baseline(self):
        """Initialize the baseline manifest of real data"""
        if self.context.real_data_path:
            self.baseline_manifest = self._compute_manifest(
                Path(self.context.real_data_path)
            )
            logger.info("Initialized baseline manifest")
    
    def check_all(self, workspace_info: Optional[Dict] = None) -> tuple[bool, Optional[str]]:
        """
        Check all global invariants
        
        Args:
            workspace_info: Optional workspace information for overlay checks
        
        Returns:
            (is_valid, error_message)
        """
        # I1: Real data unchanged during task
        if not self._check_i1_real_data_unchanged():
            return False, "I1 violated: Real data modified during task"
        
        # I2: No content lost unless planned
        if not self._check_i2_no_content_lost(workspace_info):
            return False, "I2 violated: Content lost unexpectedly"
        
        # I3: Writes confined to allowed roots
        if not self._check_i3_path_confinement(workspace_info):
            return False, "I3 violated: Write outside allowed roots"
        
        # I4: Resources within bounds
        if not self._check_i4_resource_bounds(workspace_info):
            return False, "I4 violated: Resource bounds exceeded"
        
        # I5: No unexpected seccomp violations
        # This would be checked by the sandbox manager
        # For now, we'll assume it's OK
        
        return True, None
    
    def _check_i1_real_data_unchanged(self) -> bool:
        """
        I1: Real data unchanged during task
        Verify that the lower layer (real data) hasn't been modified
        """
        if not self.context.real_data_path or not self.baseline_manifest:
            return True  # Can't check without baseline
        
        current_manifest = self._compute_manifest(Path(self.context.real_data_path))
        return current_manifest == self.baseline_manifest
    
    def _check_i2_no_content_lost(self, workspace_info: Optional[Dict]) -> bool:
        """
        I2: No content lost unless planned
        Check that all hashes in lower appear in merged view unless deleted
        """
        if not workspace_info:
            return True  # Can't check without workspace
        
        # This is a simplified check
        # In production, we'd need to:
        # 1. Hash all files in lower
        # 2. Hash all files in merged view (upper + lower)
        # 3. Ensure every lower hash appears in merged view
        # 4. Unless the file was explicitly deleted in the plan
        
        return True  # Placeholder
    
    def _check_i3_path_confinement(self, workspace_info: Optional[Dict]) -> bool:
        """
        I3: Writes confined to allowed roots
        Check that all paths in upper diff are within allowed roots
        """
        if not workspace_info:
            return True
        
        try:
            from linuxpilot.workspace.diff import DiffAnalyzer
            
            diff_analyzer = DiffAnalyzer(workspace_info)
            changes = diff_analyzer.analyze()
            
            for change in changes:
                path = Path(change["path"])
                
                # Check if within allowed roots
                allowed = False
                for root in self.context.allowed_roots:
                    expanded_root = Path(root).expanduser().resolve()
                    # This is a simplified check - in production we'd need to check
                    # against the actual lower directory path
                    if str(path).startswith(str(expanded_root)):
                        allowed = True
                        break
                
                if not allowed:
                    logger.warning(f"Path confinement violation: {path}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Path confinement check failed: {e}")
            return False
    
    def _check_i4_resource_bounds(self, workspace_info: Optional[Dict]) -> bool:
        """
        I4: Resources within bounds
        Check memory, PIDs, and disk usage
        """
        if not workspace_info:
            return True
        
        try:
            from linuxpilot.workspace.overlay import OverlayManager
            
            overlay_mgr = OverlayManager()
            upper_size = overlay_mgr.get_upper_size(workspace_info)
            
            # Check upper size (should be reasonable)
            max_upper_size = 1024 * 1024 * 1024  # 1GB
            if upper_size > max_upper_size:
                logger.warning(f"Upper size exceeded: {upper_size} bytes")
                return False
            
            # Check cgroup stats if available
            if "task_id" in workspace_info:
                from linuxpilot.sandbox.cgroups import CgroupManager
                cgroup_mgr = CgroupManager()
                stats = cgroup_mgr.get_stats(workspace_info["task_id"])
                
                if stats:
                    # Check memory usage
                    if "memory_peak_bytes" in stats:
                        memory_limit = settings.DEFAULT_MEMORY_LIMIT_MB * 1024 * 1024
                        if stats["memory_peak_bytes"] > memory_limit:
                            logger.warning(f"Memory limit exceeded: {stats['memory_peak_bytes']}")
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Resource bounds check failed: {e}")
            return False
    
    def _compute_manifest(self, directory: Path) -> Dict[str, str]:
        """
        Compute a content-addressed manifest of a directory
        Maps file paths to SHA-256 hashes
        """
        manifest = {}
        
        if not directory.exists():
            return manifest
        
        for item in sorted(directory.rglob("*")):
            if item.is_file():
                with open(item, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                rel_path = item.relative_to(directory)
                manifest[str(rel_path)] = file_hash
        
        return manifest
