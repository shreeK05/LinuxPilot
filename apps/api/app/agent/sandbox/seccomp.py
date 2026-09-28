import platform
import logging
from .exceptions import UnsupportedPlatformError, SandboxInitializationError

logger = logging.getLogger(__name__)

class SeccompManager:
    """
    Manages seccomp-bpf filters to restrict syscalls.
    """
    def __init__(self, strict: bool = False):
        self.is_linux = platform.system().lower() == "linux"
        self.strict = strict

    def apply_filters(self):
        """
        Applies strict syscall filters for the sandboxed process.
        """
        if not self.is_linux:
            if self.strict:
                raise UnsupportedPlatformError("Seccomp is only supported on Linux.")
            logger.warning("Skipping seccomp filters (not on Linux).")
            return
            
        try:
            import seccomp
        except ImportError:
            if self.strict:
                raise SandboxInitializationError("python-seccomp library is missing.")
            logger.warning("Skipping seccomp filters (python-seccomp not installed).")
            return

        try:
            # Default action: KILL the process if it makes a syscall not in the allowlist
            f = seccomp.SyscallFilter(defaction=seccomp.KILL)
            
            # Allow essential syscalls for normal execution
            allowed_syscalls = [
                "read", "write", "close", "fstat", "mmap", "mprotect", 
                "munmap", "brk", "rt_sigaction", "rt_sigprocmask", 
                "rt_sigreturn", "ioctl", "getpid", "exit_group", 
                "exit", "execve", "arch_prctl", "access", "openat"
            ]
            
            for syscall in allowed_syscalls:
                f.add_rule(seccomp.ALLOW, syscall)
                
            f.load()
        except Exception as e:
            if self.strict:
                raise SandboxInitializationError(f"Failed to apply seccomp filter: {str(e)}")
            logger.warning(f"Failed to apply seccomp filter: {str(e)}")
