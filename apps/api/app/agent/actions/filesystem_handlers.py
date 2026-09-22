from app.agent.actions.registry import ActionHandler, ActionExecutionResult
from app.agent.models import ActionDefinition
from app.adapters.linux.filesystem.operations import FilesystemAdapter
from app.adapters.linux.filesystem.snapshot import SnapshotManager
from app.adapters.linux.filesystem.security import FilesystemSecurityPolicy
from pathlib import Path

# Instantiate shared components
security_policy = FilesystemSecurityPolicy()
fs_adapter = FilesystemAdapter(security_policy)
snapshot_manager = SnapshotManager()

class FSListDirectoryHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            target = action.parameters.get("path")
            result = fs_adapter.list_directory(target)
            return ActionExecutionResult(success=True, output=result)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))

class FSStatHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            target = action.parameters.get("path")
            result = fs_adapter.stat(target)
            return ActionExecutionResult(success=True, output=result)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))

class FSReadFileHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            target = action.parameters.get("path")
            result = fs_adapter.read_file(target)
            return ActionExecutionResult(success=True, output=result)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))

class FSCreateDirectoryHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            target = action.parameters.get("path")
            result = fs_adapter.create_directory(target)
            return ActionExecutionResult(success=True, output=result)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))

class FSCopyHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            src = action.parameters.get("source")
            dest = action.parameters.get("destination")
            result = fs_adapter.copy(src, dest)
            return ActionExecutionResult(success=True, output=result)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))

class FSMoveHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            src = action.parameters.get("source")
            dest = action.parameters.get("destination")
            
            # Snapshot source before moving
            task_id = action.parameters.get("task_id", "unknown_task")
            src_path = Path(src).expanduser().resolve()
            dest_path = Path(dest).expanduser().resolve() / src_path.name
            snapshot_manager.create_snapshot(task_id, action.action_id, "MOVE", src_path, dest_path)
            
            result = fs_adapter.move(src, dest)
            return ActionExecutionResult(success=True, output=result)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))

class FSRenameHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            src = action.parameters.get("source")
            dest_name = action.parameters.get("destination_name")
            
            # Snapshot source before rename
            task_id = action.parameters.get("task_id", "unknown_task")
            src_path = Path(src).expanduser().resolve()
            dest_path = src_path.parent / dest_name
            snapshot_manager.create_snapshot(task_id, action.action_id, "RENAME", src_path, dest_path)
            
            result = fs_adapter.rename(src, dest_name)
            return ActionExecutionResult(success=True, output=result)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))

class FSWriteFileHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            target = action.parameters.get("path")
            content = action.parameters.get("content")
            
            # Snapshot target before overwriting (if it exists)
            task_id = action.parameters.get("task_id", "unknown_task")
            target_path = Path(target).expanduser().resolve()
            op_type = "WRITE" if target_path.exists() else "CREATE"
            snapshot_manager.create_snapshot(task_id, action.action_id, op_type, target_path)
            
            result = fs_adapter.write_file(target, content)
            return ActionExecutionResult(success=True, output=result)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))

class FSDeleteHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            target = action.parameters.get("path")
            
            # Snapshot target before deletion
            task_id = action.parameters.get("task_id", "unknown_task")
            snapshot_manager.create_snapshot(task_id, action.action_id, "DELETE", Path(target).expanduser().resolve())
            
            result = fs_adapter.delete(target)
            return ActionExecutionResult(success=True, output=result)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))
