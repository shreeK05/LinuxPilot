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
        # A simple branching plan for testing
        step1 = PlanStep(
            step_id="step-1",
            name="Initialize",
            dependencies=[],
            action=ActionDefinition(
                action_type="test.init",
                parameters={"target": "system"},
                risk_level=RiskLevel.LEVEL_0_READ_ONLY
            )
        )
        
        step2 = PlanStep(
            step_id="step-2",
            name="Search",
            dependencies=["step-1"],
            action=ActionDefinition(
                action_type="test.search",
                parameters={"query": goal.objective},
                risk_level=RiskLevel.LEVEL_0_READ_ONLY
            )
        )
        
        step3 = PlanStep(
            step_id="step-3",
            name="Validate",
            dependencies=["step-1"], # Parallel with step 2
            action=ActionDefinition(
                action_type="test.validate",
                parameters={"constraints": goal.constraints},
                risk_level=RiskLevel.LEVEL_0_READ_ONLY
            )
        )
        
        step4 = PlanStep(
            step_id="step-4",
            name="Finalize",
            dependencies=["step-2", "step-3"],
            action=ActionDefinition(
                action_type="test.finalize",
                parameters={"outcome": goal.expected_outcome},
                risk_level=RiskLevel.LEVEL_1_NON_DESTRUCTIVE
            )
        )
        
        steps = [step1, step2, step3, step4]
        
        # Validate and sort before returning
        DAGValidator.topological_sort(steps)
        
        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            steps=steps,
            risk_level=RiskLevel.LEVEL_1_NON_DESTRUCTIVE
        )
