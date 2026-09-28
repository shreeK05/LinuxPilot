import psutil
from typing import Dict, Any

class SafeTerminalCommands:
    """
    Exposes explicit deterministic system commands without using an unrestricted shell.
    Uses Python native APIs (psutil) where possible, ensuring multi-platform safety and avoiding shell injection.
    """
    @staticmethod
    def get_disk_usage(path: str = "/") -> Dict[str, Any]:
        try:
            usage = psutil.disk_usage(path)
            return {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        try:
            mem = psutil.virtual_memory()
            return {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "percent": mem.percent,
                "used_gb": round(mem.used / (1024**3), 2)
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        try:
            return {
                "logical_cores": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False),
                "usage_percent": psutil.cpu_percent(interval=0.5)
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_os_info() -> Dict[str, Any]:
        import platform
        try:
            return {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "architecture": platform.architecture()[0]
            }
        except Exception as e:
            return {"error": str(e)}
