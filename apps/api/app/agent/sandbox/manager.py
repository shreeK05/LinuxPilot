from typing import Any, Callable
from app.agent.models import ActionDefinition, SandboxConfig
from app.agent.actions.registry import ActionExecutionResult
from .namespaces import NamespaceManager
from .cgroups import CgroupManager
from .seccomp import SeccompManager
from .exceptions import UnsupportedPlatformError, SandboxInitializationError
import platform

class SandboxManager:
    """
    Coordinates the sandbox environment for high-risk actions.
    """
    def __init__(self):
        self.namespaces = NamespaceManager()
        self.cgroups = CgroupManager()
        self.seccomp = SeccompManager()
        self.is_linux = platform.system().lower() == "linux"

    def execute_in_sandbox(self, action: ActionDefinition, handler_func: Callable[[], ActionExecutionResult]) -> ActionExecutionResult:
        """
        Sets up the sandbox configured in `action.sandbox_config`, executes the handler, and tears it down.
        """
        config = action.sandbox_config
        
        if not self.is_linux:
            # We are on an unsupported platform (e.g. Windows).
            # The blueprint explicitly requires returning UNSUPPORTED_PLATFORM instead of falling back to unsafe execution.
            return ActionExecutionResult(
                success=False,
                output=None,
                error="UNSUPPORTED_PLATFORM: Linux Sandbox features are not available on this OS."
            )

        try:
            # 1. Resource Limits (Cgroups)
            group_name = f"task_{action.action_id}"
            self.cgroups.apply_limits(
                group_name=group_name, 
                cpu_limit_shares=config.cpu_limit_shares, 
                memory_limit_mb=config.memory_limit_mb
            )

            # 2. Namespace Isolation
            self.namespaces.setup_namespaces(network_allowed=config.network_allowed)
            self.namespaces.mount_filesystem(allowed_mounts=config.allowed_mounts)
            
            # 3. Syscall filtering
            self.seccomp.apply_filters()
            
            # (In a real implementation, we would fork and execute the payload in the isolated process)
            # Since this is a python-based conceptual phase on Windows, we execute it directly if we were on Linux.
            
            result = handler_func()
            return result
            
        except UnsupportedPlatformError as e:
            return ActionExecutionResult(success=False, output=None, error=f"UNSUPPORTED_PLATFORM: {str(e)}")
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=f"SANDBOX_ERROR: {str(e)}")
        finally:
            if self.is_linux:
                try:
                    self.cgroups.cleanup(group_name)
                except Exception:
                    pass
