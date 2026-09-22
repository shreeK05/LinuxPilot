import pytest
import os
from pathlib import Path
from app.adapters.linux.filesystem.snapshot import SnapshotManager, TaskSnapshot
from app.adapters.linux.filesystem.rollback import RollbackManager, RollbackError
from app.adapters.linux.filesystem.security import FilesystemSecurityPolicy
from app.agent.models import ActionDefinition, RecoveryDecisionResult

@pytest.fixture
def temp_workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws

@pytest.fixture
def snap_dir(tmp_path):
    sd = tmp_path / "snapshots"
    sd.mkdir()
    return sd

def test_snapshot_creation_and_hashing(temp_workspace, snap_dir):
    manager = SnapshotManager(str(snap_dir))
    
    test_file = temp_workspace / "test.txt"
    test_file.write_text("Hello World")
    
    record = manager.create_snapshot("task_1", "action_1", "WRITE", test_file)
    
    assert record.operation_type == "WRITE"
    assert record.restoration_status == "PENDING"
    assert record.original_hash is not None
    assert record.size_bytes == 11
    
    task_snap = manager.get_task_snapshot("task_1")
    assert task_snap is not None
    assert len(task_snap.files) == 1
    assert task_snap.files[0].snapshot_id == record.snapshot_id

def test_snapshot_create_operation(temp_workspace, snap_dir):
    manager = SnapshotManager(str(snap_dir))
    
    new_file = temp_workspace / "new.txt"
    
    # Snapshot before creating it
    record = manager.create_snapshot("task_1", "action_1", "CREATE", new_file)
    assert record.operation_type == "CREATE"
    assert record.restoration_status == "PENDING"
    
    task_snap = manager.get_task_snapshot("task_1")
    assert len(task_snap.files) == 1

def test_rollback_manager_success(temp_workspace, snap_dir):
    manager = SnapshotManager(str(snap_dir))
    rb = RollbackManager(allowed_roots=[str(temp_workspace)])
    
    test_file = temp_workspace / "modify.txt"
    test_file.write_text("Original")
    
    # 1. Take snapshot
    manager.create_snapshot("task_2", "act_1", "WRITE", test_file)
    
    # 2. Modify file
    test_file.write_text("Modified")
    
    # 3. Create new file
    new_file = temp_workspace / "new.txt"
    manager.create_snapshot("task_2", "act_2", "CREATE", new_file)
    new_file.write_text("New file")
    
    # Rollback
    task_snap = manager.get_task_snapshot("task_2")
    res = rb.rollback_task(task_snap)
    
    assert len(res["successes"]) == 2
    assert len(res["failures"]) == 0
    assert task_snap.status == "ROLLED_BACK"
    
    # Assertions
    assert test_file.read_text() == "Original"
    assert not new_file.exists()

def test_rollback_manager_partial_failure(temp_workspace, snap_dir):
    manager = SnapshotManager(str(snap_dir))
    rb = RollbackManager(allowed_roots=[str(temp_workspace)])
    
    test_file = temp_workspace / "fail.txt"
    test_file.write_text("Original")
    
    record = manager.create_snapshot("task_3", "act_1", "WRITE", test_file)
    
    # Corrupt the snapshot to force a failure
    os.remove(record.snapshot_path)
    
    task_snap = manager.get_task_snapshot("task_3")
    res = rb.rollback_task(task_snap)
    
    assert len(res["failures"]) == 1
    assert len(res["successes"]) == 0
    assert task_snap.status == "PARTIAL_ROLLBACK"

def test_rollback_security_bounds(temp_workspace, snap_dir):
    manager = SnapshotManager(str(snap_dir))
    rb = RollbackManager(allowed_roots=[str(temp_workspace)])
    
    # Path outside workspace
    outside = temp_workspace.parent / "outside.txt"
    outside.write_text("Secret")
    
    # Since snapshotmanager doesn't enforce bounds itself, we mock a record
    record = manager.create_snapshot("task_4", "act_1", "WRITE", outside)
    
    task_snap = manager.get_task_snapshot("task_4")
    
    # Rollback should fail due to security policy
    res = rb.rollback_task(task_snap)
    assert len(res["failures"]) == 1
    assert "resolves outside allowed roots" in res["failures"][0]["error"]

def test_recovery_engine_rollback_decision():
    from app.agent.recovery import RecoveryEngine
    from app.agent.models import SandboxConfig, RiskLevel
    
    engine = RecoveryEngine(max_retries=1)
    action = ActionDefinition(
        action_type="filesystem.delete", 
        parameters={},
        risk_level=RiskLevel.LEVEL_3_HIGH_IMPACT,
        retry_policy=1,
        sandbox_config=SandboxConfig(required=True)
    )
    
    # First attempt -> Retry
    dec1 = engine.determine_recovery(action, "fail", 0)
    assert dec1.decision == RecoveryDecisionResult.RETRY
    
    # Second attempt -> ROLLBACK (since risk >= 3)
    dec2 = engine.determine_recovery(action, "fail", 1)
    assert dec2.decision == RecoveryDecisionResult.ROLLBACK
