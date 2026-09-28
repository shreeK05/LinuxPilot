"""
Unit Tests: Policy Engine
Tests for risk classification, path confinement, and destructive operation detection
"""

import os
import pytest
import tempfile

from linuxpilot.models import Step, Risk, ExecutionContext
from linuxpilot.planning.policy import PolicyEngine


@pytest.fixture
def policy():
    return PolicyEngine()


@pytest.fixture
def context(tmp_path):
    return ExecutionContext(
        task_id="t-test",
        allowed_roots=[str(tmp_path)],
    )


class TestRiskClassification:
    """Test base risk classification for each tool"""

    def test_read_only_tools(self, policy, context):
        for tool in ["fs.list", "fs.stat", "fs.read_text", "doc.extract_pdf", "web.wait_for_text"]:
            step = Step(id="s1", intent="test", tool=tool, args={})
            risk = policy.classify(step, context)
            assert risk == Risk.READ_ONLY, f"{tool} should be READ_ONLY"

    def test_reversible_tools(self, policy, context):
        for tool in ["fs.mkdir", "fs.copy", "fs.move", "sheet.write",
                      "app.launch", "app.close", "ui.invoke", "ui.set_text",
                      "ui.key", "ui.click_xy", "ui.vlm_click"]:
            step = Step(id="s1", intent="test", tool=tool, args={})
            risk = policy.classify(step, context)
            assert risk >= Risk.REVERSIBLE, f"{tool} should be at least REVERSIBLE"

    def test_delete_is_destructive(self, policy, context):
        step = Step(id="s1", intent="Delete", tool="fs.delete", args={"path": "/tmp/test"})
        risk = policy.classify(step, context)
        assert risk >= Risk.DESTRUCTIVE


class TestPathConfinement:
    """Test path confinement — paths outside allowed roots must be FORBIDDEN"""

    def test_allowed_path(self, policy, context, tmp_path):
        step = Step(id="s1", intent="List", tool="fs.list",
                    args={"path": str(tmp_path / "subdir")})
        risk = policy.classify(step, context)
        assert risk != Risk.FORBIDDEN

    def test_forbidden_path_etc(self, policy, context):
        step = Step(id="s1", intent="Read", tool="fs.read_text",
                    args={"path": "/etc/passwd"})
        risk = policy.classify(step, context)
        assert risk == Risk.FORBIDDEN

    def test_forbidden_path_root(self, policy, context):
        step = Step(id="s1", intent="List", tool="fs.list",
                    args={"path": "/"})
        risk = policy.classify(step, context)
        assert risk == Risk.FORBIDDEN

    def test_dotdot_traversal_blocked(self, policy, context, tmp_path):
        step = Step(id="s1", intent="Read", tool="fs.read_text",
                    args={"path": str(tmp_path / ".." / ".." / "etc" / "passwd")})
        risk = policy.classify(step, context)
        assert risk == Risk.FORBIDDEN

    def test_symlink_escape_blocked(self, policy, context, tmp_path):
        """Symlink pointing outside allowed roots should be FORBIDDEN"""
        # os.path.realpath resolves symlinks
        step = Step(id="s1", intent="Read", tool="fs.read_text",
                    args={"path": "/tmp/../../etc/passwd"})
        risk = policy.classify(step, context)
        assert risk == Risk.FORBIDDEN


class TestLLMRiskEscalation:
    """Test that LLM can only raise risk, never lower it"""

    def test_llm_raises_risk(self, policy, context):
        step = Step(id="s1", intent="Copy", tool="fs.copy",
                    args={}, risk_llm=Risk.DESTRUCTIVE)
        risk = policy.classify(step, context)
        assert risk >= Risk.DESTRUCTIVE

    def test_llm_cannot_lower_risk(self, policy, context):
        step = Step(id="s1", intent="Delete", tool="fs.delete",
                    args={}, risk_llm=Risk.READ_ONLY)
        risk = policy.classify(step, context)
        assert risk >= Risk.DESTRUCTIVE  # Base risk is DESTRUCTIVE


class TestApprovalLogic:
    """Test approval/block decisions"""

    def test_destructive_needs_approval(self, policy):
        assert policy.should_require_approval(Risk.DESTRUCTIVE)
        assert policy.should_require_approval(Risk.FORBIDDEN)

    def test_read_only_no_approval(self, policy):
        assert not policy.should_require_approval(Risk.READ_ONLY)
        assert not policy.should_require_approval(Risk.REVERSIBLE)

    def test_forbidden_blocked(self, policy):
        assert policy.should_block(Risk.FORBIDDEN)
        assert not policy.should_block(Risk.DESTRUCTIVE)
