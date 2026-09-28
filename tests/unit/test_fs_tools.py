"""
Unit Tests: Filesystem Tools
Tests for the action ladder's L0 filesystem operations
"""

import pytest
import os
from pathlib import Path

from linuxpilot.actions.fs_tools import FileSystemTools


@pytest.fixture
def workspace(tmp_path):
    """Create a test workspace"""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def fs(workspace):
    """Create FileSystemTools instance"""
    return FileSystemTools(str(workspace))


@pytest.fixture
def populated_workspace(workspace):
    """Workspace with some test files"""
    (workspace / "file1.txt").write_text("hello")
    (workspace / "file2.pdf").write_text("pdf content")
    (workspace / "subdir").mkdir()
    (workspace / "subdir" / "nested.txt").write_text("nested")
    return workspace


class TestPathConfinement:
    """Test that paths are confined to workspace root"""

    def test_path_within_workspace(self, fs, workspace):
        (workspace / "test.txt").write_text("ok")
        result = fs.stat("test.txt")
        assert result["name"] == "test.txt"

    def test_path_escape_blocked(self, fs, workspace):
        with pytest.raises(PermissionError, match="escapes"):
            fs.stat("/etc/passwd")

    def test_dotdot_escape_blocked(self, fs, workspace):
        with pytest.raises(PermissionError, match="escapes"):
            fs.stat("../../../etc/passwd")

    def test_absolute_path_outside_blocked(self, fs, workspace):
        with pytest.raises(PermissionError, match="escapes"):
            fs.list_dir("/tmp")


class TestListDir:
    """Test directory listing"""

    def test_list_empty_dir(self, fs, workspace):
        result = fs.list_dir(".")
        assert result["count"] == 0

    def test_list_populated_dir(self, fs, populated_workspace, workspace):
        result = fs.list_dir(".")
        assert result["count"] == 3  # file1.txt, file2.pdf, subdir

    def test_list_nonexistent(self, fs):
        with pytest.raises(FileNotFoundError):
            fs.list_dir("nonexistent")


class TestMkdir:
    """Test directory creation"""

    def test_mkdir_simple(self, fs, workspace):
        result = fs.mkdir("newdir")
        assert result["created"]
        assert (workspace / "newdir").is_dir()

    def test_mkdir_nested(self, fs, workspace):
        result = fs.mkdir("a/b/c/d")
        assert (workspace / "a" / "b" / "c" / "d").is_dir()

    def test_mkdir_existing(self, fs, workspace):
        (workspace / "existing").mkdir()
        result = fs.mkdir("existing")
        assert result["created"]  # exist_ok=True


class TestMove:
    """Test file move/rename"""

    def test_move_file(self, fs, workspace):
        (workspace / "src.txt").write_text("data")
        result = fs.move("src.txt", "dst.txt")
        assert result["moved"]
        assert not (workspace / "src.txt").exists()
        assert (workspace / "dst.txt").exists()

    def test_move_collision_resolved(self, fs, workspace):
        (workspace / "file.txt").write_text("original")
        (workspace / "target.txt").write_text("existing")
        result = fs.move("file.txt", "target.txt")
        assert result["moved"]
        # Should have been renamed to avoid collision
        assert (workspace / "target.txt").exists()  # Original preserved

    def test_move_into_directory(self, fs, workspace):
        (workspace / "file.txt").write_text("data")
        (workspace / "dest").mkdir()
        result = fs.move("file.txt", "dest")
        assert (workspace / "dest" / "file.txt").exists()


class TestCopy:
    """Test file copy"""

    def test_copy_file(self, fs, workspace):
        (workspace / "src.txt").write_text("data")
        result = fs.copy("src.txt", "dst.txt")
        assert result["copied"]
        assert (workspace / "src.txt").exists()  # Original preserved
        assert (workspace / "dst.txt").exists()


class TestDelete:
    """Test file deletion"""

    def test_delete_file(self, fs, workspace):
        (workspace / "target.txt").write_text("data")
        result = fs.delete("target.txt")
        assert result["deleted"]
        assert not (workspace / "target.txt").exists()

    def test_delete_directory(self, fs, workspace):
        (workspace / "target_dir").mkdir()
        (workspace / "target_dir" / "inner.txt").write_text("data")
        result = fs.delete("target_dir")
        assert result["deleted"]

    def test_delete_nonexistent(self, fs):
        result = fs.delete("nonexistent.txt")
        assert not result["deleted"]


class TestReadText:
    """Test text reading"""

    def test_read_text(self, fs, workspace):
        (workspace / "test.txt").write_text("hello world")
        result = fs.read_text("test.txt")
        assert result["content"] == "hello world"
        assert not result["truncated"]

    def test_read_text_truncated(self, fs, workspace):
        (workspace / "big.txt").write_text("x" * 100000)
        result = fs.read_text("big.txt", max_bytes=100)
        assert result["truncated"]
        assert len(result["content"]) == 100


class TestClassifyByExtension:
    """Test file classification"""

    def test_classify_mixed(self, fs, workspace):
        (workspace / "doc.pdf").write_text("pdf")
        (workspace / "image.png").write_text("png")
        (workspace / "code.py").write_text("python")
        (workspace / "unknown.xyz").write_text("mystery")

        result = fs.classify_by_extension(".")
        assert "doc.pdf" in result["Documents"]
        assert "image.png" in result["Images"]
        assert "code.py" in result["Code"]
        assert "unknown.xyz" in result["Other"]


class TestWriteXlsx:
    """Test Excel writing"""

    def test_write_xlsx(self, fs, workspace):
        pytest.importorskip("openpyxl")
        result = fs.write_xlsx(
            "output.xlsx",
            rows=[["Alice", "100"], ["Bob", "200"]],
            headers=["Name", "Amount"],
        )
        assert result["rows_written"] == 2
        assert (workspace / "output.xlsx").exists()
