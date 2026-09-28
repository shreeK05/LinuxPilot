"""
Planner Module
Generates execution plans from natural language goals using LLM
"""

from typing import Optional
from linuxpilot.models import Plan, Step, Risk, Postcondition
from linuxpilot.llm.gateway import LLMGateway
from linuxpilot.llm.cassette import CassetteManager
from linuxpilot.config import settings
import logging
import uuid

logger = logging.getLogger(__name__)


# Available action schemas for the LLM
ACTION_SCHEMAS = """
Available Actions and their parameter schemas:

- fs.list: {path: "directory path to list (supports ~)"}
- fs.stat: {path: "file path to get info (supports ~)"}
- fs.mkdir: {path: "directory path to create (supports ~)"}
- fs.move: {source: "source path (supports ~)", destination: "destination path (supports ~)"}
- fs.copy: {source: "source path (supports ~)", destination: "destination path (supports ~)"}
- fs.delete: {path: "path to delete (supports ~)"}
- fs.read_text: {path: "file path to read (supports ~)"}
- doc.extract_pdf: {path: "path to PDF file (supports ~)"}
- sheet.write: {path: "path to Excel file (supports ~)", rows: [["cell1", "cell2"]], sheet_name: "optional sheet name"}
- app.launch: {app_name: "application name (e.g., thunar, libreoffice, firefox)"}
- app.close: {app_name: "application name"}
- ui.invoke: {element_id: "AT-SPI element ID or role/name combo"}
- ui.set_text: {element_id: "AT-SPI element ID", text: "text to type"}
- ui.key: {key: "key combination (e.g., Ctrl+C, Enter)"}
- ui.click_xy: {x: int, y: int}
- ui.vlm_click: {description: "description of element to click"}
- web.wait_for_text: {url: "URL", text: "text to wait for", timeout: 30}
"""


SYSTEM_PROMPT = f"""
You are the Planning Engine for LinuxPilot. Your task is to generate a DAG (Directed Acyclic Graph) of executable steps to accomplish a user's goal.

{ACTION_SCHEMAS}

Rules:
1. ONLY use the available actions listed above.
2. Each step must have a unique step_id (use step-1, step-2, etc.).
3. Specify dependencies as a list of step_ids that must complete before this step.
4. Independent steps must have empty dependencies [].
5. NO CYCLES - the dependency graph must be acyclic.
6. To pass data between steps, use the EXACT step_id in the format: {{step_id.output.key}}. Never invent step IDs.
7. Each step must have at least one postcondition to verify success.
8. Postcondition types: fs.exists, fs.not_exists, fs.count, ui.element, xlsx.cell, http.record.
9. Risk levels: 0 (read-only), 1 (reversible), 2 (destructive), 3 (forbidden). Start with 0 for read operations, 1 for modifications.
10. The final step must always provide a summary of what was accomplished.
11. You MUST provide correct parameters for each action - no placeholders.
"""


USER_PROMPT_TEMPLATE = """
Goal: {goal}

Generate a valid execution plan to accomplish this goal.
"""


class Planner:
    """Base planner interface"""
    
    def create_plan(self, goal: str) -> Plan:
        """Create an execution plan from a natural language goal"""
        raise NotImplementedError
    
    def replan(
        self,
        goal: str,
        current_plan: Plan,
        failed_step: Step,
        error: str,
        executed_steps: list[str],
    ) -> Plan:
        """Generate a new plan after a failure"""
        raise NotImplementedError


class LLMPlanner(Planner):
    """
    LLM-based planner that generates execution plans
    """
    
    def __init__(self, llm_gateway: LLMGateway):
        self.llm = llm_gateway
    
    def create_plan(self, goal: str) -> Plan:
        """Create an execution plan using the LLM"""
        logger.info(f"Creating plan for goal: {goal}")
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(goal=goal)},
        ]
        
        # Use structured output for the plan
        response = self.llm.complete_structured(
            messages=messages,
            response_model=Plan,
            temperature=0.0,
            timeout=60,
        )
        
        logger.info(f"Created plan with {len(response.steps)} steps")
        return response
    
    def replan(
        self,
        goal: str,
        current_plan: Plan,
        failed_step: Step,
        error: str,
        executed_steps: list[str],
    ) -> Plan:
        """Generate a new plan after a failure"""
        logger.info(f"Replanning for failed step: {failed_step.id}")
        
        # Build context for the LLM
        executed_summary = "\n".join([
            f"- {step.id}: {step.intent} ({step.tool})"
            for step in current_plan.steps
            if step.id in executed_steps
        ])
        
        replan_prompt = f"""
Original Goal: {goal}

Completed Steps:
{executed_summary}

Failed Step:
- ID: {failed_step.id}
- Intent: {failed_step.intent}
- Tool: {failed_step.tool}
- Error: {error}

Generate a new valid execution plan that:
1. Preserves all completed steps with their exact step_ids
2. Fixes the failed step with a different approach
3. Completes the remaining goal
"""
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": replan_prompt},
        ]
        
        response = self.llm.complete_structured(
            messages=messages,
            response_model=Plan,
            temperature=0.2,  # Slightly higher temperature for creativity in recovery
            timeout=60,
        )
        
        logger.info(f"Replanned with {len(response.steps)} steps")
        return response
