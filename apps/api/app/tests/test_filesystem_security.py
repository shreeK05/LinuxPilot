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

def test_restricted_directories():
    policy = FilesystemSecurityPolicy()
    
    # Check that root restricted dirs are blocked
    restricted_paths = ["/etc", "/bin", "/var/log", "/sys", "/dev", "/usr/bin"]
    if Path.cwd().drive:
        restricted_paths = [Path.cwd().drive + "\\Windows", Path.cwd().drive + "\\Program Files"]
        
    for path in restricted_paths:
        with pytest.raises(FilesystemSecurityError):
            policy.validate_path(path)
