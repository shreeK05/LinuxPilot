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
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1], risk_level=RiskLevel.LEVEL_2_MODIFY)
            
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
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1], risk_level=RiskLevel.LEVEL_2_MODIFY)
            
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
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1], risk_level=RiskLevel.LEVEL_4_DESTRUCTIVE)
        
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
        return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step1], risk_level=RiskLevel.LEVEL_0_READ_ONLY)

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
from pydantic import BaseModel, Field
from typing import Optional

class LLMActionDef(BaseModel):
    action_type: str
    parameters: Dict[str, Any]
    expected_result: Optional[str] = None
    verification_requirements: Optional[Dict[str, Any]] = None

class LLMPlanStep(BaseModel):
    step_id: str
    name: str
    dependencies: List[str]
    action: LLMActionDef

class LLMPlanResponse(BaseModel):
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
            
        system_prompt = (
            "You are the Planning Engine for LinuxPilot. Your task is to generate a DAG of executable steps.\n"
            f"AVAILABLE ACTIONS: {', '.join(available_actions)}\n\n"
            "Rules:\n"
            "1. ONLY use available actions.\n"
            "2. Ensure step_ids are unique.\n"
            "3. Specify dependencies as a list of step_ids.\n"
            "4. Independent steps must have empty dependencies.\n"
            "5. NO CYCLES."
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
                parameters=llm_step.action.parameters,
                expected_result=llm_step.action.expected_result,
                verification_requirements=llm_step.action.verification_requirements
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
        
        system_prompt = (
            "You are the Replanning Engine for LinuxPilot.\n"
            "An execution or verification failure occurred. You must generate a new DAG of executable steps.\n"
            f"AVAILABLE ACTIONS: {', '.join(available_actions)}\n\n"
            "Rules:\n"
            "1. ONLY use available actions.\n"
            "2. Ensure step_ids are unique.\n"
            "3. Specify dependencies as a list of step_ids.\n"
            "4. NO CYCLES.\n"
            "5. The new plan MUST preserve and include steps that already succeeded, mapping exactly to their old step_ids.\n"
            "6. Provide a new strategy to accomplish the failed step/remaining goal.\n"
        )
        
        # Serialize executed steps
        completed = []
        for s in current_plan.steps:
            if s.step_id in executed_steps:
                completed.append(f"- [{s.step_id}] {s.name}: {s.action.action_type}")
                
        user_prompt = (
            f"Goal: {goal.intent}\n"
            f"Completed Steps:\n{chr(10).join(completed) if completed else 'None'}\n\n"
            f"Failed Step: [{failed_step.step_id}] {failed_step.name}\n"
            f"Error/Verification Output:\n{error}\n\n"
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
                parameters=llm_step.action.parameters,
                expected_result=llm_step.action.expected_result,
                verification_requirements=llm_step.action.verification_requirements
            )
            
            steps.append(PlanStep(
                step_id=llm_step.step_id,
                name=llm_step.name,
                dependencies=llm_step.dependencies,
                action=action_def
            ))
            
        DAGValidator.topological_sort(steps)
        
        return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=steps, risk_level=highest_risk)
