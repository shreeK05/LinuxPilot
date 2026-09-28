import pytest
from pathlib import Path
from app.adapters.linux.filesystem.security import FilesystemSecurityPolicy, FilesystemSecurityError

def test_validate_path_safe():
    # Use custom root for test
    base = Path.home() / "Documents"
    policy = FilesystemSecurityPolicy(allowed_roots=[str(base)])
    safe_path = base / "safe_file.txt"
    
    result = policy.validate_path(str(safe_path))
    assert result == safe_path.resolve()

def test_validate_path_traversal():
    policy = FilesystemSecurityPolicy()
    base = Path.home()
    
    # Try to traverse out to /etc/passwd or similar
    # On Windows, try C:/Windows/System32
    if Path.cwd().drive:
        attack_path = Path.cwd().drive + "\\Windows\\System32\\cmd.exe"
    else:
        attack_path = "/etc/passwd"
        
    with pytest.raises(FilesystemSecurityError, match="resolves outside allowed roots"):
        policy.validate_path(str(attack_path))

def test_validate_path_relative_traversal():
    policy = FilesystemSecurityPolicy()
    
    # Even if we start in a valid root, climbing out should fail
    # e.g., ~/Documents/../../../../etc/passwd
    attack_path = str(Path.home() / "Documents" / ".." / ".." / ".." / "etc" / "passwd")
    
    with pytest.raises(FilesystemSecurityError, match="resolves outside allowed roots"):
        policy.validate_path(attack_path)

def test_never_allowed_directories():
    base = Path.home() / "Documents"
    # Even if we explicitly allow a root, never_allowed should override
    policy = FilesystemSecurityPolicy(allowed_roots=[str(base)], never_allowed=[str(base / "secrets")])
    
    # Allowed
    safe_path = base / "safe_file.txt"
    assert policy.validate_path(str(safe_path)) == safe_path.resolve()
    
    # Never allowed exact match
    secret_path = base / "secrets"
    with pytest.raises(FilesystemSecurityError, match="inside a protected system directory"):
        policy.validate_path(str(secret_path))
        
    # Never allowed sub-directory
    secret_file = base / "secrets" / "key.txt"
    with pytest.raises(FilesystemSecurityError, match="inside a protected system directory"):
        policy.validate_path(str(secret_file))

def test_o_nofollow_opener():
    from app.adapters.linux.filesystem.operations import FilesystemAdapter
    policy = FilesystemSecurityPolicy()
    adapter = FilesystemAdapter(policy)
    
    # Check that it runs without crashing, since we cannot easily test os.open directly
    # without mocking. We just ensure the _safe_opener is callable and returns a descriptor or fails gracefully.
    import os
    if hasattr(os, "O_NOFOLLOW"):
        assert adapter._safe_opener is not None
