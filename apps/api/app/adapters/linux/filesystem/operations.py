import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Union
from app.adapters.linux.filesystem.security import FilesystemSecurityPolicy, FilesystemSecurityError

class FilesystemAdapter:
    """
    Provides safe, controlled file operations using Python native APIs.
    Integrates with FilesystemSecurityPolicy to prevent path escapes.
    """
    def __init__(self, security_policy: FilesystemSecurityPolicy):
        self.security = security_policy
        self.max_read_size = 5 * 1024 * 1024  # 5MB
        self.max_write_size = 50 * 1024 * 1024 # 50MB

    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        safe_path = self.security.validate_path(path)
        if not safe_path.exists() or not safe_path.is_dir():
            raise FileNotFoundError(f"Directory not found: {path}")
            
        results = []
        for item in safe_path.iterdir():
            results.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0,
                "path": str(item)
            })
        return results

    def stat(self, path: str) -> Dict[str, Any]:
        safe_path = self.security.validate_path(path)
        if not safe_path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
            
        s = safe_path.stat()
        return {
            "size": s.st_size,
            "is_dir": safe_path.is_dir(),
            "created": s.st_ctime,
            "modified": s.st_mtime,
            "path": str(safe_path)
        }

    def read_file(self, path: str) -> str:
        safe_path = self.security.validate_path(path)
        if not safe_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
            
        if safe_path.stat().st_size > self.max_read_size:
            raise ValueError(f"File exceeds maximum read size of {self.max_read_size} bytes")
            
        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()

    def create_directory(self, path: str) -> str:
        safe_path = self.security.validate_path(path)
        safe_path.mkdir(parents=True, exist_ok=True)
        return str(safe_path)

    def write_file(self, path: str, content: str) -> str:
        safe_path = self.security.validate_path(path)
        if len(content.encode('utf-8')) > self.max_write_size:
            raise ValueError(f"Content exceeds maximum write size of {self.max_write_size} bytes")
            
        # Ensure parent exists
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return str(safe_path)

    def copy(self, src: str, dest: str) -> str:
        safe_src = self.security.validate_path(src)
        safe_dest = self.security.validate_path(dest)
        
        if not safe_src.exists():
            raise FileNotFoundError(f"Source not found: {src}")
            
        safe_dest.parent.mkdir(parents=True, exist_ok=True)
        
        if safe_src.is_dir():
            shutil.copytree(safe_src, safe_dest, dirs_exist_ok=True)
        else:
            shutil.copy2(safe_src, safe_dest)
        return str(safe_dest)

    def move(self, src: str, dest: str) -> str:
        safe_src = self.security.validate_path(src)
        safe_dest = self.security.validate_path(dest)
        
        if not safe_src.exists():
            raise FileNotFoundError(f"Source not found: {src}")
            
        safe_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(safe_src), str(safe_dest))
        return str(safe_dest)

    def rename(self, src: str, dest_name: str) -> str:
        safe_src = self.security.validate_path(src)
        # For rename, destination is in the same directory
        safe_dest = safe_src.parent / dest_name
        # Still validate to prevent 'dest_name' containing traversals like '../test'
        safe_dest = self.security.validate_path(str(safe_dest))
        
        if not safe_src.exists():
            raise FileNotFoundError(f"Source not found: {src}")
            
        safe_src.rename(safe_dest)
        return str(safe_dest)

    def delete(self, path: str) -> bool:
        safe_path = self.security.validate_path(path)
        if not safe_path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
            
        if safe_path.is_dir():
            shutil.rmtree(safe_path)
        else:
            safe_path.unlink()
        return True
