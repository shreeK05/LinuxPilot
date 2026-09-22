from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

class AgentState(str, Enum):
    IDLE = "IDLE"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    POLICY_CHECK = "POLICY_CHECK"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    READY = "READY"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RETRYING = "RETRYING"
    REPLANNING = "REPLANNING"
    ROLLING_BACK = "ROLLING_BACK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class RiskLevel(int, Enum):
    LEVEL_0_READ_ONLY = 0
    LEVEL_1_NON_DESTRUCTIVE = 1
    LEVEL_2_MODIFY = 2
    LEVEL_3_HIGH_IMPACT = 3
    LEVEL_4_DESTRUCTIVE = 4
    LEVEL_5_BLOCKED = 5

class PolicyDecisionResult(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REQUIRE_SNAPSHOT = "REQUIRE_SNAPSHOT"
    BLOCK = "BLOCK"

class RecoveryDecisionResult(str, Enum):
    RETRY = "RETRY"
    REPLAN = "REPLAN"
    ROLLBACK = "ROLLBACK"
    ASK_USER = "ASK_USER"
    FAIL = "FAIL"

class PolicyDecision(BaseModel):
    decision: PolicyDecisionResult
    reason: str
    risk_level: RiskLevel

class RecoveryDecision(BaseModel):
    decision: RecoveryDecisionResult
    reason: str

class StateTransition(BaseModel):
    from_state: AgentState
    to_state: AgentState
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None

class GoalUnderstanding(BaseModel):
    objective: str
    entities: List[str] = []
    constraints: List[str] = []
    requested_operations: List[str] = []
    expected_outcome: str

class ActionDefinition(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str
    parameters: Dict[str, Any]
    risk_level: RiskLevel = RiskLevel.LEVEL_0_READ_ONLY
    timeout_seconds: int = 60
    retry_policy: int = 0
    expected_result: Optional[str] = None
    verification_requirements: Optional[Dict[str, Any]] = None

class PlanStep(BaseModel):
    step_id: str
    name: str
    dependencies: List[str] = []
    action: ActionDefinition

class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    steps: List[PlanStep]
    risk_level: RiskLevel = RiskLevel.LEVEL_0_READ_ONLY

class VerificationResult(BaseModel):
    success: bool
    expected_state: str
    actual_state: str
    evidence: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
