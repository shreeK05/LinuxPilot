"""
Namespace Manager
Manages Linux namespaces for process isolation
"""

import os
import subprocess
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class NamespaceManager:
    """
    Manages Linux namespaces for process isolation
    Uses mount, pid, ipc, uts, and optionally net namespaces
    """
    
    def __init__(self):
        # Check if unprivileged user namespaces are available
        self.unprivileged_available = self._check_unprivileged()
    
    def _check_unprivileged(self) -> bool:
        """Check if unprivileged user namespaces are available"""
        try:
            # Check if the kernel allows unprivileged user namespaces
            with open("/proc/sys/kernel/unprivileged_userns_clone", "r") as f:
                return f.read().strip() == "1"
        except Exception:
            # May not exist on all systems
            return False
    
    def create_namespaces(
        self,
        mount: bool = True,
        pid: bool = True,
        ipc: bool = True,
        uts: bool = True,
        net: bool = False,
    ) -> Optional[subprocess.Popen]:
        """
        Create a new process with isolated namespaces
        
        Args:
            mount: Isolate mount namespace
            pid: Isolate PID namespace
            ipc: Isolate IPC namespace
            uts: Isolate UTS namespace
            net: Isolate network namespace
        
        Returns:
            Process object or None if failed
        """
        try:
            # Build unshare flags
            flags = []
            if mount:
                flags.append("--mount")
            if pid:
                flags.append("--pid")
            if ipc:
                flags.append("--ipc")
            if uts:
                flags.append("--uts")
            if net:
                flags.append("--net")
            
            if not flags:
                logger.warning("No namespaces requested")
                return None
            
            # Use unshare to create namespaces
            # Note: This requires the unshare command
            cmd = ["unshare"] + flags + ["--fork", "--mount-proc", "sleep", "infinity"]
            
            proc = subprocess.Popen(cmd)
            logger.info(f"Created process with namespaces: {flags}")
            return proc
            
        except Exception as e:
            logger.error(f"Failed to create namespaces: {e}")
            return None
    
    def setup_mount_namespace(
        self,
        workspace_path: str,
        real_data_path: str,
    ) -> bool:
        """
        Setup overlayfs mount in the mount namespace
        
        Args:
            workspace_path: Path to workspace overlay
            real_data_path: Path to real data
        
        Returns:
            True if successful
        """
        try:
            # This would be called inside the mount namespace
            # Mount overlayfs with lower=real_data, upper=workspace/upper, work=workspace/work
            # This is a placeholder - in production, this needs proper execution in the namespace
            
            logger.info(f"Setting up mount namespace: {workspace_path} over {real_data_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup mount namespace: {e}")
            return False
    
    def enter_namespace(self, pid: int, namespace: str) -> bool:
        """
        Enter an existing namespace (for debugging/inspection)
        
        Args:
            pid: PID of the target process
            namespace: Namespace type (mnt, pid, ipc, uts, net)
        
        Returns:
            True if successful
        """
        try:
            ns_path = f"/proc/{pid}/ns/{namespace}"
            if not os.path.exists(ns_path):
                logger.error(f"Namespace {namespace} not found for PID {pid}")
                return False
            
            # Use nsenter to enter the namespace
            # This is for debugging purposes
            logger.info(f"Would enter namespace {namespace} for PID {pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enter namespace: {e}")
            return False
