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
                intent="Find and organize PDF files",
                objective="Find and organize PDF files in Downloads",
                entities=["*.pdf", "~/Downloads"],
                constraints=["Do not delete files", "Read-only search first"],
                preconditions=["Downloads directory exists"],
                expected_outcome="A list of all PDF files located in the Downloads directory.",
                risk_assessment="Low risk, read-only operation.",
                required_permissions=["Read access to ~/Downloads"],
                relevant_context="User is organizing documents."
            )
            
        # Default fallback deterministic goal
        return GoalUnderstanding(
            intent=raw_goal,
            objective=raw_goal,
            entities=[],
            constraints=[],
            preconditions=[],
            expected_outcome="Completion of the requested task.",
            risk_assessment="Unknown risk, fallback mode.",
            required_permissions=[],
            relevant_context="No context available."
        )

from app.agent.llm.provider import LLMProvider

class LLMGoalInterpreter(GoalInterpreter):
    """
    Interprets natural language goals using the configured LLM Provider.
    """
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.system_prompt = (
            "You are the Goal Understanding Engine for LinuxPilot, a high-end autonomous Linux agent. "
            "Your job is to read a user's natural language request and output a highly structured JSON object "
            "that matches the provided schema perfectly. "
            "Extract intent, entities, constraints, and preconditions. Assess the potential risk of the operation."
        )

    def interpret(self, raw_goal: str) -> GoalUnderstanding:
        return self.provider.generate_structured(
            prompt=raw_goal,
            system_prompt=self.system_prompt,
            response_model=GoalUnderstanding,
            temperature=0.0
        )
