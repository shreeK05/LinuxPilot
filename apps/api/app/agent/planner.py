from abc import ABC, abstractmethod
from typing import List, Dict, Set
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
