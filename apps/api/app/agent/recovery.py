from app.agent.models import ActionDefinition, RecoveryDecision, RecoveryDecisionResult, VerificationResult
from typing import Optional

class RecoveryEngine:
    """
    Determines recovery strategy when an action or verification fails.
    """
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def determine_recovery(self, action: ActionDefinition, failure_reason: str, retry_count: int, verification_result: Optional[VerificationResult] = None) -> RecoveryDecision:
        
        # Check explicit retry policy from action or fallback to engine max
        allowed_retries = min(action.retry_policy, self.max_retries)
        
        if retry_count < allowed_retries:
            return RecoveryDecision(
                decision=RecoveryDecisionResult.RETRY,
                reason=f"Retrying action. Attempt {retry_count + 1} of {allowed_retries}."
            )
            
        # If retries exhausted, we could replan or ask user. For now, fail or replan based on some dummy logic.
        # Let's say if it fails verification it might trigger replan, else fail.
        if verification_result and not verification_result.success:
            return RecoveryDecision(
                decision=RecoveryDecisionResult.REPLAN,
                reason="Verification failed after retries. Replanning is required."
            )
            
        return RecoveryDecision(
            decision=RecoveryDecisionResult.FAIL,
            reason=f"Action failed and max retries ({allowed_retries}) exceeded."
        )
