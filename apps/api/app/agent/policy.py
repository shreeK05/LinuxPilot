from app.agent.models import ActionDefinition, PolicyDecision, PolicyDecisionResult, RiskLevel

class RiskClassifier:
    """
    Classifies the risk level of an action.
    """
    def classify(self, action: ActionDefinition) -> RiskLevel:
        # In a real system, this would analyze action parameters and type.
        # For Phase 2, we trust the action's defined risk_level.
        return action.risk_level

class PolicyEngine:
    """
    Evaluates actions against security policies to determine allowed executions.
    """
    def __init__(self):
        self.classifier = RiskClassifier()
        self.max_allowed_risk = RiskLevel.LEVEL_4_DESTRUCTIVE

    def evaluate(self, action: ActionDefinition) -> PolicyDecision:
        risk_level = self.classifier.classify(action)
        
        if risk_level == RiskLevel.LEVEL_5_BLOCKED:
            return PolicyDecision(
                decision=PolicyDecisionResult.BLOCK,
                reason="Action risk level is explicitly blocked by policy.",
                risk_level=risk_level
            )
            
        if risk_level > self.max_allowed_risk:
            return PolicyDecision(
                decision=PolicyDecisionResult.BLOCK,
                reason=f"Action risk level ({risk_level}) exceeds maximum allowed ({self.max_allowed_risk}).",
                risk_level=risk_level
            )
            
        if risk_level >= RiskLevel.LEVEL_3_HIGH_IMPACT:
            return PolicyDecision(
                decision=PolicyDecisionResult.REQUIRE_SNAPSHOT,
                reason="High impact action requires a system snapshot before execution.",
                risk_level=risk_level
            )
            
        if risk_level >= RiskLevel.LEVEL_2_MODIFY:
            return PolicyDecision(
                decision=PolicyDecisionResult.REQUIRE_APPROVAL,
                reason="Modifying action requires explicit user approval.",
                risk_level=risk_level
            )
            
        return PolicyDecision(
            decision=PolicyDecisionResult.ALLOW,
            reason="Action is safe to execute.",
            risk_level=risk_level
        )
