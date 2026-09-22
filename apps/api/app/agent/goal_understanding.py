from abc import ABC, abstractmethod
from typing import Optional
from app.agent.models import GoalUnderstanding

class GoalInterpreter(ABC):
    """
    Abstract interface for interpreting natural language goals into structured goals.
    Future implementations will include LocalLLMGoalInterpreter, CloudLLMGoalInterpreter, etc.
    """
    @abstractmethod
    def interpret(self, raw_goal: str) -> GoalUnderstanding:
        pass

class DeterministicGoalInterpreter(GoalInterpreter):
    """
    Deterministic implementation for testing and development.
    Do NOT use in production as a replacement for real LLM interpretation.
    """
    def interpret(self, raw_goal: str) -> GoalUnderstanding:
        # Simple deterministic parsing for testing
        lower_goal = raw_goal.lower()
        
        if "pdf" in lower_goal and "download" in lower_goal:
            return GoalUnderstanding(
                objective="Find and organize PDF files in Downloads",
                entities=["*.pdf", "~/Downloads"],
                constraints=["Do not delete files", "Read-only search first"],
                requested_operations=["search", "list"],
                expected_outcome="A list of all PDF files located in the Downloads directory."
            )
            
        # Default fallback deterministic goal
        return GoalUnderstanding(
            objective=raw_goal,
            entities=[],
            constraints=[],
            requested_operations=["unknown"],
            expected_outcome="Completion of the requested task."
        )
