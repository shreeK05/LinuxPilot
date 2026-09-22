import platform
import os
import sys
from typing import Dict, Any

class SystemInfoAdapter:
    """
    Detects hardware, OS, and runtime environment.
    Falls back gracefully on Windows to support local development.
    """
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        os_name = platform.system()
        
        info = {
            "os": os_name,
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "python_version": sys.version.split(" ")[0],
            "runtime_platform": "LINUX_RUNTIME" if os_name == "Linux" else "WINDOWS_DEVELOPMENT",
            "is_ubuntu": False,
            "distribution": "Unknown",
            "distribution_version": "Unknown",
            "current_user": os.getlogin() if hasattr(os, "getlogin") else "unknown",
        }
        
        if os_name == "Linux":
            try:
                import distro
                info["distribution"] = distro.id()
                info["distribution_version"] = distro.version()
                info["is_ubuntu"] = info["distribution"].lower() == "ubuntu"
            except ImportError:
                # Fallback if distro package is missing
                try:
                    with open("/etc/os-release") as f:
                        for line in f:
                            if line.startswith("ID="):
                                info["distribution"] = line.split("=")[1].strip().strip('"')
                            elif line.startswith("VERSION_ID="):
                                info["distribution_version"] = line.split("=")[1].strip().strip('"')
                        info["is_ubuntu"] = info["distribution"].lower() == "ubuntu"
                except Exception:
                    pass
                    
        return info
