"""
Unit Tests: Data Models
Tests for pydantic models, DAG validation, risk levels
"""

import pytest
from pydantic import ValidationError

from linuxpilot.models import (
    Risk, Step, Plan, AuditEntry,
    FsExists, FsNotExists, FsCount, UiElement, XlsxCell,
    ExecutionContext, VerificationResult, ActionExecutionResult,
    SandboxConfig,
)


class TestRisk:
    """Test Risk enum ordering"""

    def test_risk_ordering(self):
        assert Risk.READ_ONLY < Risk.REVERSIBLE
        assert Risk.REVERSIBLE < Risk.DESTRUCTIVE
        assert Risk.DESTRUCTIVE < Risk.FORBIDDEN

    def test_risk_max(self):
        assert max(Risk.READ_ONLY, Risk.DESTRUCTIVE) == Risk.DESTRUCTIVE
        assert max(Risk.FORBIDDEN, Risk.READ_ONLY) == Risk.FORBIDDEN


class TestPostconditions:
    """Test postcondition model validation"""

    def test_fs_exists(self):
        pc = FsExists(type="fs.exists", path="/tmp/test")
        assert pc.type == "fs.exists"
        assert pc.path == "/tmp/test"

    def test_fs_not_exists(self):
        pc = FsNotExists(type="fs.not_exists", path="/tmp/gone")
        assert pc.type == "fs.not_exists"

    def test_fs_count(self):
        pc = FsCount(type="fs.count", dir="/tmp", glob="*.txt", eq=5)
        assert pc.eq == 5

    def test_xlsx_cell(self):
        pc = XlsxCell(type="xlsx.cell", file="test.xlsx", sheet="Sheet1", cell="A1", equals="hello")
        assert pc.equals == "hello"


class TestStep:
    """Test Step model"""

    def test_valid_step(self):
        step = Step(
            id="s1",
            intent="List files",
            tool="fs.list",
            args={"path": "~/Downloads"},
            risk_llm=Risk.READ_ONLY,
            postconditions=[FsExists(type="fs.exists", path="~/Downloads")],
        )
        assert step.tool == "fs.list"

    def test_step_default_risk(self):
        step = Step(id="s1", intent="test", tool="fs.list", args={})
        assert step.risk_llm == Risk.READ_ONLY

    def test_step_default_postconditions(self):
        step = Step(id="s1", intent="test", tool="fs.list", args={})
        assert step.postconditions == []

    def test_step_default_depends(self):
        step = Step(id="s1", intent="test", tool="fs.list", args={})
        assert step.depends_on == []


class TestPlan:
    """Test Plan model with DAG validation"""

    def test_valid_plan(self):
        plan = Plan(
            goal="Organize files",
            steps=[
                Step(id="s1", intent="List", tool="fs.list", args={"path": "~/Downloads"}),
                Step(id="s2", intent="Create dir", tool="fs.mkdir", args={"path": "~/Downloads/docs"}, depends_on=["s1"]),
            ],
        )
        assert len(plan.steps) == 2

    def test_plan_minimum_one_step(self):
        with pytest.raises(ValidationError):
            Plan(goal="Empty plan", steps=[])

    def test_plan_dag_cycle_detected(self):
        with pytest.raises(ValueError, match="Cycle"):
            Plan(
                goal="Cyclic plan",
                steps=[
                    Step(id="s1", intent="A", tool="fs.list", args={}, depends_on=["s2"]),
                    Step(id="s2", intent="B", tool="fs.list", args={}, depends_on=["s1"]),
                ],
            )

    def test_plan_dag_missing_dependency(self):
        with pytest.raises(ValueError, match="non-existent"):
            Plan(
                goal="Missing dep",
                steps=[
                    Step(id="s1", intent="A", tool="fs.list", args={}, depends_on=["s99"]),
                ],
            )

    def test_plan_max_steps(self):
        steps = [
            Step(id=f"s{i}", intent=f"Step {i}", tool="fs.list", args={})
            for i in range(61)
        ]
        with pytest.raises(ValidationError):
            Plan(goal="Too many steps", steps=steps)


class TestAuditEntry:
    """Test AuditEntry model"""

    def test_valid_entry(self):
        entry = AuditEntry(
            seq=0, ts="2025-01-01T00:00:00Z", task="t-1",
            kind="action", payload={"tool": "fs.list"},
            prev="0" * 64, hash="a" * 64,
        )
        assert entry.seq == 0

    def test_optional_step(self):
        entry = AuditEntry(
            seq=0, ts="2025-01-01T00:00:00Z", task="t-1",
            step="s1", kind="verify", payload={},
            prev="0" * 64, hash="a" * 64,
        )
        assert entry.step == "s1"


class TestExecutionContext:
    """Test ExecutionContext model"""

    def test_default_roots(self):
        ctx = ExecutionContext(task_id="t-1")
        assert "~/Downloads" in ctx.allowed_roots

    def test_custom_roots(self):
        ctx = ExecutionContext(task_id="t-1", allowed_roots=["/custom"])
        assert ctx.allowed_roots == ["/custom"]
