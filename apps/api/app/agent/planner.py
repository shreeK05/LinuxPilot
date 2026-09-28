from abc import ABC, abstractmethod
from typing import List, Dict, Set, Any
from collections import deque
import uuid
from app.agent.models import GoalUnderstanding, ExecutionPlan, PlanStep, ActionDefinition, RiskLevel

class PlannerError(Exception):
    pass

class DAGValidator:
    @staticmethod
    def topological_sort(steps: List[PlanStep]) -> List[PlanStep]:
        # Build graph
        graph: Dict[str, List[str]] = {step.step_id: [] for step in steps}
        in_degree: Dict[str, int] = {step.step_id: 0 for step in steps}
        step_map: Dict[str, PlanStep] = {step.step_id: step for step in steps}

        for step in steps:
            for dep in step.dependencies:
                if dep not in graph:
                    raise PlannerError(f"Dependency {dep} not found in plan steps")
                graph[dep].append(step.step_id)
                in_degree[step.step_id] += 1

        # Kahn's algorithm
        queue = deque([node for node in in_degree if in_degree[node] == 0])
        sorted_steps = []

        while queue:
            node = queue.popleft()
            sorted_steps.append(step_map[node])

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_steps) != len(steps):
            raise PlannerError("Cycle detected in plan dependencies")

        return sorted_steps

class Planner(ABC):
    @abstractmethod
    def create_plan(self, goal: GoalUnderstanding) -> ExecutionPlan:
        pass

    @abstractmethod
    def replan(self, goal: GoalUnderstanding, current_plan: ExecutionPlan, failed_step: PlanStep, error: str, executed_steps: List[str]) -> ExecutionPlan:
        pass

class DeterministicPlanner(Planner):
    """
    Deterministic DAG Planner for testing and development.
    Do NOT use as a real planner.
    """
    def create_plan(self, goal: GoalUnderstanding) -> ExecutionPlan:
        # Map specific text from the Phase 3 manual test sequence to actual plans
        obj = goal.objective.lower()
        import os
        from pathlib import Path
        home_docs = str(Path.home() / "Documents")
        
        if "create a folder called linuxpilot-test" in obj:
            step1 = PlanStep(
                step_id="step-create",
                name="Create Test Folder",
                dependencies=[],
                action=ActionDefinition(
                    action_type="filesystem.create_directory",
                    parameters={"path": os.path.join(home_docs, "LinuxPilot-Test")},
                    risk_level=RiskLevel.LEVEL_2_MODIFY
                )
            )
            step2 = PlanStep(
                step_id="step-respond",
                name="Respond to user",
                dependencies=["step-create"],
                action=ActionDefinition(
                    action_type="agent.respond",
                    parameters={"content": "Successfully created the folder LinuxPilot-Test in your Documents directory."},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1, step2], risk_level=RiskLevel.LEVEL_2_MODIFY)
            
        elif "rename linuxpilot-test to linuxpilot-demo" in obj:
            step1 = PlanStep(
                step_id="step-rename",
                name="Rename Test Folder",
                dependencies=[],
                action=ActionDefinition(
                    action_type="filesystem.rename",
                    parameters={
                        "source": os.path.join(home_docs, "LinuxPilot-Test"),
                        "destination_name": "LinuxPilot-Demo"
                    },
                    risk_level=RiskLevel.LEVEL_2_MODIFY
                )
            )
            step2 = PlanStep(
                step_id="step-respond",
                name="Respond to user",
                dependencies=["step-rename"],
                action=ActionDefinition(
                    action_type="agent.respond",
                    parameters={"content": "Successfully renamed LinuxPilot-Test to LinuxPilot-Demo."},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1, step2], risk_level=RiskLevel.LEVEL_2_MODIFY)
            
        elif "delete linuxpilot-demo" in obj:
            step1 = PlanStep(
                step_id="step-delete",
                name="Delete Test Folder",
                dependencies=[],
                action=ActionDefinition(
                    action_type="filesystem.delete",
                    parameters={"path": os.path.join(home_docs, "LinuxPilot-Demo")},
                    risk_level=RiskLevel.LEVEL_4_DESTRUCTIVE
                )
            )
            step2 = PlanStep(
                step_id="step-respond",
                name="Respond to user",
                dependencies=["step-delete"],
                action=ActionDefinition(
                    action_type="agent.respond",
                    parameters={"content": "Successfully deleted the LinuxPilot-Demo folder."},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1, step2], risk_level=RiskLevel.LEVEL_4_DESTRUCTIVE)
            
        elif any(phrase in obj for phrase in ["architecture", "os ", "what os", "x64", "x86", "arm", "machine", "ubuntu", "kernel"]):
            step1 = PlanStep(
                step_id="step-os-info",
                name="Get OS Architecture",
                dependencies=[],
                action=ActionDefinition(
                    action_type="system.info",
                    parameters={"command": "os_info"},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            step2 = PlanStep(
                step_id="step-respond",
                name="Respond to user",
                dependencies=["step-os-info"],
                action=ActionDefinition(
                    action_type="agent.respond",
                    parameters={
                        "content": "You are running {{step-os-info.output.system}} {{step-os-info.output.release}} on {{step-os-info.output.machine}} architecture with kernel version {{step-os-info.output.version}}."
                    },
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1, step2], risk_level=RiskLevel.LEVEL_0_READ_ONLY)
            
        elif "list" in obj and "downloads" in obj:
            step1 = PlanStep(
                step_id="step-list-downloads",
                name="List Downloads",
                dependencies=[],
                action=ActionDefinition(
                    action_type="filesystem.list_directory",
                    parameters={"path": os.path.join(str(Path.home()), "Downloads")},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            step2 = PlanStep(
                step_id="step-respond",
                name="Respond to user",
                dependencies=["step-list-downloads"],
                action=ActionDefinition(
                    action_type="agent.respond",
                    parameters={"content": "Here are the files in your Downloads folder: {{step-list-downloads.output}}"},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1, step2], risk_level=RiskLevel.LEVEL_0_READ_ONLY)
            
        elif "pdf" in obj and "downloads" in obj:
            step1 = PlanStep(
                step_id="step-find-pdf",
                name="Find PDFs in Downloads",
                dependencies=[],
                action=ActionDefinition(
                    action_type="filesystem.find_files",
                    parameters={"path": os.path.join(str(Path.home()), "Downloads"), "pattern": "*.pdf"},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            step2 = PlanStep(
                step_id="step-respond",
                name="Respond to user",
                dependencies=["step-find-pdf"],
                action=ActionDefinition(
                    action_type="agent.respond",
                    parameters={"content": "I found the following PDFs in your Downloads folder: {{step-find-pdf.output}}"},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1, step2], risk_level=RiskLevel.LEVEL_0_READ_ONLY)
            
        elif "make a lab folder" in obj or ("create" in obj and "lab" in obj):
            step1 = PlanStep(
                step_id="step-create-lab",
                name="Create LAB Folder",
                dependencies=[],
                action=ActionDefinition(
                    action_type="filesystem.create_directory",
                    parameters={"path": os.path.join(str(Path.home()), "Downloads", "LAB")},
                    risk_level=RiskLevel.LEVEL_2_MODIFY
                )
            )
            step2 = PlanStep(
                step_id="step-respond",
                name="Respond to user",
                dependencies=["step-create-lab"],
                action=ActionDefinition(
                    action_type="agent.respond",
                    parameters={"content": "Successfully created the LAB folder in your Downloads directory."},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1, step2], risk_level=RiskLevel.LEVEL_2_MODIFY)
            
        elif "delete the lab folder" in obj or ("delete" in obj and "lab" in obj):
            step1 = PlanStep(
                step_id="step-delete-lab",
                name="Delete LAB Folder",
                dependencies=[],
                action=ActionDefinition(
                    action_type="filesystem.delete",
                    parameters={"path": os.path.join(str(Path.home()), "Downloads", "LAB")},
                    risk_level=RiskLevel.LEVEL_4_DESTRUCTIVE
                )
            )
            step2 = PlanStep(
                step_id="step-respond",
                name="Respond to user",
                dependencies=["step-delete-lab"],
                action=ActionDefinition(
                    action_type="agent.respond",
                    parameters={"content": "Successfully deleted the LAB folder."},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1, step2], risk_level=RiskLevel.LEVEL_4_DESTRUCTIVE)
            
        elif "modified today" in obj:
            step1 = PlanStep(
                step_id="step-find-modified",
                name="Find recently modified",
                dependencies=[],
                action=ActionDefinition(
                    action_type="filesystem.find_files",
                    parameters={"path": os.path.join(str(Path.home())), "pattern": "*"},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            step2 = PlanStep(
                step_id="step-respond",
                name="Respond to user",
                dependencies=["step-find-modified"],
                action=ActionDefinition(
                    action_type="agent.respond",
                    parameters={"content": "Here are the files recently modified: {{step-find-modified.output}}"},
                    risk_level=RiskLevel.LEVEL_0_READ_ONLY
                )
            )
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1, step2], risk_level=RiskLevel.LEVEL_0_READ_ONLY)

        
        # Fallback for old tests or generic actions
        step1 = PlanStep(
            step_id="step-fallback",
            name="Generic Info",
            dependencies=[],
            action=ActionDefinition(
                action_type="system.info",
                parameters={"command": "disk_usage"},
                risk_level=RiskLevel.LEVEL_0_READ_ONLY
            )
        )
        step2 = PlanStep(
            step_id="step-respond",
            name="Respond to user",
            dependencies=["step-fallback"],
            action=ActionDefinition(
                action_type="agent.respond",
                parameters={
                    "content": "Your system disk usage is at {{step-fallback.output.percent}}%. You have {{step-fallback.output.free_gb}} GB free out of {{step-fallback.output.total_gb}} GB."
                },
                risk_level=RiskLevel.LEVEL_0_READ_ONLY
            )
        )
        return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1, step2], risk_level=RiskLevel.LEVEL_0_READ_ONLY)

    def replan(self, goal: GoalUnderstanding, current_plan: ExecutionPlan, failed_step: PlanStep, error: str, executed_steps: List[str]) -> ExecutionPlan:
        # Mock replan for testing
        step_replan = PlanStep(
            step_id="step-replanned",
            name="Replanned Action",
            dependencies=[],
            action=ActionDefinition(
                action_type="system.info",
                parameters={"command": "replanned"},
                risk_level=RiskLevel.LEVEL_0_READ_ONLY
            )
        )
        # Preserve executed steps from current_plan to simulate DAG regeneration 
        steps = [s for s in current_plan.steps if s.step_id in executed_steps]
        steps.append(step_replan)
        return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=steps, risk_level=RiskLevel.LEVEL_0_READ_ONLY)

from app.agent.llm.provider import LLMProvider
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from typing import Optional, Union, List

class LLMActionParameters(BaseModel):
    model_config = ConfigDict(extra="ignore")

    command: Optional[Union[str, List[str]]] = None
    path: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    destination_name: Optional[str] = None
    task_id: Optional[str] = None
    sheet_name: Optional[str] = None
    rows: Optional[List[List[str]]] = None
    url: Optional[str] = None
    selector: Optional[str] = None
    value: Optional[str] = None

class LLMVerificationRequirements(BaseModel):
    model_config = ConfigDict(extra="ignore")

    method: Optional[str] = None
    expected_content: Optional[str] = None
    timeout: Optional[int] = None

class LLMActionDef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    action_type: str
    parameters: LLMActionParameters
    expected_result: Optional[str] = None
    verification_requirements: Optional[LLMVerificationRequirements] = None

class LLMPlanStep(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    step_id: str
    name: str
    dependencies: List[str]
    action: LLMActionDef

class LLMPlanResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    steps: List[LLMPlanStep]

class LLMPlanner(Planner):
    """
    Uses an LLMProvider to generate a hierarchical DAG of steps.
    """
    def __init__(self, provider: LLMProvider, registry):
        self.provider = provider
        self.registry = registry

    def create_plan(self, goal: GoalUnderstanding) -> ExecutionPlan:
        # Build prompt using available actions
        available_actions = []
        for a_type, handler in self.registry._handlers.items():
            available_actions.append(a_type)
            
        action_schemas = """
        - system.info: {command: "disk_usage" | "memory_usage" | "cpu_info" | "os_info"}
        - filesystem.list_directory: {path: "path to list (supports ~/)"}
        - filesystem.find_files: {path: "dir to search (supports ~/)", pattern: "file pattern like *.pdf"}
        - filesystem.stat: {path: "file path (supports ~/)"}
        - filesystem.read_file: {path: "file path (supports ~/)"}
        - filesystem.create_directory: {path: "path to create (supports ~/)"}
        - filesystem.copy: {source: "old path (supports ~/)", destination: "new path (supports ~/)"}
        - filesystem.move: {source: "old path (supports ~/)", destination: "new path (supports ~/)"}
        - filesystem.rename: {source: "old path (supports ~/)", destination_name: "new name"}
        - filesystem.write_file: {path: "file path (supports ~/)", content: "file content"}
        - filesystem.delete: {path: "path to delete (supports ~/)"}
        - document.pdf.extract_text: {path: "path to pdf (supports ~/)"}
        - document.xlsx.read: {path: "path to file (supports ~/)", sheet_name: "optional sheet name"}
        - document.xlsx.write: {path: "path to file (supports ~/)", rows: [["cell1", "cell2"]], sheet_name: "optional sheet name"}
        - browser.navigate: {url: "url to navigate to"}
        - browser.extract: {selector: "CSS selector (optional, if omitted extracts full page text)"}
        - browser.fill: {selector: "CSS selector", value: "text to type"}
        - browser.click: {selector: "CSS selector"}
        - browser.submit: {selector: "CSS selector of button"}
        - agent.respond: {content: "natural language response. Can use {{step_id.output.key}}"}
        """
            
        system_prompt = (
            "You are the Planning Engine for LinuxPilot. Your task is to generate a DAG of executable steps.\n"
            f"AVAILABLE ACTIONS: {', '.join(available_actions)}\n\n"
            f"ACTION PARAMETER SCHEMAS:\n{action_schemas}\n\n"
            "Rules:\n"
            "1. ONLY use available actions.\n"
            "2. Ensure step_ids are unique.\n"
            "3. Specify dependencies as a list of step_ids.\n"
            "4. Independent steps must have empty dependencies.\n"
            "5. NO CYCLES.\n"
            "6. To pass data between steps, YOU MUST use the EXACT step_id of the previous step in the variable: {{EXACT_STEP_ID.output.key}}. Never invent step IDs.\n"
            "7. The 'expected_result' field MUST only describe the expected outcome of THAT SPECIFIC STEP, not the entire goal.\n"
            "8. YOU MUST PROVIDE THE CORRECT PARAMETERS FOR EACH ACTION.\n"
            "9. THE FINAL STEP IN YOUR DAG MUST ALWAYS BE AN 'agent.respond' ACTION that summarizes the overall results in a conversational way to the user."
        )
        
        user_prompt = f"Goal Intent: {goal.intent}\nObjective: {goal.objective}\nEntities: {goal.entities}"
        
        llm_response = self.provider.generate_structured(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_model=LLMPlanResponse,
            temperature=0.0
        )
        
        steps = []
        highest_risk = RiskLevel.LEVEL_0_READ_ONLY
        
        for llm_step in llm_response.steps:
            if llm_step.action.action_type not in self.registry._handlers:
                raise PlannerError(f"LLM proposed unknown action: {llm_step.action.action_type}")
                
            # For phase 4, we evaluate risk using our existing policy engine inside the orchestrator
            # We'll default to LEVEL_0 here and let the Policy Engine elevate it before execution!
            # Wait, the blueprint says risk classification should be generated, but our Policy Engine handles it.
            # We'll set a default here, the orchestrator upgrades it.
            
            action_def = ActionDefinition(
                action_type=llm_step.action.action_type,
                parameters=llm_step.action.parameters.model_dump(exclude_none=True),
                expected_result=llm_step.action.expected_result,
                verification_requirements=llm_step.action.verification_requirements.model_dump(exclude_none=True) if llm_step.action.verification_requirements else None
            )
            
            steps.append(PlanStep(
                step_id=llm_step.step_id,
                name=llm_step.name,
                dependencies=llm_step.dependencies,
                action=action_def
            ))
            
        DAGValidator.topological_sort(steps)
        
        return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=steps, risk_level=highest_risk)

    def replan(self, goal: GoalUnderstanding, current_plan: ExecutionPlan, failed_step: PlanStep, error: str, executed_steps: List[str]) -> ExecutionPlan:
        available_actions = list(self.registry._handlers.keys())
        
        action_schemas = """
        - system.info: {command: "disk_usage" | "memory_usage" | "cpu_info" | "os_info"}
        - filesystem.list_directory: {path: "path to list (supports ~/)"}
        - filesystem.find_files: {path: "dir to search (supports ~/)", pattern: "file pattern like *.pdf"}
        - filesystem.stat: {path: "file path (supports ~/)"}
        - filesystem.read_file: {path: "file path (supports ~/)"}
        - filesystem.create_directory: {path: "path to create (supports ~/)"}
        - filesystem.copy: {source: "old path (supports ~/)", destination: "new path (supports ~/)"}
        - filesystem.move: {source: "old path (supports ~/)", destination: "new path (supports ~/)"}
        - filesystem.rename: {source: "old path (supports ~/)", destination_name: "new name"}
        - filesystem.write_file: {path: "file path (supports ~/)", content: "file content"}
        - filesystem.delete: {path: "path to delete (supports ~/)"}
        - document.pdf.extract_text: {path: "path to pdf (supports ~/)"}
        - document.xlsx.read: {path: "path to file (supports ~/)", sheet_name: "optional sheet name"}
        - document.xlsx.write: {path: "path to file (supports ~/)", rows: [["cell1", "cell2"]], sheet_name: "optional sheet name"}
        - browser.navigate: {url: "url to navigate to"}
        - browser.extract: {selector: "CSS selector (optional, if omitted extracts full page text)"}
        - browser.fill: {selector: "CSS selector", value: "text to type"}
        - browser.click: {selector: "CSS selector"}
        - browser.submit: {selector: "CSS selector of button"}
        - agent.respond: {content: "natural language response. Can use {{step_id.output.key}}"}
        """
        
        system_prompt = (
            "You are the Replanning Engine for LinuxPilot.\n"
            "An execution or verification failure occurred. You must generate a new DAG of executable steps.\n"
            f"AVAILABLE ACTIONS: {', '.join(available_actions)}\n\n"
            f"ACTION PARAMETER SCHEMAS:\n{action_schemas}\n\n"
            "Rules:\n"
            "1. ONLY use available actions.\n"
            "2. Ensure step_ids are unique.\n"
            "3. Specify dependencies as a list of step_ids.\n"
            "4. NO CYCLES.\n"
            "5. The new plan MUST preserve and include steps that already succeeded, mapping exactly to their old step_ids.\n"
            "6. Provide a new strategy to accomplish the failed step/remaining goal.\n"
            "7. To pass data between steps, YOU MUST use the EXACT step_id of the previous step in the variable: {{EXACT_STEP_ID.output.key}}. Never invent step IDs.\n"
            "8. The 'expected_result' field MUST only describe the expected outcome of THAT SPECIFIC STEP, not the entire goal.\n"
            "9. YOU MUST PROVIDE THE CORRECT PARAMETERS FOR EACH ACTION.\n"
            "10. THE FINAL STEP IN YOUR DAG MUST ALWAYS BE AN 'agent.respond' ACTION that summarizes the overall results in a conversational way to the user."
        )
        
        # Serialize executed steps
        completed = []
        for s in current_plan.steps:
            if s.step_id in executed_steps:
                completed.append(f"- [{s.step_id}] {s.name}: {s.action.action_type}")
                
        # Truncate error context to prevent LLM context limit bounds
        truncated_error = error
        if error and len(error) > 5000:
            truncated_error = error[:5000] + "\n...[TRUNCATED]"

        user_prompt = (
            f"Goal: {goal.intent}\n"
            f"Completed Steps:\n{chr(10).join(completed) if completed else 'None'}\n\n"
            f"Failed Step: [{failed_step.step_id}] {failed_step.name}\n"
            f"Error/Verification Output:\n{truncated_error}\n\n"
            "Generate a new valid DAG."
        )
        
        llm_response = self.provider.generate_structured(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_model=LLMPlanResponse,
            temperature=0.2
        )
        
        steps = []
        highest_risk = RiskLevel.LEVEL_0_READ_ONLY
        
        for llm_step in llm_response.steps:
            if llm_step.action.action_type not in self.registry._handlers:
                raise PlannerError(f"LLM proposed unknown action: {llm_step.action.action_type}")
                
            action_def = ActionDefinition(
                action_type=llm_step.action.action_type,
                parameters=llm_step.action.parameters.model_dump(exclude_none=True),
                expected_result=llm_step.action.expected_result,
                verification_requirements=llm_step.action.verification_requirements.model_dump(exclude_none=True) if llm_step.action.verification_requirements else None
            )
            
            steps.append(PlanStep(
                step_id=llm_step.step_id,
                name=llm_step.name,
                dependencies=llm_step.dependencies,
                action=action_def
            ))
            
        DAGValidator.topological_sort(steps)
        
        return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=steps, risk_level=highest_risk)
