from abc import ABC, abstractmethod
from typing import Any
from app.agent.models import ActionDefinition, VerificationResult
from app.adapters.linux.filesystem.security import FilesystemSecurityPolicy
from pathlib import Path

class Verifier(ABC):
    """
    Abstract interface for verifying if an action succeeded based on its expected state.
    """
    @abstractmethod
    def verify(self, action: ActionDefinition, execution_output: Any) -> VerificationResult:
        pass

class DeterministicVerifier(Verifier):
    """
    Phase 3 Verifier that checks real OS states where possible.
    """
    def __init__(self):
        self.security = FilesystemSecurityPolicy()

    def verify(self, action: ActionDefinition, output: Any) -> VerificationResult:
        try:
            if action.action_type == "filesystem.create_directory":
                target = action.parameters.get("path")
                safe_path = self.security.validate_path(target)
                if safe_path.exists() and safe_path.is_dir():
                    return VerificationResult(success=True)
                return VerificationResult(success=False, error="Directory was not created successfully")
                
            elif action.action_type == "filesystem.write_file":
                target = action.parameters.get("path")
                safe_path = self.security.validate_path(target)
                if safe_path.exists() and safe_path.is_file():
                    # For simplicity, we just check existence and size > 0 if content wasn't empty
                    if action.parameters.get("content") and safe_path.stat().st_size == 0:
                        return VerificationResult(success=False, error="File created but is empty")
                    return VerificationResult(success=True)
                return VerificationResult(success=False, error="File was not written successfully")
                
            elif action.action_type == "filesystem.delete":
                target = action.parameters.get("path")
                try:
                    safe_path = self.security.validate_path(target)
                    if safe_path.exists():
                        return VerificationResult(success=False, error="File still exists after deletion")
                except Exception:
                    pass # Invalid paths mean it's deleted or inaccessible
                return VerificationResult(success=True)

            elif action.action_type == "filesystem.rename" or action.action_type == "filesystem.move":
                dest = action.parameters.get("destination") or action.parameters.get("destination_name")
                src = action.parameters.get("source")
                try:
                    safe_src = self.security.validate_path(src)
                    if safe_src.exists():
                        return VerificationResult(success=False, error="Source still exists after move/rename")
                except Exception:
                    pass
                
                # Dest check
                if dest:
                    # if rename, dest is in same dir as src
                    if action.action_type == "filesystem.rename":
                        dest_path = self.security.validate_path(src).parent / dest
                        safe_dest = self.security.validate_path(str(dest_path))
                    else:
                        safe_dest = self.security.validate_path(dest)
                        
                    if not safe_dest.exists():
                        return VerificationResult(success=False, error="Destination does not exist")
                        
                return VerificationResult(success=True)
                
            elif action.action_type == "filesystem.copy":
                dest = action.parameters.get("destination")
                safe_dest = self.security.validate_path(dest)
                if safe_dest.exists():
                    return VerificationResult(success=True)
                return VerificationResult(success=False, error="Destination does not exist after copy")

            # Fallback for others (system.info, read, list)
            return VerificationResult(success=True)
            
        except Exception as e:
            return VerificationResult(success=False, error=f"Verification crashed: {str(e)}")
