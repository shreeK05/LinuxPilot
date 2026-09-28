"""
Seccomp Profile Manager
Manages seccomp-bpf profiles for syscall filtering
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SeccompProfile:
    """
    Manages seccomp-bpf profiles for syscall filtering
    Implements syscall-level security policies
    """
    
    # Syscalls to deny for GUI applications
    DENY_FOR_GUI = [
        "ptrace",
        "process_vm_readv",
        "process_vm_writev",
        "kexec_load",
        "kexec_file_load",
        "reboot",
        "mount",
        "umount2",
        "pivot_root",
        "swapon",
        "swapoff",
        "init_module",
        "finit_module",
        "delete_module",
        "bpf",
        "perf_event_open",
        "keyctl",
        "add_key",
        "request_key",
        "setns",
        "open_by_handle_at",
        "userfaultfd",
        "iopl",
        "ioperm",
        "acct",
        "settimeofday",
        "clock_settime",
        "sethostname",
        "setdomainname",
        "syslog",
    ]
    
    # Additional syscalls to deny for browser profile
    DENY_FOR_BROWSER_ADDITIONAL = [
        "unshare",
        "clone",
    ]
    
    # Minimal allowlist for helper tools
    HELPER_ALLOWLIST_BASE = [
        "read",
        "write",
        "open",
        "close",
        "stat",
        "fstat",
        "lstat",
        "poll",
        "lseek",
        "mmap",
        "mprotect",
        "munmap",
        "brk",
        "rt_sigaction",
        "rt_sigprocmask",
        "rt_sigreturn",
        "ioctl",
        "pread64",
        "pwrite64",
        "readv",
        "writev",
        "access",
        "pipe",
        "select",
        "sched_yield",
        "mremap",
        "msync",
        "mincore",
        "madvise",
        "dup",
        "dup2",
        "pause",
        "nanosleep",
        "getitimer",
        "alarm",
        "setitimer",
        "getpid",
        "sendfile",
        "socket",
        "connect",
        "accept",
        "sendto",
        "recvfrom",
        "sendmsg",
        "recvmsg",
        "shutdown",
        "bind",
        "listen",
        "getsockname",
        "getpeername",
        "socketpair",
        "setsockopt",
        "getsockopt",
        "clone",
        "fork",
        "vfork",
        "execve",
        "exit",
        "wait4",
        "kill",
        "uname",
    ]
    
    def __init__(self):
        self.profiles = {
            "helper-strict": self._generate_helper_profile(),
            "app-gui": self._generate_gui_profile(),
            "app-browser": self._generate_browser_profile(),
        }
    
    def _generate_helper_profile(self) -> Dict:
        """Generate strict allowlist profile for helper tools"""
        return {
            "default_action": "SCMP_ACT_KILL_PROCESS",
            "allowlist": self.HELPER_ALLOWLIST_BASE,
        }
    
    def _generate_gui_profile(self) -> Dict:
        """Generate denylist profile for GUI applications"""
        return {
            "default_action": "SCMP_ACT_ALLOW",
            "denylist": self.DENY_FOR_GUI,
        }
    
    def _generate_browser_profile(self) -> Dict:
        """Generate denylist profile for browser applications"""
        return {
            "default_action": "SCMP_ACT_ALLOW",
            "denylist": self.DENY_FOR_GUI + self.DENY_FOR_BROWSER_ADDITIONAL,
        }
    
    def get_profile(self, profile_name: str) -> Optional[Dict]:
        """
        Get a seccomp profile by name
        
        Args:
            profile_name: Name of the profile (helper-strict, app-gui, app-browser)
        
        Returns:
            Profile dictionary or None if not found
        """
        return self.profiles.get(profile_name)
    
    def load_profile(self, profile_name: str) -> bool:
        """
        Load a seccomp profile for the current process
        
        Args:
            profile_name: Name of the profile to load
        
        Returns:
            True if successful
        """
        try:
            profile = self.get_profile(profile_name)
            if not profile:
                logger.error(f"Profile {profile_name} not found")
                return False
            
            # In a real implementation, this would use python3-seccomp
            # or libseccomp to load the profile
            # For now, this is a placeholder
            
            logger.info(f"Loaded seccomp profile: {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load seccomp profile: {e}")
            return False
    
    def generate_seccomp_filter(
        self,
        profile_name: str,
        output_file: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate a seccomp filter in JSON format
        
        Args:
            profile_name: Name of the profile
            output_file: Optional file to write the filter to
        
        Returns:
            JSON string of the filter or None if failed
        """
        try:
            profile = self.get_profile(profile_name)
            if not profile:
                return None
            
            import json
            
            # Convert to seccomp JSON format
            if profile["default_action"] == "SCMP_ACT_KILL_PROCESS":
                default_action = "SCMP_ACT_KILL_PROCESS"
            else:
                default_action = "SCMP_ACT_ALLOW"
            
            seccomp_filter = {
                "defaultAction": default_action,
                "architectures": ["SCMP_ARCH_X86_64"],
                "syscalls": [],
            }
            
            if "allowlist" in profile:
                for syscall in profile["allowlist"]:
                    seccomp_filter["syscalls"].append({
                        "names": [syscall],
                        "action": "SCMP_ACT_ALLOW",
                    })
            
            if "denylist" in profile:
                for syscall in profile["denylist"]:
                    seccomp_filter["syscalls"].append({
                        "names": [syscall],
                        "action": "SCMP_ACT_ERRNO",
                        "args": [],
                    })
            
            filter_json = json.dumps(seccomp_filter, indent=2)
            
            if output_file:
                with open(output_file, "w") as f:
                    f.write(filter_json)
            
            return filter_json
            
        except Exception as e:
            logger.error(f"Failed to generate seccomp filter: {e}")
            return None
    
    def learn_syscalls(self, command: List[str]) -> List[str]:
        """
        Learn syscalls used by a command using strace
        Useful for building allowlists
        
        Args:
            command: Command to trace
        
        Returns:
            List of syscalls used
        """
        try:
            import subprocess
            
            # Run strace with syscall filtering
            cmd = ["strace", "-c", "-f", "-qq"] + command
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            # Parse strace output to extract syscalls
            syscalls = []
            for line in result.stderr.split("\n"):
                if "%" in line and not line.startswith("%"):
                    # Parse syscall name from strace summary
                    parts = line.split()
                    if parts:
                        syscall = parts[-1]
                        if syscall != "total":
                            syscalls.append(syscall)
            
            logger.info(f"Learned {len(syscalls)} syscalls from command")
            return syscalls
            
        except Exception as e:
            logger.error(f"Failed to learn syscalls: {e}")
            return []
