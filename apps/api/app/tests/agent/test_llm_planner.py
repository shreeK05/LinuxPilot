import pytest
from app.agent.llm.provider import MockProvider, LLMProviderError
from app.agent.planner import LLMPlanner, PlannerError
from app.agent.goal_understanding import LLMGoalInterpreter
from app.agent.models import GoalUnderstanding
from app.agent.actions.registry import ActionRegistry, ActionHandler

class DummyHandler(ActionHandler):
    def execute(self, action):
        pass

@pytest.fixture
def mock_registry():
    registry = ActionRegistry()
    registry.register("filesystem.create_directory", DummyHandler())
    registry.register("filesystem.write_file", DummyHandler())
    registry.register("system.memory", DummyHandler())
    registry.register("system.disk", DummyHandler())
    return registry

@pytest.fixture
def goal():
    return GoalUnderstanding(
        intent="Test goal",
        objective="Do a test",
        expected_outcome="Test done",
        risk_assessment="Low"
    )

def test_valid_sequential_dag(mock_registry, goal):
    mock_responses = {
        "LLMPlanResponse": {
            "steps": [
                {
                    "step_id": "step1",
                    "name": "Create dir",
                    "dependencies": [],
                    "action": {"action_type": "filesystem.create_directory", "parameters": {"path": "/tmp/test"}}
                },
                {
                    "step_id": "step2",
                    "name": "Write file",
                    "dependencies": ["step1"],
                    "action": {"action_type": "filesystem.write_file", "parameters": {"path": "/tmp/test/f.txt", "content": "hi"}}
                },
                {
                    "step_id": "step3",
                    "name": "Check mem",
                    "dependencies": ["step2"],
                    "action": {"action_type": "system.memory", "parameters": {}}
                }
            ]
        }
    }
    
    provider = MockProvider(mock_responses=mock_responses)
    planner = LLMPlanner(provider, mock_registry)
    
    plan = planner.create_plan(goal)
    assert len(plan.steps) == 3
    assert plan.steps[0].step_id == "step1"
    assert plan.steps[2].step_id == "step3"

def test_parallel_dag(mock_registry, goal):
    mock_responses = {
        "LLMPlanResponse": {
            "steps": [
                {
                    "step_id": "step1",
                    "name": "Check mem",
                    "dependencies": [],
                    "action": {"action_type": "system.memory", "parameters": {}}
                },
                {
                    "step_id": "step2",
                    "name": "Check disk",
                    "dependencies": [],
                    "action": {"action_type": "system.disk", "parameters": {}}
                }
            ]
        }
    }
    
    provider = MockProvider(mock_responses=mock_responses)
    planner = LLMPlanner(provider, mock_registry)
    
    plan = planner.create_plan(goal)
    assert len(plan.steps) == 2
    assert plan.steps[0].dependencies == []
    assert plan.steps[1].dependencies == []

def test_unknown_action_rejected(mock_registry, goal):
    mock_responses = {
        "LLMPlanResponse": {
            "steps": [
                {
                    "step_id": "step1",
                    "name": "Format disk",
                    "dependencies": [],
                    "action": {"action_type": "filesystem.format_disk", "parameters": {}}
                }
            ]
        }
    }
    
    provider = MockProvider(mock_responses=mock_responses)
    planner = LLMPlanner(provider, mock_registry)
    
    with pytest.raises(PlannerError, match="LLM proposed unknown action"):
        planner.create_plan(goal)

def test_cyclic_dag_rejected(mock_registry, goal):
    mock_responses = {
        "LLMPlanResponse": {
            "steps": [
                {
                    "step_id": "step1",
                    "name": "Task A",
                    "dependencies": ["step2"],
                    "action": {"action_type": "system.memory", "parameters": {}}
                },
                {
                    "step_id": "step2",
                    "name": "Task B",
                    "dependencies": ["step1"],
                    "action": {"action_type": "system.disk", "parameters": {}}
                }
            ]
        }
    }
    
    provider = MockProvider(mock_responses=mock_responses)
    planner = LLMPlanner(provider, mock_registry)
    
    with pytest.raises(PlannerError, match="Cycle detected"):
        planner.create_plan(goal)

def test_missing_dependency_rejected(mock_registry, goal):
    mock_responses = {
        "LLMPlanResponse": {
            "steps": [
                {
                    "step_id": "step1",
                    "name": "Task A",
                    "dependencies": ["step-missing"],
                    "action": {"action_type": "system.memory", "parameters": {}}
                }
            ]
        }
    }
    
    provider = MockProvider(mock_responses=mock_responses)
    planner = LLMPlanner(provider, mock_registry)
    
    with pytest.raises(PlannerError, match="not found in plan steps"):
        planner.create_plan(goal)

def test_provider_error(mock_registry, goal):
    provider = MockProvider(mock_responses={}) # Empty mocks will raise LLMProviderError
    planner = LLMPlanner(provider, mock_registry)
    
    with pytest.raises(LLMProviderError):
        planner.create_plan(goal)
