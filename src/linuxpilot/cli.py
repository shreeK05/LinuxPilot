"""
LinuxPilot CLI
Complete command-line interface: run, diff, commit, undo, audit, doctor, daemon
"""

import sys
import os
import argparse
import json
import logging
import time
from pathlib import Path

from linuxpilot.config import settings

logger = logging.getLogger(__name__)


def _setup_logging(debug: bool = False):
    """Configure logging"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def doctor():
    """
    Run system diagnostics.
    Checks kernel version, cgroup v2, overlayfs, seccomp, AT-SPI, LLM providers.
    """
    print("╔══════════════════════════════════════════╗")
    print("║       LinuxPilot System Doctor           ║")
    print("╚══════════════════════════════════════════╝")
    print()

    issues = []
    warnings = []

    # ── Python version ──
    py = sys.version_info
    if py >= (3, 12):
        print(f"  ✓ Python {py.major}.{py.minor}.{py.micro}")
    else:
        print(f"  ✗ Python {py.major}.{py.minor}.{py.micro} (need ≥3.12)")
        issues.append("Upgrade Python to ≥3.12")

    # ── Platform ──
    import platform
    if platform.system() == "Linux":
        print(f"  ✓ Platform: Linux")
    else:
        print(f"  ⚠ Platform: {platform.system()} (LinuxPilot is designed for Linux)")
        warnings.append("Not running on Linux — sandbox features will be unavailable")

    # ── Kernel version ──
    try:
        with open("/proc/version") as f:
            version = f.read()
        kernel_ver = version.split()[2]
        print(f"  ✓ Kernel: {kernel_ver}")
    except Exception:
        print("  ○ Kernel: cannot read (not Linux)")

    # ── cgroup v2 ──
    cgroup_path = Path("/sys/fs/cgroup")
    if cgroup_path.exists():
        try:
            with open(cgroup_path / "cgroup.controllers") as f:
                controllers = f.read().strip()
            print(f"  ✓ cgroup v2 (controllers: {controllers})")
        except Exception:
            print("  ✗ cgroup v2 not available")
            issues.append("cgroup v2 not available — resource limits disabled")
    else:
        print("  ○ cgroup v2: not available (not Linux)")

    # ── overlayfs ──
    try:
        import subprocess
        result = subprocess.run(
            ["grep", "overlay", "/proc/filesystems"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            print("  ✓ overlayfs supported")
        else:
            print("  ✗ overlayfs not supported")
            issues.append("overlayfs not supported — transactional workspace disabled")
    except Exception:
        print("  ○ overlayfs: cannot check (not Linux)")

    # ── seccomp ──
    try:
        import seccomp
        print("  ✓ python3-seccomp available")
    except ImportError:
        print("  ○ python3-seccomp not installed (install via: apt install python3-seccomp)")
        warnings.append("python3-seccomp not installed — syscall filtering disabled")

    # ── AT-SPI ──
    try:
        import gi
        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
        print("  ✓ AT-SPI (gi.repository.Atspi)")
    except Exception:
        print("  ○ AT-SPI not available (install: apt install python3-gi gir1.2-atspi-2.0 at-spi2-core)")
        warnings.append("AT-SPI not available — GUI automation disabled")

    # ── xdotool ──
    try:
        import subprocess
        result = subprocess.run(["xdotool", "--version"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            print(f"  ✓ xdotool ({result.stdout.strip()})")
        else:
            print("  ○ xdotool not responding")
    except FileNotFoundError:
        print("  ○ xdotool not installed (install: apt install xdotool)")
        warnings.append("xdotool not installed — keyboard/mouse automation disabled")
    except Exception:
        print("  ○ xdotool: cannot check")

    # ── Core Python dependencies ──
    print()
    print("  Dependencies:")
    deps = {
        "fastapi": "FastAPI",
        "pydantic": "Pydantic",
        "httpx": "HTTPX",
        "openpyxl": "openpyxl",
        "pypdf": "PyPDF",
        "prometheus_client": "Prometheus",
        "yaml": "PyYAML",
    }
    for module, name in deps.items():
        try:
            __import__(module)
            print(f"    ✓ {name}")
        except ImportError:
            print(f"    ✗ {name} (pip install {module})")
            issues.append(f"{name} not installed")

    # ── LLM Providers ──
    print()
    print("  LLM Providers:")

    # Ollama
    try:
        import httpx
        response = httpx.get(settings.OLLAMA_BASE_URL, timeout=3)
        if response.status_code == 200:
            print(f"    ✓ Ollama at {settings.OLLAMA_BASE_URL}")
        else:
            print(f"    ○ Ollama not responding at {settings.OLLAMA_BASE_URL}")
    except Exception:
        print(f"    ○ Ollama not available at {settings.OLLAMA_BASE_URL}")

    if settings.GROQ_API_KEY:
        print("    ✓ Groq API key configured")
    else:
        print("    ○ Groq API key not configured (set GROQ_API_KEY in .env)")

    if settings.GEMINI_API_KEY:
        print("    ✓ Gemini API key configured")
    else:
        print("    ○ Gemini API key not configured (set GEMINI_API_KEY in .env)")

    # ── Workspace ──
    print()
    print("  Workspace:")
    ws = settings.WORKSPACE_BASE
    if ws.exists():
        print(f"    ✓ {ws}")
    else:
        print(f"    ○ {ws} (will be created on first run)")

    # ── Summary ──
    print()
    print("═" * 44)
    if issues:
        print(f"  ✗ {len(issues)} issue(s) found:")
        for issue in issues:
            print(f"    • {issue}")
    if warnings:
        print(f"  ⚠ {len(warnings)} warning(s):")
        for w in warnings:
            print(f"    • {w}")
    if not issues and not warnings:
        print("  ✓ All checks passed! LinuxPilot is ready.")
    elif not issues:
        print("  ✓ No critical issues. LinuxPilot can run with limited features.")

    return 1 if issues else 0


def run_task(goal: str, mode: str = "hybrid", auto_approve: bool = False, debug: bool = False):
    """Run a task via the API"""
    import httpx

    base_url = f"http://{settings.API_HOST}:{settings.API_PORT}{settings.API_V1_STR}"

    # Check if daemon is running
    try:
        health = httpx.get(f"{base_url}/health", timeout=3)
        if health.status_code != 200:
            print("✗ LinuxPilot daemon is not running. Start it with: lp daemon")
            return 1
    except Exception:
        print("✗ LinuxPilot daemon is not running. Start it with: lp daemon")
        return 1

    # Create task
    print(f"Goal: {goal}")
    print(f"Mode: {mode}")
    print()

    response = httpx.post(
        f"{base_url}/tasks/",
        json={
            "goal": goal,
            "mode": mode,
            "auto_approve": auto_approve,
        },
        timeout=120,
    )

    if response.status_code != 200:
        print(f"✗ Failed to create task: {response.text}")
        return 1

    task = response.json()
    task_id = task["task_id"]
    print(f"Task: {task_id}")
    print(f"Status: {task['status']}")

    # Poll for completion
    while True:
        time.sleep(2)
        try:
            status = httpx.get(f"{base_url}/tasks/{task_id}", timeout=10).json()
        except Exception as e:
            print(f"  ⚠ Status check failed: {e}")
            continue

        state = status["status"]
        step = status["current_step"]
        total = status["total_steps"]
        elapsed = status.get("elapsed_time", 0)

        print(f"  [{elapsed:.0f}s] {state} — step {step}/{total}")

        if state == "waiting_approval":
            answer = input("  Approve destructive action? [y/N]: ")
            if answer.lower() == "y":
                httpx.post(
                    f"{base_url}/tasks/{task_id}/approve",
                    json={"approved": True},
                    timeout=10,
                )
            else:
                httpx.post(
                    f"{base_url}/tasks/{task_id}/approve",
                    json={"approved": False},
                    timeout=10,
                )
                print("  Task rejected.")
                return 1

        elif state == "review":
            # Show diff
            print()
            diff = httpx.get(f"{base_url}/tasks/{task_id}/diff", timeout=10).json()
            summary = diff.get("summary", {})
            changes = diff.get("changes", [])

            print(f"  Changes: +{summary.get('add', 0)} ~{summary.get('modify', 0)} -{summary.get('delete', 0)}")
            for c in changes[:20]:
                symbol = {"add": "+", "modify": "~", "delete": "-"}.get(c["kind"], "?")
                print(f"    {symbol} {c['path']}")
            if len(changes) > 20:
                print(f"    ... and {len(changes) - 20} more")

            print()
            answer = input("  Commit these changes? [y/N]: ")
            if answer.lower() == "y":
                httpx.post(f"{base_url}/tasks/{task_id}/commit", timeout=30)
                print("  ✓ Changes committed!")
            else:
                httpx.post(f"{base_url}/tasks/{task_id}/discard", timeout=10)
                print("  ↺ Changes discarded.")
            return 0

        elif state in ("completed", "failed", "aborted"):
            print(f"  Final state: {state}")
            return 0 if state == "completed" else 1


def audit_verify(task_id: str):
    """Verify the audit chain for a task"""
    from linuxpilot.audit.chain import AuditChain

    chain = AuditChain(task_id)
    is_valid, error = chain.verify()

    if is_valid:
        final_hash = chain.get_final_hash()
        entries = chain.get_entries()
        print(f"✓ Audit chain verified ({len(entries)} entries)")
        if final_hash:
            print(f"  Final hash: {final_hash[:32]}...")
    else:
        print(f"✗ Audit chain BROKEN: {error}")
        return 1

    return 0


def undo_task(task_id: str):
    """Undo a committed task by restoring from trash"""
    import httpx
    base_url = f"http://{settings.API_HOST}:{settings.API_PORT}{settings.API_V1_STR}"

    # Check workspace for the task
    task_dir = settings.WORKSPACE_BASE / "tasks" / task_id
    if not task_dir.exists():
        print(f"✗ Task {task_id} not found in workspace")
        return 1

    journal_dir = task_dir / "journal"
    for wal_file in journal_dir.glob("*.wal"):
        with open(wal_file) as f:
            journal = json.load(f)
        if journal.get("status") == "completed":
            print(f"Undoing task {task_id}...")
            from linuxpilot.workspace.commit import CommitManager
            workspace_info = {
                "journal_dir": str(journal_dir),
                "trash_dir": str(task_dir / "trash"),
                "upper_dir": str(task_dir / "upper"),
                "lower_dir": str(settings.REAL_DATA_BASE),
            }
            mgr = CommitManager(workspace_info)
            if mgr.rollback_commit(str(wal_file)):
                print("✓ Task undone successfully")
                return 0
            else:
                print("✗ Undo failed")
                return 1

    print(f"✗ No completed commit found for task {task_id}")
    return 1


def show_diff(task_id: str):
    """Show the diff for a task"""
    import httpx
    base_url = f"http://{settings.API_HOST}:{settings.API_PORT}{settings.API_V1_STR}"

    try:
        response = httpx.get(f"{base_url}/tasks/{task_id}/diff", timeout=10)
        if response.status_code == 200:
            diff = response.json()
            for c in diff.get("changes", []):
                symbol = {"add": "+", "modify": "~", "delete": "-"}.get(c["kind"], "?")
                print(f"  {symbol} {c['path']}")
            summary = diff.get("summary", {})
            print(f"\n  Total: +{summary.get('add', 0)} ~{summary.get('modify', 0)} -{summary.get('delete', 0)}")
        else:
            print(f"✗ {response.text}")
            return 1
    except Exception as e:
        print(f"✗ Cannot reach daemon: {e}")
        return 1

    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="lp",
        description="LinuxPilot — A Trust-First OS Agent for Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lp doctor                              Check system readiness
  lp daemon                              Start the API daemon
  lp run "Organize my Downloads"         Run a task
  lp run "Sort files" --mode gui         Run in GUI-only mode
  lp diff <task-id>                      Show changes
  lp commit <task-id>                    Commit changes
  lp undo <task-id>                      Undo a committed task
  lp audit verify <task-id>              Verify audit chain
        """,
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # doctor
    subparsers.add_parser("doctor", help="Run system diagnostics")

    # daemon
    daemon_p = subparsers.add_parser("daemon", help="Start the API daemon")
    daemon_p.add_argument("--host", default=settings.API_HOST, help="Host to bind to")
    daemon_p.add_argument("--port", type=int, default=settings.API_PORT, help="Port to bind to")
    daemon_p.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # run
    run_p = subparsers.add_parser("run", help="Run a task")
    run_p.add_argument("goal", help="Natural language goal")
    run_p.add_argument("--mode", choices=["api", "gui", "hybrid"], default="hybrid", help="Execution mode")
    run_p.add_argument("--approve", action="store_true", help="Auto-approve destructive actions")

    # diff
    diff_p = subparsers.add_parser("diff", help="Show task changes")
    diff_p.add_argument("task_id", help="Task ID")

    # commit (via API)
    commit_p = subparsers.add_parser("commit", help="Commit task changes")
    commit_p.add_argument("task_id", help="Task ID")

    # undo
    undo_p = subparsers.add_parser("undo", help="Undo a committed task")
    undo_p.add_argument("task_id", help="Task ID")

    # audit
    audit_p = subparsers.add_parser("audit", help="Audit operations")
    audit_sub = audit_p.add_subparsers(dest="audit_command")
    verify_p = audit_sub.add_parser("verify", help="Verify audit chain")
    verify_p.add_argument("task_id", help="Task ID")

    args = parser.parse_args()
    _setup_logging(args.debug if hasattr(args, 'debug') else False)

    if args.command == "doctor":
        sys.exit(doctor())

    elif args.command == "daemon":
        import uvicorn
        from linuxpilot.api.app import create_app
        app = create_app()
        print(f"Starting LinuxPilot daemon at http://{args.host}:{args.port}")
        print(f"Dashboard: http://{args.host}:{args.port}/dashboard")
        print(f"API docs: http://{args.host}:{args.port}{settings.API_V1_STR}/openapi.json")
        uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)

    elif args.command == "run":
        sys.exit(run_task(args.goal, args.mode, args.approve))

    elif args.command == "diff":
        sys.exit(show_diff(args.task_id))

    elif args.command == "commit":
        import httpx
        base_url = f"http://{settings.API_HOST}:{settings.API_PORT}{settings.API_V1_STR}"
        try:
            r = httpx.post(f"{base_url}/tasks/{args.task_id}/commit", timeout=30)
            if r.status_code == 200:
                print("✓ Changes committed!")
            else:
                print(f"✗ {r.json().get('detail', r.text)}")
                sys.exit(1)
        except Exception as e:
            print(f"✗ {e}")
            sys.exit(1)

    elif args.command == "undo":
        sys.exit(undo_task(args.task_id))

    elif args.command == "audit":
        if args.audit_command == "verify":
            sys.exit(audit_verify(args.task_id))
        else:
            parser.print_help()
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


def daemon():
    """Daemon entry point (for pyproject.toml lpd script)"""
    import uvicorn
    from linuxpilot.api.app import create_app
    _setup_logging()
    app = create_app()
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)


if __name__ == "__main__":
    main()
