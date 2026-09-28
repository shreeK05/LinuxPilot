"""
Keyboard Tools
Keyboard shortcut handling and key sequence support
"""

import subprocess
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)


# Common keyboard shortcuts for applications
SHORTCUTS = {
    "save": "ctrl+s",
    "save_as": "ctrl+shift+s",
    "copy": "ctrl+c",
    "paste": "ctrl+v",
    "cut": "ctrl+x",
    "undo": "ctrl+z",
    "redo": "ctrl+shift+z",
    "select_all": "ctrl+a",
    "close": "alt+F4",
    "new_tab": "ctrl+t",
    "close_tab": "ctrl+w",
    "find": "ctrl+f",
    "quit": "ctrl+q",
    "refresh": "F5",
    "fullscreen": "F11",
    "print": "ctrl+p",
}


class KeyboardTools:
    """
    Keyboard interaction tools.
    Wraps xdotool for sending key events.
    """

    def send_key(self, key: str) -> dict[str, Any]:
        """
        Send a key or key combination.

        Accepts:
        - Named shortcuts: 'save', 'copy', 'undo', etc.
        - Key names: 'Return', 'Tab', 'Escape', 'space'
        - Combinations: 'ctrl+s', 'alt+F4', 'ctrl+shift+z'
        """
        # Check for named shortcuts first
        actual_key = SHORTCUTS.get(key.lower(), key)

        # Normalize for xdotool
        key_map = {
            "Enter": "Return",
            "Esc": "Escape",
            "Del": "Delete",
            "Backspace": "BackSpace",
        }

        parts = actual_key.replace("+", " ").split()
        normalized = [key_map.get(p, p) for p in parts]
        xdotool_key = "+".join(normalized)

        try:
            result = subprocess.run(
                ["xdotool", "key", "--clearmodifiers", xdotool_key],
                capture_output=True,
                text=True,
                timeout=5,
            )
            success = result.returncode == 0
            if not success:
                logger.warning(f"xdotool key failed: {result.stderr}")
            return {"key": key, "resolved": actual_key, "sent": success}
        except FileNotFoundError:
            raise RuntimeError("xdotool not installed")

    def send_key_sequence(self, keys: list[str], delay: float = 0.1) -> dict[str, Any]:
        """
        Send a sequence of keys with delay between each.

        Args:
            keys: List of key names/combinations
            delay: Delay between keys in seconds
        """
        results = []
        for key in keys:
            result = self.send_key(key)
            results.append(result)
            if delay > 0:
                time.sleep(delay)

        all_success = all(r.get("sent", False) for r in results)
        return {"keys_sent": len(keys), "all_success": all_success, "results": results}

    def type_text(self, text: str, delay_ms: int = 12) -> dict[str, Any]:
        """
        Type text character by character via xdotool.

        Args:
            text: Text to type
            delay_ms: Delay between characters in milliseconds
        """
        try:
            result = subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", str(delay_ms), text],
                capture_output=True,
                text=True,
                timeout=max(10, len(text) * delay_ms / 1000 + 5),
            )
            return {"typed": True, "length": len(text), "success": result.returncode == 0}
        except FileNotFoundError:
            raise RuntimeError("xdotool not installed")

    def focus_window(self, window_name: str) -> dict[str, Any]:
        """Focus a window by name using xdotool"""
        try:
            # Search for window
            search = subprocess.run(
                ["xdotool", "search", "--name", window_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if search.returncode != 0 or not search.stdout.strip():
                return {"window": window_name, "focused": False, "reason": "not found"}

            window_id = search.stdout.strip().split("\n")[0]

            # Activate the window
            subprocess.run(
                ["xdotool", "windowactivate", "--sync", window_id],
                capture_output=True,
                timeout=5,
            )
            logger.info(f"Focused window: {window_name} (ID: {window_id})")
            return {"window": window_name, "window_id": window_id, "focused": True}
        except FileNotFoundError:
            raise RuntimeError("xdotool not installed")
