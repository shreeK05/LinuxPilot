"""
Unit Tests: Audit Chain
Tests for tamper-evident hash chain, verification, and integrity
"""

import pytest
import json
import tempfile
from pathlib import Path

from linuxpilot.audit.chain import AuditChain


@pytest.fixture
def audit_dir(tmp_path):
    return tmp_path / "audit"


@pytest.fixture
def chain(audit_dir):
    return AuditChain("test-task", audit_dir=audit_dir)


class TestAuditChain:
    """Test hash chain creation and verification"""

    def test_empty_chain_valid(self, chain):
        is_valid, error = chain.verify()
        assert is_valid
        assert error is None

    def test_single_entry(self, chain):
        chain.append("action", {"tool": "fs.list"}, step="s1")
        is_valid, error = chain.verify()
        assert is_valid

    def test_multiple_entries(self, chain):
        chain.append("action", {"tool": "fs.list"}, step="s1")
        chain.append("verify", {"success": True}, step="s1")
        chain.append("action", {"tool": "fs.mkdir"}, step="s2")
        chain.append("commit", {"changes": 3})

        is_valid, error = chain.verify()
        assert is_valid

    def test_chain_links_correctly(self, chain):
        e1 = chain.append("action", {"tool": "fs.list"})
        e2 = chain.append("verify", {"success": True})
        assert e2.prev == e1.hash

    def test_tamper_detection_single_byte(self, chain, audit_dir):
        """G7: Flip one byte; audit verify must fail"""
        chain.append("action", {"tool": "fs.list"}, step="s1")
        chain.append("verify", {"success": True}, step="s1")
        chain.append("commit", {"changes": 1})

        # Verify it's valid first
        is_valid, error = chain.verify()
        assert is_valid

        # Tamper with the file
        audit_file = audit_dir / "test-task.audit"
        content = audit_file.read_text()
        lines = content.strip().split("\n")

        # Modify a byte in the second entry
        entry = json.loads(lines[1])
        entry["payload"]["success"] = False  # Tamper!
        lines[1] = json.dumps(entry)

        audit_file.write_text("\n".join(lines) + "\n")

        # Verification must fail
        chain2 = AuditChain("test-task", audit_dir=audit_dir)
        is_valid, error = chain2.verify()
        assert not is_valid
        assert "mismatch" in error.lower() or "broken" in error.lower()

    def test_get_entries_filter(self, chain):
        chain.append("action", {"tool": "fs.list"})
        chain.append("verify", {"success": True})
        chain.append("rollback", {"to": "s1"})

        all_entries = chain.get_entries()
        assert len(all_entries) == 3

        action_entries = chain.get_entries(kind_filter="action")
        assert len(action_entries) == 1
        assert action_entries[0].kind == "action"

    def test_final_hash(self, chain):
        chain.append("action", {"tool": "fs.list"})
        final = chain.get_final_hash()
        assert final is not None
        assert len(final) == 64  # SHA-256 hex

    def test_clear(self, chain):
        chain.append("action", {"tool": "fs.list"})
        chain.clear()
        assert chain.seq == 0
        entries = chain.get_entries()
        assert len(entries) == 0

    def test_genesis_hash(self, chain):
        """First entry should have prev = 64 zeros"""
        entry = chain.append("action", {"tool": "fs.list"})
        assert entry.prev == "0" * 64

    def test_sequence_numbers(self, chain):
        e1 = chain.append("action", {})
        e2 = chain.append("verify", {})
        e3 = chain.append("commit", {})
        assert e1.seq == 0
        assert e2.seq == 1
        assert e3.seq == 2
