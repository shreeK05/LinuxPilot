import json
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any

class VerificationResult(BaseModel):
    success: bool
    expected_state: Any
    actual_state: Any
    diff: Optional[dict] = None
    confidence: float = 1.0
    verification_method: str = "deterministic" # or "semantic"
    retry_suggested: bool = False
    recovery_suggestion: Optional[str] = None
    evidence: Optional[dict] = None
    error: Optional[str] = None

try:
    raise ValueError("Groq rate limit")
except Exception as e:
    res = VerificationResult(
        success=False,
        expected_state="Some state",
        actual_state="Error executing semantic verification",
        error=str(e),
        verification_method="semantic",
        retry_suggested=False,
        diff={"error": "Failed to generate structured response"}
    )
    print("RES:", res.model_dump())
