"""
Core data models for LinuxPilot
Following the v2.0 specification with strict schema validation
"""

from enum import Enum, IntEnum
from typing import Literal, Annotated, Union, Optional
from pydantic import BaseModel, Field


class Risk(IntEnum):
    """Risk level classification - ordering matters: higher = more dangerous"""
    READ_ONLY = 0
    REVERSIBLE = 1
    DESTRUCTIVE = 2
    FORBIDDEN = 3


Tool = Literal[
    "fs.list",
    "fs.stat",
    "fs.mkdir",
    "fs.move",
    "fs.copy",
    "fs.delete",
    "fs.read_text",
    "doc.extract_pdf",
    "sheet.write",
    "app.launch",
    "app.close",
    "ui.invoke",
    "ui.set_text",
    "ui.key",
    "ui.click_xy",
    "ui.vlm_click",
    "web.wait_for_text",
]


# --- Postconditions: machine-checkable claims about the world after a step

class FsExists(BaseModel):
    type: Literal["fs.exists"]
    path: str


class FsNotExists(BaseModel):
    type: Literal["fs.not_exists"]
    path: str


class FsCount(BaseModel):
    type: Literal["fs.count"]
    dir: str
    glob: str
    eq: int


class UiElement(BaseModel):
    type: Literal["ui.element"]
    role: str
    name: Optional[str] = None
    showing: bool = True


class XlsxCell(BaseModel):
    type: Literal["xlsx.cell"]
    file: str
    sheet: str
    cell: str
    equals: str


class HttpRecord(BaseModel):
    type: Literal["http.record"]
    url: str
    field: str
    equals: str


Postcondition = Annotated[
    Union[FsExists, FsNotExists, FsCount, UiElement, XlsxCell, HttpRecord],
    Field(discriminator="type")
]


class Step(BaseModel):
    """A single execution step in the plan"""
    id: str
    intent: str  # human-readable description
    tool: Tool
    args: dict
    risk_llm: Risk = Risk.READ_ONLY  # LLM's opinion; policy engine may only raise it
    postconditions: list[Postcondition] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """A complete execution plan with DAG-ordered steps"""
    goal: str
    steps: list[Step] = Field(min_length=1, max_length=60)
    
    def model_post_init(self, __context):
        """Validate the plan is a valid DAG after creation"""
        self._validate_dag()
    
    def _validate_dag(self):
        """Ensure the plan forms a valid directed acyclic graph"""
        step_ids = {step.id for step in self.steps}
        
        # Check all dependencies exist
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(f"Step {step.id} depends on non-existent step {dep}")
        
        # Check for cycles using DFS
        visited = set()
        recursion_stack = set()
        
        def visit(step_id):
            if step_id in recursion_stack:
                raise ValueError(f"Cycle detected involving step {step_id}")
            if step_id in visited:
                return
            
            visited.add(step_id)
            recursion_stack.add(step_id)
            
            step = next(s for s in self.steps if s.id == step_id)
            for dep in step.depends_on:
                visit(dep)
            
            recursion_stack.remove(step_id)
        
        for step in self.steps:
            visit(step.id)


class AuditEntry(BaseModel):
    """A single entry in the tamper-evident audit log"""
    seq: int
    ts: str  # ISO 8601 timestamp
    task: str
    step: Optional[str] = None
    kind: Literal["action", "verify", "rollback", "violation", "approval", "commit"]
    payload: dict
    prev: str  # Previous hash in chain
    hash: str  # SHA-256 hash of this entry


class SandboxConfig(BaseModel):
    """Sandbox configuration for a step"""
    required: bool = False
    profile: Literal["helper-strict", "app-gui", "app-browser"] = "app-gui"
    memory_limit_mb: Optional[int] = None
    cpu_limit_percent: Optional[int] = None
    pids_limit: Optional[int] = None


class ExecutionContext(BaseModel):
    """Context information for task execution"""
    task_id: str
    plan_id: Optional[str] = None
    current_step_id: Optional[str] = None
    allowed_roots: list[str] = Field(default_factory=lambda: ["~/Downloads", "~/Documents"])
    workspace_path: Optional[str] = None
    real_data_path: Optional[str] = None


class VerificationResult(BaseModel):
    """Result of postcondition verification"""
    success: bool
    error: Optional[str] = None
    details: dict = Field(default_factory=dict)


class ActionExecutionResult(BaseModel):
    """Result of executing a single action"""
    success: bool
    output: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
