"""
Action Ladder
Routes tool invocations to the appropriate executor rung.
Prefers deterministic tools (L0) and escalates to GUI interaction only when needed.
"""

import time
import logging
from typing import Any, Optional

from linuxpilot.actions.fs_tools import FileSystemTools
from linuxpilot.actions.ui_tools import UITools
from linuxpilot.actions.keys import KeyboardTools
from linuxpilot.models import Step, ActionExecutionResult

logger = logging.getLogger(__name__)


class ActionLadder:
    """
    Routes step tool invocations to the correct executor.

    Rung hierarchy (prefer the top; escalate only on failure):
      L0  fs.*, doc.*, sheet.*      — direct file ops inside overlay (deterministic)
      L1  ui.invoke                 — AT-SPI Action.do_action (no coordinates)
      L2  ui.set_text               — AT-SPI EditableText
      L3  ui.key                    — xdotool key (keyboard shortcuts)
      L4  ui.click_xy               — xdotool click at AT-SPI element center
      L5  ui.vlm_click              — VLM-guided click (last resort, stretch goal)
    """

    def __init__(self, workspace_root: str, mode: str = "hybrid"):
        """
        Args:
            workspace_root: Root path of the overlay workspace for fs tools
            mode: Execution mode — 'api' (L0 only), 'gui' (L1-L5 only), 'hybrid' (all)
        """
        self.workspace_root = workspace_root
        self.mode = mode
        self.fs = FileSystemTools(workspace_root)
        self.ui = UITools()
        self.keys = KeyboardTools()

        # Tool -> executor dispatch table
        self._dispatch = {
            # L0: File system tools
            "fs.list": self._exec_fs_list,
            "fs.stat": self._exec_fs_stat,
            "fs.mkdir": self._exec_fs_mkdir,
            "fs.move": self._exec_fs_move,
            "fs.copy": self._exec_fs_copy,
            "fs.delete": self._exec_fs_delete,
            "fs.read_text": self._exec_fs_read_text,
            "doc.extract_pdf": self._exec_doc_extract_pdf,
            "sheet.write": self._exec_sheet_write,
            # L0/L1: App lifecycle
            "app.launch": self._exec_app_launch,
            "app.close": self._exec_app_close,
            # L1: AT-SPI actions
            "ui.invoke": self._exec_ui_invoke,
            # L2: AT-SPI text
            "ui.set_text": self._exec_ui_set_text,
            # L3: Keyboard
            "ui.key": self._exec_ui_key,
            # L4: Coordinate click
            "ui.click_xy": self._exec_ui_click_xy,
            # L5: VLM-guided click
            "ui.vlm_click": self._exec_ui_vlm_click,
            # Utility
            "web.wait_for_text": self._exec_web_wait,
        }

    def execute(self, step: Step) -> ActionExecutionResult:
        """
        Execute a step's tool invocation.

        Args:
            step: The plan Step containing tool and args

        Returns:
            ActionExecutionResult with success/failure and output
        """
        tool = step.tool
        args = step.args

        # Mode gating
        l0_tools = {
            "fs.list", "fs.stat", "fs.mkdir", "fs.move", "fs.copy",
            "fs.delete", "fs.read_text", "doc.extract_pdf", "sheet.write",
        }
        gui_tools = {
            "app.launch", "app.close", "ui.invoke", "ui.set_text",
            "ui.key", "ui.click_xy", "ui.vlm_click",
        }

        if self.mode == "api" and tool in gui_tools:
            return ActionExecutionResult(
                success=False,
                error=f"Tool {tool} not available in api-only mode",
            )
        if self.mode == "gui" and tool in l0_tools:
            return ActionExecutionResult(
                success=False,
                error=f"Tool {tool} not available in gui-only mode",
            )

        executor = self._dispatch.get(tool)
        if not executor:
            return ActionExecutionResult(
                success=False,
                error=f"Unknown tool: {tool}",
            )

        start_time = time.time()
        try:
            output = executor(args)
            duration_ms = int((time.time() - start_time) * 1000)

            # Record which rung was used
            rung = self._get_rung(tool)
            logger.info(f"Action {tool} completed in {duration_ms}ms (rung L{rung})")

            return ActionExecutionResult(
                success=True,
                output=output,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Action {tool} failed after {duration_ms}ms: {e}")
            return ActionExecutionResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    def _get_rung(self, tool: str) -> int:
        """Get the action ladder rung number for a tool"""
        rung_map = {
            "fs.list": 0, "fs.stat": 0, "fs.mkdir": 0, "fs.move": 0,
            "fs.copy": 0, "fs.delete": 0, "fs.read_text": 0,
            "doc.extract_pdf": 0, "sheet.write": 0,
            "app.launch": 0, "app.close": 0,
            "ui.invoke": 1,
            "ui.set_text": 2,
            "ui.key": 3,
            "ui.click_xy": 4,
            "ui.vlm_click": 5,
            "web.wait_for_text": 0,
        }
        return rung_map.get(tool, -1)

    # ---- L0 Executors ----

    def _exec_fs_list(self, args: dict) -> dict:
        return self.fs.list_dir(args["path"])

    def _exec_fs_stat(self, args: dict) -> dict:
        return self.fs.stat(args["path"])

    def _exec_fs_mkdir(self, args: dict) -> dict:
        return self.fs.mkdir(args["path"])

    def _exec_fs_move(self, args: dict) -> dict:
        return self.fs.move(args["source"], args["destination"])

    def _exec_fs_copy(self, args: dict) -> dict:
        return self.fs.copy(args["source"], args["destination"])

    def _exec_fs_delete(self, args: dict) -> dict:
        return self.fs.delete(args["path"])

    def _exec_fs_read_text(self, args: dict) -> dict:
        return self.fs.read_text(args["path"])

    def _exec_doc_extract_pdf(self, args: dict) -> dict:
        return self.fs.extract_pdf(args["path"])

    def _exec_sheet_write(self, args: dict) -> dict:
        return self.fs.write_xlsx(
            path=args["path"],
            rows=args["rows"],
            sheet_name=args.get("sheet_name", "Sheet1"),
            headers=args.get("headers"),
        )

    # ---- App Lifecycle ----

    def _exec_app_launch(self, args: dict) -> dict:
        return self.ui.launch_app(
            args["app_name"],
            args.get("args"),
        )

    def _exec_app_close(self, args: dict) -> dict:
        return self.ui.close_app(args["app_name"])

    # ---- L1: AT-SPI Action ----

    def _exec_ui_invoke(self, args: dict) -> dict:
        return self.ui.invoke_action(
            args["element_id"],
            args.get("action", "activate"),
        )

    # ---- L2: AT-SPI Text ----

    def _exec_ui_set_text(self, args: dict) -> dict:
        return self.ui.set_text(args["element_id"], args["text"])

    # ---- L3: Keyboard ----

    def _exec_ui_key(self, args: dict) -> dict:
        return self.keys.send_key(args["key"])

    # ---- L4: Coordinate Click ----

    def _exec_ui_click_xy(self, args: dict) -> dict:
        return self.ui.click_xy(int(args["x"]), int(args["y"]))

    # ---- L5: VLM Click (stretch goal) ----

    def _exec_ui_vlm_click(self, args: dict) -> dict:
        """VLM-guided click — last resort. Uses screenshot + VLM to find element."""
        # This is a stretch goal. For now, try OCR-based fallback or return error.
        description = args.get("description", "")
        logger.warning(f"VLM click requested for: {description} — not yet implemented, trying OCR fallback")
        raise NotImplementedError(
            "VLM-guided click is a stretch goal. "
            "Use ui.invoke, ui.click_xy, or ui.key instead."
        )

    # ---- Utility ----

    def _exec_web_wait(self, args: dict) -> dict:
        """Wait for text to appear on a web page (via HTTP check)"""
        import httpx

        url = args["url"]
        text = args["text"]
        timeout = args.get("timeout", 30)

        start = time.time()
        while time.time() - start < timeout:
            try:
                response = httpx.get(url, timeout=5, follow_redirects=True)
                if text in response.text:
                    return {"url": url, "text": text, "found": True}
            except Exception:
                pass
            time.sleep(1)

        return {"url": url, "text": text, "found": False, "timeout": True}
