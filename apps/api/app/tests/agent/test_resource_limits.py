import platform
import pytest
from app.agent.sandbox.resource_limits import ResourceLimits, is_windows, preexec_fn_limits

def test_resource_limits_graceful_on_windows():
    if is_windows:
        # Should not raise exception
        ResourceLimits.apply_limits()
        preexec_fn_limits()
    else:
        # On Linux/macOS, we don't want to actually restrict the test process,
        # but calling it with large limits should not crash.
        ResourceLimits.apply_limits(max_memory_mb=10240, max_cpu_seconds=3600, max_processes=1000, max_file_size_mb=10240)
        assert True
