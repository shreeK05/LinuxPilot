import platform
from .exceptions import UnsupportedPlatformError, SandboxInitializationError

class CgroupManager:
    """
    Manages cgroups v2 resource limits for a sandbox environment.
    """
    def __init__(self):
        self.is_linux = platform.system().lower() == "linux"

    def apply_limits(self, group_name: str, cpu_limit_shares: int = None, memory_limit_mb: int = None):
        """
        Applies memory and CPU limits using cgroups v2.
        """
        if not self.is_linux:
            raise UnsupportedPlatformError("cgroups v2 are only supported on Linux.")
            
        # Stub implementation for actual Linux enforcement
        # In a real environment, this would write to /sys/fs/cgroup/...
        # e.g., /sys/fs/cgroup/sandbox_<group_name>/memory.max
        pass
        
    def add_process(self, group_name: str, pid: int):
        if not self.is_linux:
            raise UnsupportedPlatformError("cgroups v2 are only supported on Linux.")
        pass

    def cleanup(self, group_name: str):
        if not self.is_linux:
            return
        pass
