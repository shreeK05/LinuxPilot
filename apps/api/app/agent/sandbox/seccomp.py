import platform
from .exceptions import UnsupportedPlatformError, SandboxInitializationError

class SeccompManager:
    """
    Manages seccomp-bpf filters to restrict syscalls.
    """
    def __init__(self):
        self.is_linux = platform.system().lower() == "linux"

    def apply_filters(self):
        """
        Applies strict syscall filters for the sandboxed process.
        """
        if not self.is_linux:
            raise UnsupportedPlatformError("Seccomp is only supported on Linux.")
            
        # Stub: libseccomp bindings to create rules and load them.
        pass
