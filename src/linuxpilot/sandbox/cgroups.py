"""
Cgroup Manager
Manages cgroup v2 for resource containment
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CgroupManager:
    """
    Manages cgroup v2 for resource limits
    Implements resource containment (memory, CPU, PIDs)
    """
    
    def __init__(self, cgroup_base: Path = None):
        self.cgroup_base = cgroup_base or Path("/sys/fs/cgroup")
        self.cgroup_linuxpilot = self.cgroup_base / "linuxpilot"
        
        # Ensure base directory exists
        try:
            self.cgroup_linuxpilot.mkdir(exist_ok=True)
        except (PermissionError, OSError) as e:
            logger.warning(f"Cannot create cgroup directory (cgroups will be disabled): {e}")
            self.cgroup_linuxpilot = None
    
    def create_cgroup(
        self,
        task_id: str,
        memory_limit_mb: Optional[int] = None,
        cpu_limit_percent: Optional[int] = None,
        pids_limit: Optional[int] = None,
    ) -> Optional[str]:
        """
        Create a cgroup for a task
        
        Args:
            task_id: Task identifier
            memory_limit_mb: Memory limit in MB
            cpu_limit_percent: CPU limit as percentage (100 = 1 CPU)
            pids_limit: Process count limit
        
        Returns:
            Path to the cgroup or None if failed
        """
        try:
            if not self.cgroup_linuxpilot:
                return None
            cgroup_path = self.cgroup_linuxpilot / task_id
            cgroup_path.mkdir(exist_ok=True)
            
            # Set memory limit
            if memory_limit_mb:
                memory_max = cgroup_path / "memory.max"
                memory_bytes = memory_limit_mb * 1024 * 1024
                with open(memory_max, "w") as f:
                    f.write(str(memory_bytes))
            
            # Set CPU limit
            if cpu_limit_percent:
                cpu_max = cgroup_path / "cpu.max"
                # Format: "$MAX $PERIOD" where $PERIOD is usually 100000
                cpu_quota = int(cpu_limit_percent * 1000)  # 100% = 100000
                with open(cpu_max, "w") as f:
                    f.write(f"{cpu_quota} 100000")
            
            # Set PIDs limit
            if pids_limit:
                pids_max = cgroup_path / "pids.max"
                with open(pids_max, "w") as f:
                    f.write(str(pids_limit))
            
            logger.info(f"Created cgroup {task_id} with limits: memory={memory_limit_mb}MB, cpu={cpu_limit_percent}%, pids={pids_limit}")
            return str(cgroup_path)
            
        except PermissionError:
            logger.error(f"Permission denied creating cgroup {task_id} - may need root")
            return None
        except Exception as e:
            logger.error(f"Failed to create cgroup {task_id}: {e}")
            return None
    
    def remove_cgroup(self, task_id: str) -> bool:
        """
        Remove a cgroup
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if successful
        """
        try:
            if not self.cgroup_linuxpilot:
                return True
            cgroup_path = self.cgroup_linuxpilot / task_id
            
            if not cgroup_path.exists():
                return True
            
            # Ensure all processes are killed first
            self.kill_cgroup(task_id)
            
            # Remove directory
            cgroup_path.rmdir()
            
            logger.info(f"Removed cgroup {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove cgroup {task_id}: {e}")
            return False
    
    def kill_cgroup(self, task_id: str) -> bool:
        """
        Kill all processes in a cgroup
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if successful
        """
        try:
            if not self.cgroup_linuxpilot:
                return True
            cgroup_path = self.cgroup_linuxpilot / task_id
            kill_file = cgroup_path / "cgroup.kill"
            
            if kill_file.exists():
                with open(kill_file, "w") as f:
                    f.write("1")
                logger.info(f"Killed all processes in cgroup {task_id}")
                return True
            else:
                # Fallback: read pids and kill manually
                procs_file = cgroup_path / "cgroup.procs"
                if procs_file.exists():
                    with open(procs_file, "r") as f:
                        pids = [line.strip() for line in f if line.strip()]
                    
                    import signal
                    for pid in pids:
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    
                    logger.info(f"Killed {len(pids)} processes in cgroup {task_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to kill cgroup {task_id}: {e}")
            return False
    
    def get_stats(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a cgroup
        
        Args:
            task_id: Task identifier
        
        Returns:
            Dictionary with stats or None if failed
        """
        try:
            if not self.cgroup_linuxpilot:
                return None
            cgroup_path = self.cgroup_linuxpilot / task_id
            
            if not cgroup_path.exists():
                return None
            
            stats = {}
            
            # Memory stats
            memory_current = cgroup_path / "memory.current"
            if memory_current.exists():
                with open(memory_current, "r") as f:
                    stats["memory_bytes"] = int(f.read().strip())
            
            memory_peak = cgroup_path / "memory.peak"
            if memory_peak.exists():
                with open(memory_peak, "r") as f:
                    stats["memory_peak_bytes"] = int(f.read().strip())
            
            # PIDs
            procs_file = cgroup_path / "cgroup.procs"
            if procs_file.exists():
                with open(procs_file, "r") as f:
                    pids = [line.strip() for line in f if line.strip()]
                stats["pids"] = len(pids)
            
            # CPU stats
            cpu_stat = cgroup_path / "cpu.stat"
            if cpu_stat.exists():
                with open(cpu_stat, "r") as f:
                    cpu_data = {}
                    for line in f:
                        if line.strip():
                            key, value = line.strip().split()
                            cpu_data[key] = int(value)
                    stats["cpu_stat"] = cpu_data
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats for cgroup {task_id}: {e}")
            return None
    
    def list_cgroups(self) -> list[str]:
        """List all active cgroups"""
        try:
            if not self.cgroup_linuxpilot or not self.cgroup_linuxpilot.exists():
                return []
            
            return [item.name for item in self.cgroup_linuxpilot.iterdir() if item.is_dir()]
            
        except Exception as e:
            logger.error(f"Failed to list cgroups: {e}")
            return []
