import psutil
from typing import List, Dict, Any

class ProcessInspector:
    """
    Safe read-only process inspection using psutil.
    """
    @staticmethod
    def get_process_list() -> List[Dict[str, Any]]:
        processes = []
        for p in psutil.process_iter(['pid', 'name', 'username', 'status', 'cpu_percent', 'memory_info']):
            try:
                proc_info = p.info
                # Simplify memory info for generic display
                if proc_info.get('memory_info'):
                    proc_info['memory_mb'] = round(proc_info['memory_info'].rss / (1024 * 1024), 2)
                    del proc_info['memory_info']
                else:
                    proc_info['memory_mb'] = 0.0
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return processes

    @staticmethod
    def get_process_details(pid: int) -> Dict[str, Any]:
        try:
            p = psutil.Process(pid)
            return p.as_dict(attrs=['pid', 'name', 'username', 'status', 'cpu_percent', 'memory_info', 'cmdline', 'create_time'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            return {"error": str(e)}
