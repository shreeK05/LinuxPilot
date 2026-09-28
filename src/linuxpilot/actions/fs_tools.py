"""
Filesystem Tools
Direct filesystem operations executed inside the sandbox overlay
These run at Rung L0 (highest determinism) of the action ladder
"""

import os
import shutil
import glob as globmod
from pathlib import Path
from typing import Optional, Any
import logging
import mimetypes

logger = logging.getLogger(__name__)


class FileSystemTools:
    """
    Deterministic filesystem operations on the overlay workspace.
    All paths are resolved relative to the workspace root.
    """

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)

    def _resolve(self, path: str) -> Path:
        """Resolve a user-facing path to an absolute overlay path, with confinement check"""
        p = Path(os.path.expanduser(path))
        if not p.is_absolute():
            p = self.workspace_root / p
        rp = p.resolve()
        wr = self.workspace_root.resolve()
        if not str(rp).startswith(str(wr)):
            raise PermissionError(
                f"Path {rp} escapes workspace root {wr}"
            )
        return rp

    def list_dir(self, path: str) -> dict[str, Any]:
        """List directory contents with metadata"""
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        if not target.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        entries = []
        for item in sorted(target.iterdir()):
            try:
                stat = item.stat()
                entry = {
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "is_file": item.is_file(),
                    "size": stat.st_size if item.is_file() else 0,
                    "extension": item.suffix.lower() if item.is_file() else "",
                }
                if item.is_file():
                    mime, _ = mimetypes.guess_type(str(item))
                    entry["mime_type"] = mime or "application/octet-stream"
                entries.append(entry)
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot stat {item}: {e}")
                entries.append({"name": item.name, "error": str(e)})

        return {
            "path": path,
            "count": len(entries),
            "entries": entries,
        }

    def stat(self, path: str) -> dict[str, Any]:
        """Get file/directory metadata"""
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        st = target.stat()
        mime, _ = mimetypes.guess_type(str(target))
        return {
            "path": path,
            "name": target.name,
            "is_dir": target.is_dir(),
            "is_file": target.is_file(),
            "is_symlink": target.is_symlink(),
            "size": st.st_size,
            "extension": target.suffix.lower(),
            "mime_type": mime or ("inode/directory" if target.is_dir() else "application/octet-stream"),
        }

    def mkdir(self, path: str) -> dict[str, Any]:
        """Create directory (including parents)"""
        target = self._resolve(path)
        target.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {target}")
        return {"path": path, "created": True}

    def move(self, source: str, destination: str) -> dict[str, Any]:
        """Move/rename a file or directory"""
        src = self._resolve(source)
        dst = self._resolve(destination)

        if not src.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        # If destination is a directory, move into it
        if dst.is_dir():
            dst = dst / src.name

        # Handle name collisions with automatic suffix
        if dst.exists():
            stem = dst.stem
            suffix = dst.suffix
            parent = dst.parent
            counter = 1
            while dst.exists():
                dst = parent / f"{stem}_{counter}{suffix}"
                counter += 1
            logger.info(f"Collision resolved: renaming to {dst.name}")

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        logger.info(f"Moved: {src} -> {dst}")
        return {"source": source, "destination": str(dst.relative_to(self.workspace_root)), "moved": True}

    def copy(self, source: str, destination: str) -> dict[str, Any]:
        """Copy a file or directory"""
        src = self._resolve(source)
        dst = self._resolve(destination)

        if not src.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.is_dir():
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        else:
            shutil.copy2(str(src), str(dst))

        logger.info(f"Copied: {src} -> {dst}")
        return {"source": source, "destination": destination, "copied": True}

    def delete(self, path: str) -> dict[str, Any]:
        """Delete a file or directory"""
        target = self._resolve(path)
        if not target.exists():
            return {"path": path, "deleted": False, "reason": "not found"}

        if target.is_dir():
            shutil.rmtree(str(target))
        else:
            target.unlink()

        logger.info(f"Deleted: {target}")
        return {"path": path, "deleted": True}

    def read_text(self, path: str, max_bytes: int = 65536) -> dict[str, Any]:
        """Read text file content (capped for safety)"""
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not target.is_file():
            raise IsADirectoryError(f"Not a file: {path}")

        size = target.stat().st_size
        truncated = size > max_bytes

        with open(target, "r", errors="replace") as f:
            content = f.read(max_bytes)

        return {
            "path": path,
            "size": size,
            "truncated": truncated,
            "content": content,
        }

    def extract_pdf(self, path: str) -> dict[str, Any]:
        """Extract text from a PDF file"""
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        text = ""
        pages = 0
        try:
            import pdfplumber
            with pdfplumber.open(str(target)) as pdf:
                pages = len(pdf.pages)
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except ImportError:
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(target))
                pages = len(reader.pages)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            except ImportError:
                raise RuntimeError("Neither pdfplumber nor pypdf is installed")

        return {
            "path": path,
            "pages": pages,
            "text": text[:32768],  # cap output
            "truncated": len(text) > 32768,
        }

    def write_xlsx(
        self,
        path: str,
        rows: list[list[str]],
        sheet_name: str = "Sheet1",
        headers: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Write data to an Excel spreadsheet"""
        try:
            from openpyxl import Workbook
        except ImportError:
            raise RuntimeError("openpyxl not installed")

        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name

        if headers:
            ws.append(headers)

        for row in rows:
            ws.append(row)

        wb.save(str(target))
        logger.info(f"Wrote {len(rows)} rows to {target}")
        return {
            "path": path,
            "rows_written": len(rows),
            "sheet": sheet_name,
        }

    def classify_by_extension(self, path: str) -> dict[str, list[str]]:
        """Classify files in a directory by their extension for the organizer workflow"""
        target = self._resolve(path)
        if not target.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        categories: dict[str, list[str]] = {
            "Documents": [],
            "Images": [],
            "Videos": [],
            "Audio": [],
            "Archives": [],
            "Code": [],
            "Data": [],
            "Other": [],
        }

        ext_map = {
            ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
            ".txt": "Documents", ".odt": "Documents", ".rtf": "Documents",
            ".xls": "Documents", ".xlsx": "Documents", ".csv": "Data",
            ".ppt": "Documents", ".pptx": "Documents",
            ".png": "Images", ".jpg": "Images", ".jpeg": "Images",
            ".gif": "Images", ".bmp": "Images", ".svg": "Images",
            ".webp": "Images", ".ico": "Images", ".tiff": "Images",
            ".mp4": "Videos", ".avi": "Videos", ".mkv": "Videos",
            ".mov": "Videos", ".wmv": "Videos", ".flv": "Videos",
            ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio",
            ".ogg": "Audio", ".aac": "Audio", ".wma": "Audio",
            ".zip": "Archives", ".tar": "Archives", ".gz": "Archives",
            ".bz2": "Archives", ".xz": "Archives", ".7z": "Archives",
            ".rar": "Archives", ".deb": "Archives",
            ".py": "Code", ".js": "Code", ".ts": "Code", ".html": "Code",
            ".css": "Code", ".java": "Code", ".c": "Code", ".cpp": "Code",
            ".rs": "Code", ".go": "Code", ".sh": "Code",
            ".json": "Data", ".xml": "Data", ".yaml": "Data", ".yml": "Data",
            ".sql": "Data", ".db": "Data",
        }

        for item in target.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                category = ext_map.get(ext, "Other")
                categories[category].append(item.name)

        return categories
