from app.agent.models import ActionDefinition, PolicyDecision, PolicyDecisionResult, RiskLevel

class RiskClassifier:
    """
    Classifies the risk level of an action.
    """
    def classify(self, action: ActionDefinition) -> RiskLevel:
        # Enforce phase 3 rules dynamically if risk level is not declared properly
        # But in Phase 3, we map based on explicit action type
        if action.action_type in ["system.info", "filesystem.list_directory", "filesystem.stat", "process.list"]:
            return RiskLevel.LEVEL_0_READ_ONLY
        elif action.action_type in ["filesystem.read_file"]:
            return RiskLevel.LEVEL_1_NON_DESTRUCTIVE
        elif action.action_type in ["filesystem.create_directory", "filesystem.copy", "filesystem.rename", "filesystem.move", "filesystem.write_file"]:
            return RiskLevel.LEVEL_2_MODIFY
        elif action.action_type in ["filesystem.delete"]:
            return RiskLevel.LEVEL_4_DESTRUCTIVE
        elif action.action_type.startswith("terminal.execute") or action.action_type.startswith("shell"):
            return RiskLevel.LEVEL_5_BLOCKED
            
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
