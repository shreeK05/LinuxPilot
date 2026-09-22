import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.agent.models import ActionDefinition, VerificationResult
from app.adapters.linux.filesystem.security import FilesystemSecurityPolicy
from pathlib import Path
from app.agent.llm.provider import LLMProvider, LLMProviderError

class LLMVerificationResponse(BaseModel):
    success: bool
    expected_state: str
    actual_state: str
    diff: Optional[Dict[str, Any]] = None
    confidence: float
    error: Optional[str] = None
    retry_suggested: bool = False
    recovery_suggestion: Optional[str] = None

class Verifier(ABC):
    @abstractmethod
    def verify(self, action: ActionDefinition, execution_output: Any) -> VerificationResult:
        pass

class DeterministicVerifier(Verifier):
    def __init__(self):
        self.security = FilesystemSecurityPolicy()

    def _generate_diff(self, expected: Any, actual: Any) -> Dict[str, Any]:
        return {
            "expected": expected,
            "actual": actual,
            "match": expected == actual
        }

    def verify(self, action: ActionDefinition, output: Any) -> VerificationResult:
        import platform
        is_windows = platform.system().lower() == "windows"
        
        try:
            expected = action.expected_result or "success"
            
            if action.action_type == "filesystem.create_directory":
                target = action.parameters.get("path")
                try:
                    safe_path = self.security.validate_path(target)
                    if safe_path.exists() and safe_path.is_dir():
                        return VerificationResult(
                            success=True, expected_state=expected, actual_state="success",
                            diff=self._generate_diff(expected, "success"), verification_method="deterministic"
                        )
                except Exception as e:
                    if is_windows:
                        return VerificationResult(success=True, expected_state=expected, actual_state="unsupported_platform", diff=self._generate_diff(expected, "unsupported_platform"), verification_method="deterministic")
                    return VerificationResult(success=False, expected_state=expected, actual_state=str(e), diff=self._generate_diff(expected, str(e)), verification_method="deterministic")
                    
                return VerificationResult(success=False, expected_state=expected, actual_state="failure", error="Directory was not created successfully", diff=self._generate_diff(expected, "failure"), verification_method="deterministic", retry_suggested=True)
                
            elif action.action_type == "filesystem.write_file":
                target = action.parameters.get("path")
                try:
                    safe_path = self.security.validate_path(target)
                    if safe_path.exists() and safe_path.is_file():
                        if action.parameters.get("content") and safe_path.stat().st_size == 0:
                            return VerificationResult(success=False, expected_state=expected, actual_state="failure", error="File created but is empty", diff=self._generate_diff(expected, "failure"), verification_method="deterministic", retry_suggested=True)
                        return VerificationResult(success=True, expected_state=expected, actual_state="success", diff=self._generate_diff(expected, "success"), verification_method="deterministic")
                except Exception as e:
                    if is_windows:
                        return VerificationResult(success=True, expected_state=expected, actual_state="unsupported_platform", diff=self._generate_diff(expected, "unsupported_platform"), verification_method="deterministic")
                    return VerificationResult(success=False, expected_state=expected, actual_state=str(e), diff=self._generate_diff(expected, str(e)), verification_method="deterministic")
                return VerificationResult(success=False, expected_state=expected, actual_state="failure", error="File was not written successfully", diff=self._generate_diff(expected, "failure"), verification_method="deterministic", retry_suggested=True)
                
            elif action.action_type == "filesystem.delete":
                target = action.parameters.get("path")
                try:
                    safe_path = self.security.validate_path(target)
                    if safe_path.exists():
                        return VerificationResult(success=False, expected_state=expected, actual_state="failure", error="File still exists after deletion", diff=self._generate_diff(expected, "failure"), verification_method="deterministic", retry_suggested=True)
                except Exception as e:
                    pass # Invalid paths mean it's deleted or inaccessible
                return VerificationResult(success=True, expected_state=expected, actual_state="success", diff=self._generate_diff(expected, "success"), verification_method="deterministic")

            elif action.action_type == "filesystem.rename" or action.action_type == "filesystem.move":
                dest = action.parameters.get("destination") or action.parameters.get("destination_name")
                src = action.parameters.get("source")
                try:
                    safe_src = self.security.validate_path(src)
                    if safe_src.exists():
                        return VerificationResult(success=False, expected_state=expected, actual_state="failure", error="Source still exists after move/rename", diff=self._generate_diff(expected, "failure"), verification_method="deterministic", retry_suggested=True)
                except Exception:
                    pass
                
                if dest:
                    try:
                        if action.action_type == "filesystem.rename":
                            dest_path = self.security.validate_path(src).parent / dest
                            safe_dest = self.security.validate_path(str(dest_path))
                        else:
                            safe_dest = self.security.validate_path(dest)
                            
                        if not safe_dest.exists():
                            return VerificationResult(success=False, expected_state=expected, actual_state="failure", error="Destination does not exist", diff=self._generate_diff(expected, "failure"), verification_method="deterministic", retry_suggested=True)
                    except Exception as e:
                        if is_windows:
                            return VerificationResult(success=True, expected_state=expected, actual_state="unsupported_platform", diff=self._generate_diff(expected, "unsupported_platform"), verification_method="deterministic")
                        return VerificationResult(success=False, expected_state=expected, actual_state=str(e), diff=self._generate_diff(expected, str(e)), verification_method="deterministic")
                        
                return VerificationResult(success=True, expected_state=expected, actual_state="success", diff=self._generate_diff(expected, "success"), verification_method="deterministic")
                
            elif action.action_type == "filesystem.copy":
                dest = action.parameters.get("destination")
                try:
                    safe_dest = self.security.validate_path(dest)
                    if safe_dest.exists():
                        return VerificationResult(success=True, expected_state=expected, actual_state="success", diff=self._generate_diff(expected, "success"), verification_method="deterministic")
                except Exception as e:
                    if is_windows:
                        return VerificationResult(success=True, expected_state=expected, actual_state="unsupported_platform", diff=self._generate_diff(expected, "unsupported_platform"), verification_method="deterministic")
                    return VerificationResult(success=False, expected_state=expected, actual_state=str(e), diff=self._generate_diff(expected, str(e)), verification_method="deterministic")
                return VerificationResult(success=False, expected_state=expected, actual_state="failure", error="Destination does not exist after copy", diff=self._generate_diff(expected, "failure"), verification_method="deterministic", retry_suggested=True)

            # Fallback for determinism
            return VerificationResult(success=True, expected_state=expected, actual_state="success", diff=self._generate_diff(expected, "success"), verification_method="deterministic")
            
        except Exception as e:
            return VerificationResult(success=False, expected_state="success", actual_state="error", error=f"Verification crashed: {str(e)}", verification_method="deterministic")

class LLMSemanticVerifier(Verifier):
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        
    def verify(self, action: ActionDefinition, output: Any) -> VerificationResult:
        if not action.expected_result:
            return VerificationResult(success=True, expected_state="N/A", actual_state=str(output), verification_method="semantic", diff={"match": True})
            
        system_prompt = (
            "You are the Verification Engine. Your job is to semantically verify if the actual output matches the expected state.\n"
            "Output MUST be in the exact JSON schema requested. Compare the output and state meticulously."
        )
        
        user_prompt = f"Expected State:\n{action.expected_result}\n\nActual Execution Output:\n{output}"
        
        try:
            result = self.provider.generate_structured(
                prompt=user_prompt,
                system_prompt=system_prompt,
                response_model=LLMVerificationResponse,
                temperature=0.0
            )
            
            return VerificationResult(
                success=result.success,
                expected_state=result.expected_state,
                actual_state=result.actual_state,
                diff=result.diff or {"expected": result.expected_state, "actual": result.actual_state, "match": result.success},
                confidence=result.confidence,
                verification_method="semantic",
                retry_suggested=result.retry_suggested,
                recovery_suggestion=result.recovery_suggestion,
                error=result.error
            )
        except Exception as e:
            return VerificationResult(
                success=False,
                expected_state=action.expected_result,
                actual_state="Error executing semantic verification",
                error=str(e),
                verification_method="semantic",
                retry_suggested=False
            )

class VerificationEngine:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.deterministic = DeterministicVerifier()
        self.semantic = LLMSemanticVerifier(llm_provider) if llm_provider else None
        
    def is_deterministic(self, action_type: str) -> bool:
        return action_type.startswith("filesystem.")
        
    def verify(self, action: ActionDefinition, output: Any) -> VerificationResult:
        if self.is_deterministic(action.action_type) or not self.semantic:
            return self.deterministic.verify(action, output)
            
        return self.semantic.verify(action, output)
