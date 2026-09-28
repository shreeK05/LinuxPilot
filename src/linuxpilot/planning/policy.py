"""
Policy Engine
Deterministic risk classification and path confinement
"""

import os
from typing import Dict
from linuxpilot.models import Risk, Tool, Step, ExecutionContext
from linuxpilot.config import settings
import logging

logger = logging.getLogger(__name__)


# Base risk levels for each tool (LLM can only raise, never lower)
BASE_RISK: Dict[Tool, Risk] = {
    "fs.list": Risk.READ_ONLY,
    "fs.stat": Risk.READ_ONLY,
    "fs.read_text": Risk.READ_ONLY,
    "doc.extract_pdf": Risk.READ_ONLY,
    "web.wait_for_text": Risk.READ_ONLY,
    "fs.mkdir": Risk.REVERSIBLE,
    "fs.copy": Risk.REVERSIBLE,
    "fs.move": Risk.REVERSIBLE,
    "sheet.write": Risk.REVERSIBLE,
    "app.launch": Risk.REVERSIBLE,
    "app.close": Risk.REVERSIBLE,
    "ui.invoke": Risk.REVERSIBLE,
    "ui.set_text": Risk.REVERSIBLE,
    "ui.key": Risk.REVERSIBLE,
    "ui.click_xy": Risk.REVERSIBLE,
    "ui.vlm_click": Risk.REVERSIBLE,
    "fs.delete": Risk.DESTRUCTIVE,
}


class PolicyEngine:
    """
    Deterministic policy engine for risk classification and path confinement
    """
    
    def __init__(self):
        self.base_risk = BASE_RISK
    
    def classify(self, step: Step, context: ExecutionContext) -> Risk:
        """
        Classify the risk level of a step
        
        Rules:
        1. Start with base risk for the tool
        2. Check path confinement - if path escapes allowed roots, return FORBIDDEN
        3. If LLM classified as higher risk, take the max (LLM can only raise)
        4. Special cases (e.g., overwriting existing files) may elevate risk
        """
        # Get base risk
        tool_risk = self.base_risk.get(step.tool, Risk.FORBIDDEN)
        
        # If tool is unknown, it's forbidden
        if tool_risk == Risk.FORBIDDEN:
            logger.warning(f"Unknown tool: {step.tool}")
            return Risk.FORBIDDEN
        
        # Check path confinement
        if self._check_path_confinement(step, context) == Risk.FORBIDDEN:
            return Risk.FORBIDDEN
        
        # Check for destructive operations
        if self._is_destructive_operation(step, context):
            tool_risk = max(tool_risk, Risk.DESTRUCTIVE)
        
        # LLM can only raise risk, never lower it
        final_risk = max(tool_risk, step.risk_llm)
        
        logger.debug(f"Policy classification: {step.tool} -> {final_risk}")
        return final_risk
    
    def _check_path_confinement(self, step: Step, context: ExecutionContext) -> Risk:
        """
        Check if all paths in step args are within allowed roots
        Returns FORBIDDEN if any path escapes
        """
        path_args = self._extract_paths(step.args)
        
        for path in path_args:
            # Expand user home
            expanded = os.path.expanduser(path)
            # Resolve to absolute path
            real_path = os.path.realpath(expanded)
            
            # Check if within any allowed root
            allowed = False
            for root in context.allowed_roots:
                expanded_root = os.path.expanduser(root)
                real_root = os.path.realpath(expanded_root)
                if real_path.startswith(real_root):
                    allowed = True
                    break
            
            if not allowed:
                logger.warning(f"Path {real_path} escapes allowed roots {context.allowed_roots}")
                return Risk.FORBIDDEN
        
        return Risk.READ_ONLY  # No violation
    
    def _extract_paths(self, args: dict) -> list[str]:
        """Extract all file paths from step arguments"""
        paths = []
        
        # Common path argument names
        path_keys = ["path", "source", "destination", "file"]
        
        for key, value in args.items():
            if key in path_keys and isinstance(value, str):
                paths.append(value)
            elif key == "files" and isinstance(value, list):
                paths.extend([f for f in value if isinstance(f, str)])
        
        return paths
    
    def _is_destructive_operation(self, step: Step, context: ExecutionContext) -> bool:
        """
        Check if the operation is destructive (e.g., overwrites existing files)
        """
        if step.tool == "fs.move":
            source = step.args.get("source")
            destination = step.args.get("destination")
            
            if source and destination:
                # Check if destination exists
                expanded_dest = os.path.expanduser(destination)
                if os.path.exists(expanded_dest):
                    logger.warning(f"Move operation would overwrite: {destination}")
                    return True
        
        return False
    
    def should_require_approval(self, risk: Risk) -> bool:
        """Determine if a step requires human approval"""
        return risk >= Risk.DESTRUCTIVE
    
    def should_block(self, risk: Risk) -> bool:
        """Determine if a step should be blocked entirely"""
        return risk == Risk.FORBIDDEN
