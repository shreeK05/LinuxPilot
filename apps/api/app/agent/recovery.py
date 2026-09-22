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
        
        # Override allowed_retries if verification explicitly suggests a retry and we haven't maxed out the engine max
        if verification_result and getattr(verification_result, 'retry_suggested', False):
            allowed_retries = max(allowed_retries, 1) # Give it at least 1 retry if suggested
            
        if retry_count < allowed_retries:
            return RecoveryDecision(
                decision=RecoveryDecisionResult.RETRY,
                reason=f"Retrying action. Attempt {retry_count + 1} of {allowed_retries}."
            )
            
        if verification_result and not verification_result.success:
            return RecoveryDecision(
                decision=RecoveryDecisionResult.REPLAN,
                reason="Verification failed after retries. Replanning is required."
            )
            
        return RecoveryDecision(
            decision=RecoveryDecisionResult.FAIL,
            reason=f"Action failed and max retries ({allowed_retries}) exceeded."
        )
