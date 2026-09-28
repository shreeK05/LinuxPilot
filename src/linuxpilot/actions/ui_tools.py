"""
UI Tools
AT-SPI based GUI automation tools for LinuxPilot
These run at Rungs L1-L5 of the action ladder
"""

import subprocess
import time
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Guard AT-SPI imports for systems where it's not available
try:
    import gi
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi
    ATSPI_AVAILABLE = True
except (ImportError, ValueError):
    ATSPI_AVAILABLE = False


class UITools:
    """
    GUI automation tools using AT-SPI and xdotool.
    Prefers AT-SPI actions (deterministic) over coordinate-based clicks (fragile).
    """

    def __init__(self):
        self.atspi_available = ATSPI_AVAILABLE

    def launch_app(self, app_name: str, args: Optional[list[str]] = None) -> dict[str, Any]:
        """
        Launch a GUI application (Rung L0 of lifecycle)

        Args:
            app_name: Application to launch (e.g., 'thunar', 'libreoffice', 'firefox')
            args: Optional command-line arguments
        """
        cmd = [app_name] + (args or [])

        # Special handling for known apps
        app_cmds = {
            "libreoffice": ["libreoffice", "--calc"],
            "libreoffice-calc": ["libreoffice", "--calc"],
            "firefox": ["firefox", "--no-remote"],
            "thunar": ["thunar"],
            "gedit": ["gedit"],
            "xfce4-terminal": ["xfce4-terminal"],
        }

        if app_name in app_cmds:
            cmd = app_cmds[app_name] + (args or [])

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logger.info(f"Launched {app_name} (PID {proc.pid})")

            # Wait for the application window to appear
            self._wait_for_app_window(app_name, timeout=10)

            return {
                "app_name": app_name,
                "pid": proc.pid,
                "launched": True,
            }
        except FileNotFoundError:
            raise RuntimeError(f"Application not found: {app_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to launch {app_name}: {e}")

    def close_app(self, app_name: str) -> dict[str, Any]:
        """Close an application by name"""
        try:
            result = subprocess.run(
                ["pkill", "-f", app_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            closed = result.returncode == 0
            logger.info(f"Closed {app_name}: {closed}")
            return {"app_name": app_name, "closed": closed}
        except Exception as e:
            logger.error(f"Failed to close {app_name}: {e}")
            return {"app_name": app_name, "closed": False, "error": str(e)}

    def invoke_action(self, element_id: str, action_name: str = "activate") -> dict[str, Any]:
        """
        Rung L1: Invoke an AT-SPI action on an element (no coordinates needed)

        Args:
            element_id: Stable ID or role:name identifier
            action_name: Action to invoke (default: 'activate' which is click)
        """
        if not self.atspi_available:
            raise RuntimeError("AT-SPI not available")

        element = self._find_element_by_id(element_id)
        if not element:
            raise RuntimeError(f"Element not found: {element_id}")

        action_iface = element.get_action_iface()
        if not action_iface:
            raise RuntimeError(f"Element has no actions: {element_id}")

        # Find and invoke the action
        for i in range(action_iface.get_n_actions()):
            if action_iface.get_action_name(i) == action_name:
                result = action_iface.do_action(i)
                logger.info(f"Invoked {action_name} on {element_id}: {result}")
                return {"element_id": element_id, "action": action_name, "success": result}

        raise RuntimeError(
            f"Action '{action_name}' not found on element. "
            f"Available: {[action_iface.get_action_name(i) for i in range(action_iface.get_n_actions())]}"
        )

    def set_text(self, element_id: str, text: str) -> dict[str, Any]:
        """
        Rung L2: Set text content of an editable element via AT-SPI

        Args:
            element_id: Stable ID or role:name identifier
            text: Text to set
        """
        if not self.atspi_available:
            raise RuntimeError("AT-SPI not available")

        element = self._find_element_by_id(element_id)
        if not element:
            raise RuntimeError(f"Element not found: {element_id}")

        editable = element.get_editable_text_iface()
        if not editable:
            # Fallback: try to focus and type
            logger.warning(f"Element {element_id} not editable via AT-SPI, falling back to keyboard")
            return self._type_text_fallback(element, text)

        # Clear and set text
        text_iface = element.get_text_iface()
        if text_iface:
            current_len = text_iface.get_character_count()
            if current_len > 0:
                editable.delete_text(0, current_len)

        editable.insert_text(0, text, len(text))
        logger.info(f"Set text on {element_id}: {text[:50]}...")
        return {"element_id": element_id, "text_set": True, "length": len(text)}

    def send_key(self, key: str) -> dict[str, Any]:
        """
        Rung L3: Send a key combination via xdotool

        Args:
            key: Key combination (e.g., 'Return', 'ctrl+s', 'Tab', 'alt+F4')
        """
        # Normalize key names for xdotool
        key_map = {
            "Enter": "Return",
            "Esc": "Escape",
            "Del": "Delete",
            "Backspace": "BackSpace",
            "Ctrl": "ctrl",
            "Alt": "alt",
            "Shift": "shift",
        }

        # Process the key combination
        parts = key.replace("+", " ").split()
        normalized = []
        for part in parts:
            normalized.append(key_map.get(part, part))
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
            else:
                logger.info(f"Sent key: {xdotool_key}")
            return {"key": key, "sent": success}
        except FileNotFoundError:
            raise RuntimeError("xdotool not installed")
        except Exception as e:
            raise RuntimeError(f"Failed to send key: {e}")

    def click_xy(self, x: int, y: int, button: int = 1) -> dict[str, Any]:
        """
        Rung L4: Click at screen coordinates via xdotool

        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button (1=left, 2=middle, 3=right)
        """
        try:
            result = subprocess.run(
                ["xdotool", "mousemove", "--sync", str(x), str(y),
                 "click", str(button)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            success = result.returncode == 0
            logger.info(f"Clicked at ({x}, {y}) button={button}: {success}")
            return {"x": x, "y": y, "button": button, "clicked": success}
        except FileNotFoundError:
            raise RuntimeError("xdotool not installed")
        except Exception as e:
            raise RuntimeError(f"Failed to click: {e}")

    def click_element(self, element_id: str) -> dict[str, Any]:
        """
        Rung L4: Click the center of an AT-SPI element using its bounding box
        """
        if not self.atspi_available:
            raise RuntimeError("AT-SPI not available")

        element = self._find_element_by_id(element_id)
        if not element:
            raise RuntimeError(f"Element not found: {element_id}")

        comp = element.get_component_iface()
        if not comp:
            raise RuntimeError(f"Element has no component interface: {element_id}")

        extents = comp.get_extents(Atspi.CoordType.SCREEN)
        cx = extents.x + extents.width // 2
        cy = extents.y + extents.height // 2

        return self.click_xy(cx, cy)

    def type_text(self, text: str, delay_ms: int = 12) -> dict[str, Any]:
        """Type text character by character via xdotool (for fields without AT-SPI editable)"""
        try:
            result = subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", str(delay_ms), text],
                capture_output=True,
                text=True,
                timeout=max(10, len(text) * delay_ms / 1000 + 5),
            )
            success = result.returncode == 0
            logger.info(f"Typed {len(text)} characters")
            return {"typed": True, "length": len(text)}
        except FileNotFoundError:
            raise RuntimeError("xdotool not installed")

    # --- Internal helpers ---

    def _find_element_by_id(self, element_id: str):
        """Find an AT-SPI element by stable ID or role:name pattern"""
        if not ATSPI_AVAILABLE:
            return None

        desktop = Atspi.get_desktop(0)

        # If it looks like "role:name", search by that
        if ":" in element_id and not element_id.startswith("0x"):
            parts = element_id.split(":", 1)
            role_match = parts[0]
            name_match = parts[1] if len(parts) > 1 else None
            return self._find_by_role_name(desktop, role_match, name_match)

        # Otherwise search by stable hash ID
        return self._find_by_hash(desktop, element_id)

    def _find_by_role_name(self, root, role: str, name: Optional[str], depth: int = 0):
        """Recursive search by role and name"""
        if depth > 25:
            return None

        try:
            for i in range(root.get_child_count()):
                child = root.get_child_at_index(i)
                if child is None:
                    continue

                child_role = child.get_role_name()
                child_name = child.get_name() or ""

                if child_role == role:
                    if name is None or name.lower() in child_name.lower():
                        state = child.get_state_set()
                        if state.contains(Atspi.StateType.SHOWING):
                            return child

                # Recurse
                found = self._find_by_role_name(child, role, name, depth + 1)
                if found:
                    return found
        except Exception:
            pass

        return None

    def _find_by_hash(self, root, target_hash: str, path: Optional[list] = None, depth: int = 0):
        """Find element by stable hash ID"""
        if depth > 25:
            return None
        if path is None:
            path = []

        try:
            for i in range(root.get_child_count()):
                child = root.get_child_at_index(i)
                if child is None:
                    continue

                current_path = path + [i]
                import hashlib
                role = child.get_role_name()
                name = child.get_name() or ""
                id_string = f"{role}:{name}:{':'.join(map(str, current_path))}"
                h = hashlib.sha256(id_string.encode()).hexdigest()[:16]

                if h == target_hash:
                    return child

                found = self._find_by_hash(child, target_hash, current_path, depth + 1)
                if found:
                    return found
        except Exception:
            pass

        return None

    def _wait_for_app_window(self, app_name: str, timeout: int = 10):
        """Wait for an application window to appear"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                result = subprocess.run(
                    ["xdotool", "search", "--name", app_name],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return True
            except Exception:
                pass
            time.sleep(0.3)
        logger.warning(f"Timed out waiting for {app_name} window")
        return False

    def _type_text_fallback(self, element, text: str) -> dict[str, Any]:
        """Fallback: focus element by clicking its center, then type"""
        comp = element.get_component_iface()
        if comp:
            extents = comp.get_extents(Atspi.CoordType.SCREEN)
            cx = extents.x + extents.width // 2
            cy = extents.y + extents.height // 2
            self.click_xy(cx, cy)
            time.sleep(0.2)

        # Select all, then type
        self.send_key("ctrl+a")
        time.sleep(0.1)
        return self.type_text(text)
