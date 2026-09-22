from abc import ABC, abstractmethod
from typing import Any
from app.agent.models import ActionDefinition, VerificationResult

class Verifier(ABC):
    """
    Abstract interface for verifying if an action succeeded based on its expected state.
    """
    @abstractmethod
    def verify(self, action: ActionDefinition, execution_output: Any) -> VerificationResult:
        pass

class DeterministicVerifier(Verifier):
    """
    Deterministic verifier for testing.
    Always returns success unless expected_result is 'fail_verify'.
    """
    def verify(self, action: ActionDefinition, execution_output: Any) -> VerificationResult:
        if action.expected_result == "fail_verify":
            return VerificationResult(
                success=False,
                expected_state="fail_verify",
                actual_state="unknown",
                evidence={"output": execution_output},
                error="Mock verification failure"
            )
        
        return VerificationResult(
            success=True,
            expected_state=action.expected_result or "success",
            actual_state="success",
            evidence={"output": execution_output}
        )
