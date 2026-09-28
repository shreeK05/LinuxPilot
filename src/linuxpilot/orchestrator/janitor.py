"""
Janitor Module
Cleans up leaked resources (mounts, cgroups, Xvnc sessions) on startup
"""

import os
import subprocess
import logging
from pathlib import Path

from linuxpilot.config import settings

logger = logging.getLogger(__name__)


class Janitor:
    """
    Startup janitor that cleans up leaked resources from previous runs.
    Handles:
    - Leaked overlayfs mounts
    - Orphaned cgroup directories
    - Stale Xvnc sessions
    - Orphaned task workspace directories
    """

    def __init__(self):
        self.workspace_base = settings.WORKSPACE_BASE
        self.cgroup_base = Path("/sys/fs/cgroup/linuxpilot")

    def cleanup_all(self):
        """Run all cleanup routines"""
        logger.info("Janitor: starting cleanup")
        self._cleanup_leaked_mounts()
        self._cleanup_orphaned_cgroups()
        self._cleanup_stale_vnc()
        self._cleanup_stale_workspaces()
        logger.info("Janitor: cleanup complete")

    def _cleanup_leaked_mounts(self):
        """Unmount any leaked overlayfs mounts"""
        try:
            result = subprocess.run(
                ["findmnt", "-t", "overlay", "-n", "-o", "TARGET"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return

            for mount_point in result.stdout.strip().split("\n"):
                mount_point = mount_point.strip()
                if not mount_point:
                    continue
                # Only clean up our mounts
                if "linuxpilot" in mount_point or str(self.workspace_base) in mount_point:
                    logger.warning(f"Janitor: unmounting leaked overlay at {mount_point}")
                    try:
                        subprocess.run(
                            ["umount", "-l", mount_point],
                            capture_output=True,
                            timeout=5,
                        )
                    except Exception as e:
                        logger.error(f"Janitor: failed to unmount {mount_point}: {e}")

        except FileNotFoundError:
            logger.debug("findmnt not available, skipping mount cleanup")
        except Exception as e:
            logger.warning(f"Janitor: mount cleanup error: {e}")

    def _cleanup_orphaned_cgroups(self):
        """Remove orphaned cgroup directories"""
        if not self.cgroup_base.exists():
            return

        try:
            for cgroup_dir in self.cgroup_base.iterdir():
                if not cgroup_dir.is_dir():
                    continue

                # Check if cgroup has any processes
                procs_file = cgroup_dir / "cgroup.procs"
                if procs_file.exists():
                    with open(procs_file) as f:
                        pids = [line.strip() for line in f if line.strip()]

                    if not pids:
                        # Empty cgroup — remove it
                        logger.warning(f"Janitor: removing orphaned cgroup {cgroup_dir.name}")
                        try:
                            cgroup_dir.rmdir()
                        except OSError as e:
                            logger.warning(f"Janitor: cannot remove cgroup {cgroup_dir.name}: {e}")
                    else:
                        # Has processes but maybe they're zombies — kill them
                        logger.warning(
                            f"Janitor: cgroup {cgroup_dir.name} has {len(pids)} orphaned processes"
                        )
                        kill_file = cgroup_dir / "cgroup.kill"
                        if kill_file.exists():
                            try:
                                with open(kill_file, "w") as f:
                                    f.write("1")
                                import time
                                time.sleep(0.5)
                                cgroup_dir.rmdir()
                            except Exception as e:
                                logger.warning(f"Janitor: cleanup cgroup {cgroup_dir.name} failed: {e}")

        except PermissionError:
            logger.debug("Janitor: no permission to clean cgroups (not root)")
        except Exception as e:
            logger.warning(f"Janitor: cgroup cleanup error: {e}")

    def _cleanup_stale_vnc(self):
        """Kill stale Xvnc sessions"""
        try:
            result = subprocess.run(
                ["pgrep", "-a", "Xvnc"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return

            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split(None, 1)
                if len(parts) >= 2 and "linuxpilot" in parts[1].lower():
                    pid = int(parts[0])
                    logger.warning(f"Janitor: killing stale Xvnc session (PID {pid})")
                    try:
                        os.kill(pid, 9)
                    except ProcessLookupError:
                        pass

        except FileNotFoundError:
            logger.debug("pgrep not available")
        except Exception as e:
            logger.warning(f"Janitor: VNC cleanup error: {e}")

    def _cleanup_stale_workspaces(self):
        """Clean up task workspaces that have no active overlay mount"""
        tasks_dir = self.workspace_base / "tasks"
        if not tasks_dir.exists():
            return

        # Get active mount targets
        active_mounts = set()
        try:
            result = subprocess.run(
                ["findmnt", "-t", "overlay", "-n", "-o", "TARGET"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    active_mounts.add(line.strip())
        except Exception:
            pass

        # Check each task directory
        for task_dir in tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            mount_point = task_dir / "mount"
            if str(mount_point) not in active_mounts:
                # Check if there's an incomplete journal
                journal_dir = task_dir / "journal"
                has_active_journal = False
                if journal_dir.exists():
                    for wal in journal_dir.glob("*.wal"):
                        try:
                            import json
                            with open(wal) as f:
                                data = json.load(f)
                            if data.get("status") == "in_progress":
                                has_active_journal = True
                                break
                        except Exception:
                            pass

                if not has_active_journal:
                    logger.info(f"Janitor: cleaning stale workspace {task_dir.name}")
                    # Don't delete — just log for now. User can clean manually.
                    # In production, could add a --purge flag.
