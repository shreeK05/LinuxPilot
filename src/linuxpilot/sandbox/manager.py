"""
Sandbox Manager
Main sandbox supervisor combining namespaces, cgroups, and seccomp
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from linuxpilot.sandbox.cgroups import CgroupManager
from linuxpilot.sandbox.namespaces import NamespaceManager
from linuxpilot.sandbox.seccomp import SeccompProfile
from linuxpilot.config import settings

logger = logging.getLogger(__name__)


class SandboxManager:
    """
    Main sandbox supervisor
    Combines namespaces, cgroups v2, and seccomp for isolation
    Implements the "Isolation" property of ACID
    """
    
    def __init__(self):
        self.cgroup_mgr = CgroupManager()
        self.namespace_mgr = NamespaceManager()
        self.seccomp_profile = SeccompProfile()
        
        self.active_sandboxes: Dict[str, Dict[str, Any]] = {}
    
    def create_sandbox(
        self,
        task_id: str,
        profile: str = "app-gui",
        memory_limit_mb: Optional[int] = None,
        cpu_limit_percent: Optional[int] = None,
        pids_limit: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a sandbox for a task
        
        Args:
            task_id: Task identifier
            profile: Sandbox profile (helper-strict, app-gui, app-browser)
            memory_limit_mb: Memory limit in MB
            cpu_limit_percent: CPU limit as percentage
            pids_limit: Process count limit
        
        Returns:
            Sandbox information or None if failed
        """
        try:
            # Set limits from defaults if not provided
            memory_limit = memory_limit_mb or settings.DEFAULT_MEMORY_LIMIT_MB
            cpu_limit = cpu_limit_percent or settings.DEFAULT_CPU_LIMIT_PERCENT
            pids_limit_val = pids_limit or settings.DEFAULT_PIDS_LIMIT
            
            # Create cgroup
            cgroup_path = self.cgroup_mgr.create_cgroup(
                task_id,
                memory_limit_mb=memory_limit,
                cpu_limit_percent=cpu_limit,
                pids_limit=pids_limit_val,
            )
            
            if not cgroup_path:
                logger.error(f"Failed to create cgroup for task {task_id}")
                return None
            
            sandbox_info = {
                "task_id": task_id,
                "profile": profile,
                "cgroup_path": cgroup_path,
                "memory_limit_mb": memory_limit,
                "cpu_limit_percent": cpu_limit,
                "pids_limit": pids_limit_val,
                "active": True,
            }
            
            self.active_sandboxes[task_id] = sandbox_info
            logger.info(f"Created sandbox for task {task_id} with profile {profile}")
            return sandbox_info
            
        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            return None
    
    def destroy_sandbox(self, task_id: str) -> bool:
        """
        Destroy a sandbox and clean up resources
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if successful
        """
        try:
            if task_id not in self.active_sandboxes:
                logger.warning(f"Sandbox {task_id} not found")
                return True
            
            sandbox_info = self.active_sandboxes[task_id]
            
            # Kill all processes in cgroup
            self.cgroup_mgr.kill_cgroup(task_id)
            
            # Remove cgroup
            self.cgroup_mgr.remove_cgroup(task_id)
            
            sandbox_info["active"] = False
            del self.active_sandboxes[task_id]
            
            logger.info(f"Destroyed sandbox for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to destroy sandbox: {e}")
            return False
    
    def run_in_sandbox(
        self,
        task_id: str,
        command: list[str],
        profile: str = "app-gui",
        workspace_path: Optional[str] = None,
    ) -> Optional[subprocess.Popen]:
        """
        Run a command inside a sandbox
        
        Args:
            task_id: Task identifier
            command: Command to run
            profile: Sandbox profile
            workspace_path: Path to workspace (for overlay mount)
        
        Returns:
            Process object or None if failed
        """
        try:
            if task_id not in self.active_sandboxes:
                logger.error(f"Sandbox {task_id} not active")
                return None
            
            sandbox_info = self.active_sandboxes[task_id]
            
            # In a real implementation, this would:
            # 1. Fork a child process
            # 2. In child: unshare namespaces
            # 3. In child: mount overlayfs
            # 4. In child: load seccomp profile
            # 5. In child: add to cgroup
            # 6. In child: exec command
            
            # For now, we'll use a simplified approach with the helper-strict profile
            # In production, this needs to be a proper supervisor running as root
            
            if profile == "helper-strict":
                # Run with strict seccomp
                # This would need to be done in a subprocess with seccomp loaded
                pass
            
            # Add process to cgroup
            # This would be done in the child before exec
            
            logger.info(f"Running command in sandbox {task_id}: {' '.join(command)}")
            
            # Placeholder - in production, this would use the namespace manager
            proc = subprocess.Popen(command)
            
            # Add to cgroup (simplified)
            try:
                cgroup_procs = Path(sandbox_info["cgroup_path"]) / "cgroup.procs"
                with open(cgroup_procs, "a") as f:
                    f.write(str(proc.pid))
            except Exception as e:
                logger.warning(f"Failed to add process to cgroup: {e}")
            
            return proc
            
        except Exception as e:
            logger.error(f"Failed to run command in sandbox: {e}")
            return None
    
    def get_sandbox_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a sandbox
        
        Args:
            task_id: Task identifier
        
        Returns:
            Sandbox status or None if not found
        """
        if task_id not in self.active_sandboxes:
            return None
        
        sandbox_info = self.active_sandboxes[task_id]
        
        # Get cgroup stats
        stats = self.cgroup_mgr.get_stats(task_id)
        
        return {
            **sandbox_info,
            "stats": stats,
        }
    
    def cleanup_dead_sandboxes(self):
        """Clean up any leaked sandboxes (janitor function)"""
        for task_id in list(self.active_sandboxes.keys()):
            try:
                stats = self.cgroup_mgr.get_stats(task_id)
                if not stats or stats.get("pids", 0) == 0:
                    logger.info(f"Cleaning up dead sandbox {task_id}")
                    self.destroy_sandbox(task_id)
            except Exception as e:
                logger.warning(f"Failed to cleanup sandbox {task_id}: {e}")
