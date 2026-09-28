import pytest
from app.agent.sandbox.seccomp import SeccompManager
from app.agent.sandbox.exceptions import UnsupportedPlatformError, SandboxInitializationError

def test_seccomp_manager_fallback():
    # Should not raise any errors when strict is False
    manager = SeccompManager(strict=False)
    manager.apply_filters()

def test_seccomp_manager_strict():
    manager = SeccompManager(strict=True)
    if manager.is_linux:
        # On Linux, if seccomp is missing it will raise SandboxInitializationError, else it might succeed
        pass
    else:
        with pytest.raises(UnsupportedPlatformError):
            manager.apply_filters()
