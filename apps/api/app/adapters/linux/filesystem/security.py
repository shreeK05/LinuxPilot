import os
from pathlib import Path
from typing import List

class FilesystemSecurityError(Exception):
    pass

class FilesystemSecurityPolicy:
    """
    Enforces strict path canonicalization and root checking.
    """
    def __init__(self, allowed_roots: List[str] = None, never_allowed: List[str] = None):
        # Default to safe user directories
        home = str(Path.home())
        self.allowed_roots = allowed_roots or [
            home,  # Allow root of home folder so ~/ProjectData is valid
            os.path.join(home, "Documents"),
            os.path.join(home, "Downloads"),
            os.path.join(home, "Desktop"),
            os.path.join(home, ".linuxpilot")
        ]
        
        self.never_allowed = never_allowed or [
            os.path.join(home, ".ssh"),
            os.path.join(home, ".gnupg"),
            "/etc",
            "/var/lib",
            "/root",
            "/boot"
        ]
        
        # Ensure allowed roots are absolute and canonical
        self.allowed_roots = [str(Path(r).expanduser().resolve()) for r in self.allowed_roots]
        self.never_allowed = [str(Path(r).expanduser().resolve()) for r in self.never_allowed]

    def validate_path(self, target_path: str) -> Path:
        """
        Resolves the target path and verifies it strictly resides within an allowed root.
        Throws FilesystemSecurityError if invalid.
        """
        if not target_path:
            raise FilesystemSecurityError("Target path cannot be empty.")
            
        path = Path(target_path).expanduser()
        
        # We need to resolve to catch symlinks and ../ but if the file doesn't exist,
        # resolve() on some OSes might fail or stop. 
        # Path.resolve(strict=False) resolves as much as possible.
        resolved_path = path.resolve()
        
        # Check NEVER_ALLOWED first
        resolved_str = str(resolved_path)
        for banned in self.never_allowed:
            if resolved_str == banned or resolved_str.startswith(banned + os.sep):
                raise FilesystemSecurityError(f"Path '{target_path}' is inside a protected system directory.")
        
        is_allowed = False
        for root in self.allowed_roots:
            try:
                # check if resolved_path is relative to root
                resolved_path.relative_to(root)
                is_allowed = True
                break
            except ValueError:
                continue
                
        if not is_allowed:
            raise FilesystemSecurityError(f"Path '{target_path}' resolves outside allowed roots. Resolved: '{resolved_path}'")
            
        return resolved_path
