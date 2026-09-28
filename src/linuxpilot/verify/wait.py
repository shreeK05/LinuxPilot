"""
Wait Utilities
Condition-based polling with timeouts — no fixed sleep() anywhere.
"""

import time
import hashlib
import logging
from typing import Callable, Optional, Any

logger = logging.getLogger(__name__)


def wait_until(
    predicate: Callable[[], bool],
    timeout: float = 10.0,
    interval: float = 0.2,
    description: str = "condition",
) -> bool:
    """
    Poll a predicate until it returns True or timeout expires.
    This replaces all fixed sleep() calls in the codebase.

    Args:
        predicate: Callable returning True when condition is met
        timeout: Maximum wait time in seconds
        interval: Polling interval in seconds
        description: Human-readable description for logging

    Returns:
        True if condition was met, False if timed out
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            if predicate():
                elapsed = time.time() - start
                logger.debug(f"Condition '{description}' met after {elapsed:.2f}s")
                return True
        except Exception as e:
            logger.debug(f"Condition '{description}' check error: {e}")
        time.sleep(interval)

    logger.warning(f"Condition '{description}' timed out after {timeout}s")
    return False


def wait_for_quiescence(
    get_hash: Callable[[], str],
    stable_duration: float = 0.3,
    timeout: float = 10.0,
    interval: float = 0.1,
) -> bool:
    """
    Wait until a hash stops changing for stable_duration seconds.
    Used after each action to ensure the UI has settled.

    Args:
        get_hash: Callable returning a hash of the current state
        stable_duration: How long the hash must remain unchanged
        timeout: Maximum wait time
        interval: Polling interval

    Returns:
        True if quiescence was reached, False if timed out
    """
    start = time.time()
    last_hash = None
    stable_since = None

    while time.time() - start < timeout:
        current_hash = get_hash()

        if current_hash != last_hash:
            last_hash = current_hash
            stable_since = time.time()
        elif stable_since and (time.time() - stable_since) >= stable_duration:
            elapsed = time.time() - start
            logger.debug(f"Quiescence reached after {elapsed:.2f}s")
            return True

        time.sleep(interval)

    logger.warning(f"Quiescence not reached after {timeout}s")
    return False


def wait_for_process(pid: int, timeout: float = 30.0) -> Optional[int]:
    """
    Wait for a process to exit.

    Args:
        pid: Process ID
        timeout: Maximum wait time

    Returns:
        Exit code or None if timed out
    """
    import os
    import signal

    start = time.time()
    while time.time() - start < timeout:
        try:
            result = os.waitpid(pid, os.WNOHANG)
            if result[0] != 0:
                exit_code = os.WEXITSTATUS(result[1]) if os.WIFEXITED(result[1]) else -1
                if os.WIFSIGNALED(result[1]):
                    sig = os.WTERMSIG(result[1])
                    logger.info(f"Process {pid} killed by signal {sig}")
                    return -sig
                return exit_code
        except ChildProcessError:
            return 0  # Already reaped
        except Exception:
            pass
        time.sleep(0.1)

    return None


def wait_for_file(
    path: str,
    timeout: float = 10.0,
    must_exist: bool = True,
) -> bool:
    """
    Wait for a file to exist (or not exist).

    Args:
        path: File path
        timeout: Maximum wait time
        must_exist: If True, wait for file to appear; if False, wait for it to disappear
    """
    from pathlib import Path

    target = Path(path).expanduser()

    def check():
        exists = target.exists()
        return exists if must_exist else not exists

    desc = f"file {'exists' if must_exist else 'removed'}: {path}"
    return wait_until(check, timeout=timeout, description=desc)
