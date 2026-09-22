from pydantic import BaseModel, Field
import uuid
from typing import Optional

class ExecutionContext(BaseModel):
    """
    Context passed throughout the agent lifecycle.
    Crucial for tracing, logging, and audit.
    """
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    user_id: Optional[str] = None
    plan_id: Optional[str] = None
    execution_id: Optional[str] = None
    current_step_id: Optional[str] = None
