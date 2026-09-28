import platform
import os

is_windows = platform.system() == "Windows"

if not is_windows:
    import resource

class ResourceLimits:
    """
    Platform-aware resource limit enforcer.
    On Linux, uses resource.setrlimit to bound subprocesses.
    On Windows, provides graceful fallbacks for development.
    """
    
    @staticmethod
    def apply_limits(max_memory_mb: int = 512, max_cpu_seconds: int = 60, max_processes: int = 50, max_file_size_mb: int = 100):
        if is_windows:
            # We are in a Windows development environment.
            # Real resource limits cannot be applied via `resource`.
            return

        try:
            # 1. Address space / memory limit (RLIMIT_AS)
            mem_bytes = max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            
            # 2. CPU time limit in seconds (RLIMIT_CPU)
            resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_seconds, max_cpu_seconds))
            
            # 3. Process count limit (RLIMIT_NPROC)
            resource.setrlimit(resource.RLIMIT_NPROC, (max_processes, max_processes))
            
            # 4. File size limit (RLIMIT_FSIZE)
            file_bytes = max_file_size_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))
            
        except ValueError as e:
            # This can happen if we try to set a limit higher than the hard limit
            pass
        except Exception as e:
            # We should not crash the sandbox if a limit fails to apply on some exotic unix
            pass

def preexec_fn_limits():
    """
    Used as the preexec_fn in subprocess.Popen to apply limits to the child process
    before it calls exec().
    """
    if not is_windows:
        ResourceLimits.apply_limits()
