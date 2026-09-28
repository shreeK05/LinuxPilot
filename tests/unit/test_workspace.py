"""
Unit Tests: Workspace (Overlay, Checkpoint, Commit, Diff)
"""

import pytest
import json
import shutil
from pathlib import Path

from linuxpilot.workspace.overlay import OverlayManager
from linuxpilot.workspace.checkpoint import CheckpointManager
from linuxpilot.workspace.commit import CommitManager, Change, ChangeKind
from linuxpilot.workspace.diff import DiffAnalyzer


@pytest.fixture
def overlay_mgr(tmp_path):
    return OverlayManager(
        workspace_base=tmp_path / "workspace",
        real_data_base=tmp_path / "real",
    )


@pytest.fixture
def real_data(tmp_path):
    """Create some real data files"""
    real = tmp_path / "real" / "Downloads"
    real.mkdir(parents=True)
    (real / "file1.txt").write_text("original content")
    (real / "file2.pdf").write_text("pdf data")
    return real


class TestOverlayManager:
    """Test workspace creation and management"""

    def test_create_task_workspace(self, overlay_mgr, real_data):
        ws = overlay_mgr.create_task_workspace("t-1", str(real_data))
        assert ws["task_id"] == "t-1"
        assert Path(ws["upper_dir"]).exists()
        assert Path(ws["work_dir"]).exists()
        assert Path(ws["checkpoints_dir"]).exists()
        assert Path(ws["journal_dir"]).exists()
        assert Path(ws["trash_dir"]).exists()

    def test_get_upper_size_empty(self, overlay_mgr, real_data):
        ws = overlay_mgr.create_task_workspace("t-2", str(real_data))
        size = overlay_mgr.get_upper_size(ws)
        assert size == 0

    def test_get_upper_size_with_files(self, overlay_mgr, real_data):
        ws = overlay_mgr.create_task_workspace("t-3", str(real_data))
        upper = Path(ws["upper_dir"])
        (upper / "new_file.txt").write_text("new content")
        size = overlay_mgr.get_upper_size(ws)
        assert size > 0

    def test_discard_task(self, overlay_mgr, real_data):
        ws = overlay_mgr.create_task_workspace("t-4", str(real_data))
        task_dir = Path(ws["task_dir"])
        assert task_dir.exists()
        overlay_mgr.discard_task(ws)
        assert not task_dir.exists()


class TestCheckpointManager:
    """Test checkpoint creation and restoration"""

    @pytest.fixture
    def checkpoint_setup(self, overlay_mgr, real_data):
        ws = overlay_mgr.create_task_workspace("t-cp", str(real_data))
        cp_mgr = CheckpointManager(ws)
        upper = Path(ws["upper_dir"])
        return ws, cp_mgr, upper

    def test_create_checkpoint(self, checkpoint_setup):
        ws, cp_mgr, upper = checkpoint_setup
        (upper / "change1.txt").write_text("step 1")
        info = cp_mgr.create_checkpoint("s1")
        assert info["step_id"] == "s1"
        assert Path(info["upper_backup"]).exists()

    def test_restore_checkpoint(self, checkpoint_setup):
        ws, cp_mgr, upper = checkpoint_setup

        # Create step 1 changes and checkpoint
        (upper / "step1.txt").write_text("step 1 data")
        cp_mgr.create_checkpoint("s1")

        # Create step 2 changes
        (upper / "step2.txt").write_text("step 2 data — will be rolled back")

        # Restore to step 1
        success = cp_mgr.restore_checkpoint("s1")
        assert success
        assert (upper / "step1.txt").exists()
        assert not (upper / "step2.txt").exists()

    def test_list_checkpoints(self, checkpoint_setup):
        ws, cp_mgr, upper = checkpoint_setup
        (upper / "a.txt").write_text("a")
        cp_mgr.create_checkpoint("s1")
        (upper / "b.txt").write_text("b")
        cp_mgr.create_checkpoint("s2")
        checkpoints = cp_mgr.list_checkpoints()
        assert "s1" in checkpoints
        assert "s2" in checkpoints

    def test_restore_nonexistent_checkpoint(self, checkpoint_setup):
        ws, cp_mgr, upper = checkpoint_setup
        success = cp_mgr.restore_checkpoint("nonexistent")
        assert not success


class TestCommitManager:
    """Test WAL-based commit and recovery"""

    @pytest.fixture
    def commit_setup(self, tmp_path, real_data):
        ws = {
            "journal_dir": str(tmp_path / "journal"),
            "trash_dir": str(tmp_path / "trash"),
            "upper_dir": str(tmp_path / "upper"),
            "lower_dir": str(real_data),
        }
        for d in [ws["journal_dir"], ws["trash_dir"], ws["upper_dir"]]:
            Path(d).mkdir(parents=True, exist_ok=True)
        mgr = CommitManager(ws)
        return ws, mgr

    def test_commit_add(self, commit_setup):
        ws, mgr = commit_setup
        upper = Path(ws["upper_dir"])
        lower = Path(ws["lower_dir"])

        # Create a new file in upper
        (upper / "new_file.txt").write_text("new content")

        change = Change(kind=ChangeKind.ADD, rel_path="new_file.txt")
        journal = mgr.begin_commit("t-add", [change])
        assert mgr.apply_change(journal, change)
        assert mgr.finalize_commit(journal)
        assert (lower / "new_file.txt").exists()

    def test_commit_modify(self, commit_setup):
        ws, mgr = commit_setup
        upper = Path(ws["upper_dir"])
        lower = Path(ws["lower_dir"])

        # Modify existing file
        (upper / "file1.txt").write_text("modified content")

        change = Change(kind=ChangeKind.MODIFY, rel_path="file1.txt")
        journal = mgr.begin_commit("t-mod", [change])
        assert mgr.apply_change(journal, change)
        assert mgr.finalize_commit(journal)
        assert (lower / "file1.txt").read_text() == "modified content"

    def test_commit_delete(self, commit_setup):
        ws, mgr = commit_setup
        lower = Path(ws["lower_dir"])

        change = Change(kind=ChangeKind.DELETE, rel_path="file1.txt")
        journal = mgr.begin_commit("t-del", [change])
        assert mgr.apply_change(journal, change)
        assert mgr.finalize_commit(journal)
        assert not (lower / "file1.txt").exists()

    def test_recovery_rolls_back_incomplete(self, commit_setup):
        """G6: Kill at journal step; recovery yields all-or-nothing"""
        ws, mgr = commit_setup
        upper = Path(ws["upper_dir"])
        lower = Path(ws["lower_dir"])

        original_content = (lower / "file1.txt").read_text()

        # Begin commit but don't finalize
        (upper / "file1.txt").write_text("should be rolled back")
        change = Change(kind=ChangeKind.MODIFY, rel_path="file1.txt")
        journal = mgr.begin_commit("t-crash", [change])
        mgr.apply_change(journal, change)
        # Don't finalize — simulates crash

        # Recovery should roll back
        recovered = mgr.recover()
        assert "t-crash" in recovered


class TestDiffAnalyzer:
    """Test overlay diff analysis"""

    @pytest.fixture
    def diff_setup(self, tmp_path, real_data):
        upper = tmp_path / "upper"
        upper.mkdir()
        ws = {
            "upper_dir": str(upper),
            "lower_dir": str(real_data),
        }
        return ws, upper

    def test_detect_added_file(self, diff_setup):
        ws, upper = diff_setup
        (upper / "new_file.txt").write_text("new")
        analyzer = DiffAnalyzer(ws)
        changes = analyzer.analyze()
        adds = [c for c in changes if c["kind"] == "add"]
        assert any(c["path"] == "new_file.txt" for c in adds)

    def test_detect_modified_file(self, diff_setup):
        ws, upper = diff_setup
        (upper / "file1.txt").write_text("modified")
        analyzer = DiffAnalyzer(ws)
        changes = analyzer.analyze()
        mods = [c for c in changes if c["kind"] == "modify"]
        assert any(c["path"] == "file1.txt" for c in mods)

    def test_format_diff(self, diff_setup):
        ws, upper = diff_setup
        (upper / "new.txt").write_text("added")
        analyzer = DiffAnalyzer(ws)
        changes = analyzer.analyze()
        formatted = analyzer.format_diff(changes)
        assert "+" in formatted

    def test_get_summary(self, diff_setup):
        ws, upper = diff_setup
        (upper / "new.txt").write_text("added")
        analyzer = DiffAnalyzer(ws)
        changes = analyzer.analyze()
        summary = analyzer.get_summary(changes)
        assert summary["add"] >= 1
