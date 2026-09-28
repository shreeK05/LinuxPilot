# Phase 14 Stage 4 — Execution Isolation / Sandbox Engine Design

> **STATUS: Design document only. No production code was modified.**
> Prerequisite: `docs/PHASE14_STAGE4_SANDBOX_AUDIT.md`
> Generated: 2026-09-23

---

## A. Current Execution Architecture

### A.1 How Commands/Actions Reach the ExecutionEngine

```
User NL Input
  |
  v HTTP POST /api/v1/tasks
FastAPI Router
  |
  v
AgentOrchestrator.run_lifecycle(raw_goal)
  |
  +-- [UNDERSTANDING] LLMGoalInterpreter.interpret(raw_goal)
  |       --> LLM API (Groq) --> GoalUnderstanding (Pydantic-validated)
  |
  +-- [PLANNING] LLMPlanner.create_plan(goal)
  |       --> LLM API --> LLMPlanResponse
  |       --> validate: action_type in registry._handlers? (else PlannerError)
  |       --> LLMActionParameters: strict Pydantic schema (extra=forbid)
  |       --> DAGValidator.topological_sort() --> ExecutionPlan
  |
  +-- [POLICY_CHECK] PolicyEngine.evaluate(step.action) per step (DETERMINISTIC, NO LLM)
  |       RiskClassifier maps action_type --> RiskLevel
  |       --> BLOCK / REQUIRE_APPROVAL / REQUIRE_SNAPSHOT / ALLOW
  |
  +-- [WAITING_APPROVAL] if required
  |       Suspend --> human approves via UI --> resume_from_approval()
  |
  +-- [EXECUTING] per step
  |       orchestrator._interpolate_parameters() -- regex, not eval()
  |       ExecutionEngine.execute_action(ActionDefinition)
  |           policy re-check (defense-in-depth)
  |           registry.get_handler(action_type)
  |           handler.execute(action)
  |               --> *** HOST OS INTERACTION ***
  |               FilesystemAdapter / psutil / Playwright / pypdf / openpyxl
  |
  +-- [VERIFYING]
  |       VerificationEngine.verify(action, output)
  |       DeterministicVerifier OR LLMSemanticVerifier
  |
  +-- [RECOVERY if needed]
          RecoveryEngine.determine_recovery() --> RETRY/REPLAN/ROLLBACK/FAIL
```

### A.2 Operations That Interact With Real Filesystem or OS

| Handler | OS Interaction | File |
|---------|---------------|------|
| FSListDirectoryHandler | pathlib.iterdir() | filesystem_handlers.py |
| FSStatHandler | os.stat | filesystem_handlers.py |
| FSReadFileHandler | open() read | filesystem_handlers.py |
| FSCreateDirectoryHandler | mkdir() | filesystem_handlers.py |
| FSCopyHandler | shutil.copy2() | filesystem_handlers.py |
| FSMoveHandler | shutil.move() | filesystem_handlers.py |
| FSRenameHandler | Path.rename() | filesystem_handlers.py |
| FSWriteFileHandler | open() write | filesystem_handlers.py |
| FSDeleteHandler | shutil.rmtree() / unlink() | filesystem_handlers.py |
| SystemInfoHandler | psutil.disk_usage(), platform.* | registry.py |
| PDFExtractTextHandler | pypdf file read | document_handlers.py |
| XLSXReadHandler | openpyxl file read | document_handlers.py |
| XLSXWriteHandler | openpyxl file write | document_handlers.py |
| BrowserNavigateHandler | playwright browser subprocess | browser_handlers.py |
| SnapshotManager | shutil.copy2() to ~/.linuxpilot/snapshots/ | snapshot.py |

### A.3 Trust Classification of All Components

| Component | Trust Level | Receives LLM Data? |
|-----------|-------------|-------------------|
| PolicyEngine | FULLY TRUSTED | No -- deterministic only |
| ApprovalGate (Approval DB) | FULLY TRUSTED | Human decision only |
| ActionRegistry | FULLY TRUSTED | Static whitelist |
| FilesystemSecurityPolicy | FULLY TRUSTED | No |
| AgentStateMachine | TRUSTED | No |
| ExecutionEngine | TRUSTED | Receives validated ActionDefinition |
| FilesystemAdapter | TRUSTED | Python-native |
| SnapshotManager / RollbackManager | TRUSTED | No |
| ExecutionContext | TRUSTED | Internal IDs only |
| LLMGoalInterpreter | UNTRUSTED OUTPUT | Yes -- produces GoalUnderstanding |
| LLMPlanner | UNTRUSTED OUTPUT | Yes -- validated against registry |
| LLMSemanticVerifier | UNTRUSTED OUTPUT | Yes -- produces VerificationResult |
| ActionDefinition.parameters | UNTRUSTED DATA | LLM-generated; must be sanitized |

### A.4 Where the Correct Isolation Boundary Should Be

```
ABOVE the line (untrusted/LLM-influenced):
  GoalUnderstanding, LLMPlanResponse, ActionDefinition.parameters
  (parameters validated by Pydantic schema but values are LLM-generated)

-- ISOLATION BOUNDARY (Stage 4 adds enforcement here) --

BELOW the line (trusted/deterministic):
  PolicyEngine evaluation
  ActionRegistry lookup (only registered handlers)
  FilesystemSecurityPolicy path validation
  Actual Python handler execution
  Host OS calls
```

The boundary is currently enforced only at the Python application level.
Stage 4 adds OS-level enforcement: resource limits, subprocess isolation,
and guaranteed timeout enforcement at the execution layer.

---

## B. Threat Model

### B.1 Assets to Protect

| Asset | Why Critical |
|-------|-------------|
| .env and all secrets | LLM API keys, DB passwords |
| ~/.ssh/ | Remote access credentials |
| ~/.config/chromium/, ~/.mozilla/ | Browser sessions, stored passwords |
| /etc, /usr, /bin | OS integrity |
| PostgreSQL database | Task history, users, audit log |
| ~/.gnupg/ | Encryption keys |
| Other users' home dirs | Multi-user system safety |

### B.2 Threat Actors

1. MALICIOUS LLM OUTPUT: Model produces plan that would read secrets or destroy files
2. PROMPT INJECTION: External content manipulates LLM to generate dangerous plans
3. PARAMETER CRAFTING: Legitimate action types with dangerous params (path=".env")
4. HANDLER BUG: A Python handler bug opens a path beyond the security boundary
5. RESOURCE EXHAUSTION: Handler/subprocess consumes all memory/CPU/disk
6. TOCTOU RACE: Symlink swap between path validation and file open
7. SUBPROCESS INJECTION: Future handler calls subprocess without proper validation

### B.3 Threat Mitigations

| Threat | Currently Mitigated | Stage 4 Addition |
|--------|--------------------|-----------------|
| LLM direct shell access | action_type whitelist | subprocess allowlist for terminal.safe |
| Path traversal | validate_path() + resolve() | O_NOFOLLOW + NEVER_ALLOWED list |
| Arbitrary host FS | allowed_roots | Dedicated workspace + enforcement |
| Resource exhaustion | None | resource.setrlimit() in subprocess |
| Timeout bypass | Post-hoc check (broken) | ThreadPoolExecutor.result(timeout=) |
| Process escape | None | subprocess isolation + process limits |
| Secret exposure | .env not in allowed_roots | Subprocess env cleaned of all secrets |
| Symlink TOCTOU | None | O_NOFOLLOW open flag |

---

## C. Sandbox Architecture Proposal

### C.1 Decision: Layered Defense Without Root

REJECTED options:
- Docker per action: too heavy, requires dockerd
- chroot: requires root
- OverlayFS: requires root or FUSE
- CLONE_NEWNET/CLONE_NEWNS namespaces: require CAP_SYS_ADMIN

SELECTED approach: Tiered layered defense using standard library only (no root):
- Tier 0: ThreadPoolExecutor timeout for in-process handlers
- Tier 1: subprocess.run(shell=False) + allowlist + resource.setrlimit() for terminal.safe
- Tier 2 (future): systemd-run --user --scope for scoped cgroup isolation

### C.2 Three Execution Tiers

TIER 0 -- In-Process Safe Operations (no subprocess):
  Actions: filesystem.*, system.info, document.*, browser.*
  Mechanism: ThreadPoolExecutor.result(timeout=N) for timeout enforcement
  Isolation: Python-level FilesystemSecurityPolicy (existing, improved)
  New in Stage 4: REAL timeout enforcement (existing is post-hoc/broken)

TIER 1 -- Safe Subprocess (new: terminal.safe):
  Actions: terminal.safe (curated allowlisted commands only)
  Mechanism: subprocess.run(shell=False, args=allowlist_validated, cwd=workspace,
             env=minimal_cleaned, timeout=N, preexec_fn=apply_resource_limits)
  New in Stage 4: this entire tier

TIER 2 -- Future systemd-run scope (NOT Stage 4):
  Actions: TBD high-impact operations
  Mechanism: systemd-run --user --scope with cgroup resource limits
  Notes: No root needed on Ubuntu 22.04+ desktop sessions

### C.3 Sandbox Layers in Stack Order (Tier 1)

Layer 1: PolicyEngine (deterministic risk classification --> BLOCK if needed)
Layer 2: Approval Gate (human confirmation for LEVEL_2+)
Layer 3: ActionRegistry whitelist (only registered action_type names)
Layer 4: LLMActionParameters strict Pydantic schema (extra=forbid)
Layer 5: FilesystemSecurityPolicy.validate_path() (path canonicalization)
Layer 6: Command allowlist check (SafeSubprocessRunner.validate_command())
Layer 7: resource.setrlimit() applied in child process (RLIMIT_AS, RLIMIT_CPU, RLIMIT_NPROC)
Layer 8: subprocess.run(shell=False, cwd=workspace, env=minimal, timeout=N)
Layer 9: SIGTERM --> 2s wait --> SIGKILL on timeout + cgroup cleanup in finally
Layer 10: VerificationEngine validates output before returning to orchestrator

FAIL CLOSED: Any layer that cannot be initialized returns
ActionExecutionResult(success=False, error="SANDBOX_INIT_FAILED").
Execution is REJECTED rather than falling back to unrestricted host execution.

---

## D. Trust Boundaries

```
ZONE 1: FULLY TRUSTED (internal to application process)
  PolicyEngine, AgentStateMachine, ApprovalGate, ActionRegistry
  FilesystemSecurityPolicy, SnapshotManager, RollbackManager
  ExecutionContext (internal IDs only)
  Database (PostgreSQL)
  .env / secrets (process env only -- NEVER passed to subprocess)

ZONE 2: VALIDATED BOUNDARY (LLM output is validated here)
  LLMPlanner --> action_type validated against registry
  LLMPlanner --> parameters validated by LLMActionParameters (strict Pydantic)
  orchestrator._interpolate_parameters() --> regex pattern, not eval()
  ExecutionEngine.execute_action() --> second policy check (defense-in-depth)

ZONE 3: SANDBOXED EXECUTION
  Tier 0: Python handler in ThreadPoolExecutor with real timeout
  Tier 1: subprocess.run() with allowlist + minimal env + resource limits
  RULE: subprocess env MUST NOT contain:
        LLM_API_KEY, DATABASE_URL, SECRET_KEY, JWT_SECRET,
        or any *_KEY, *_TOKEN, *_SECRET, *_PASSWORD variable

ZONE 4: HOST OS (never directly accessible from Zone 3)
  /etc, /usr, /bin, /sbin, /sys, /proc, /dev
  ~/.ssh, ~/.gnupg, ~/.config/chromium, ~/.mozilla
  Any .env file
  /var/lib/postgresql
```

---

## E. Filesystem Isolation Design

### E.1 Workspace Root

Single canonical writable workspace:
  ~/.linuxpilot/workspace/

This is the ONLY directory the agent can write to by default.
Read-only access remains for existing allowed_roots:
  ~/Documents/, ~/Downloads/, ~/Desktop/

NEVER accessible (new NEVER_ALLOWED list in FilesystemSecurityPolicy):
  ~/.ssh/
  ~/.gnupg/
  ~/.config/  (except explicit opt-in sub-paths)
  /etc, /usr, /bin, /sbin, /sys, /proc, /dev
  Any path matching *.env or .env.*

### E.2 Path Validation Hardening

CURRENT GAP: TOCTOU between validate_path() resolve() and file open().

Stage 4 fix for file opens (Linux only):
  Use os.open(path, os.O_RDONLY | os.O_NOFOLLOW) instead of open()
  O_NOFOLLOW refuses to follow symlinks at the final path component.
  On Windows: standard open() with warning log (no symlinks in this context).

### E.3 Snapshot Directory Security

Snapshot dir (~/.linuxpilot/snapshots/) must be:
- NOT in the sandbox's allowed paths
- Written to ONLY by the trusted application process
- Protected by a separate FilesystemSecurityPolicy instance

### E.4 Allowed Roots at Startup

DEFAULT_ALLOWED_ROOTS = [
    ~/.linuxpilot/workspace/  (writable)
    ~/Documents/              (read: existing)
    ~/Downloads/              (read: existing)
    ~/Desktop/                (read: existing)
]

NEVER_ALLOWED check added to validate_path():
  Reject any path that resolves into ~/.ssh, ~/.gnupg, system dirs, etc.

---

## F. Command / Process Isolation Design

### F.1 SafeSubprocessRunner (New: apps/api/app/agent/sandbox/subprocess_runner.py)

ALLOWED_COMMANDS = frozenset([
    "ls", "cat", "pwd", "find", "which", "file",
    "du", "df", "echo", "wc", "sort", "head", "tail", "grep",
    "stat", "md5sum", "sha256sum", "uname", "hostname",
    "date", "id",
])

Invariants enforced:
- shell=False always
- Command validated against ALLOWED_COMMANDS before Popen
- args is an explicit list (no string join/interpolation)
- cwd = workspace directory only
- env = minimal cleaned dict (see F.2)
- preexec_fn = apply_resource_limits (Linux only)
- timeout via subprocess.communicate(timeout=N)
- SIGTERM --> 2s wait --> SIGKILL on TimeoutExpired
- stdout + stderr captured; never executed further

### F.2 Environment Cleaning

SAFE_ENV for subprocess = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": str(workspace),  # redirect HOME to workspace
    "LANG": "en_US.UTF-8",
    "LC_ALL": "en_US.UTF-8",
    "TMPDIR": str(workspace / "tmp"),
    "TERM": "dumb",
}

EXPLICITLY REMOVED (never inherited from parent):
    LLM_API_KEY, LLM_BASE_URL, DATABASE_URL, SECRET_KEY, JWT_SECRET,
    POSTGRES_PASSWORD, GROQ_API_KEY, OPENAI_API_KEY,
    LD_PRELOAD, LD_LIBRARY_PATH, PYTHONPATH,
    HTTP_PROXY, HTTPS_PROXY, ALL_PROXY, NO_PROXY,
    All variables matching: *_KEY, *_TOKEN, *_SECRET, *_PASSWORD

### F.3 Resource Limits (preexec_fn, Linux only)

import resource

def apply_resource_limits(memory_mb=256, cpu_seconds=10, max_procs=50):
    mem_bytes = memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    resource.setrlimit(resource.RLIMIT_NPROC, (max_procs, max_procs))
    resource.setrlimit(resource.RLIMIT_FSIZE, (50*1024*1024, 50*1024*1024))

On Windows: function is a no-op with WARNING log. Tests skip with
@pytest.mark.skipif(platform.system() != 'Linux', reason='Linux only')

---

## G. Resource Limits

| Resource | Limit | Mechanism | Platform |
|----------|-------|-----------|---------|
| Memory (virtual) | 256 MB default | RLIMIT_AS in preexec_fn | Linux |
| CPU time | 10s default | RLIMIT_CPU in preexec_fn | Linux |
| Process count | 50 | RLIMIT_NPROC in preexec_fn | Linux |
| Output file size | 50 MB | RLIMIT_FSIZE in preexec_fn | Linux |
| Wall-clock timeout (subprocess) | action.timeout_seconds | subprocess.communicate(timeout=) | All |
| Wall-clock timeout (in-process) | action.timeout_seconds | ThreadPoolExecutor.result(timeout=) | All |
| Read size (Python) | 5 MB | FilesystemAdapter.max_read_size | All (existing) |
| Write size (Python) | 50 MB | FilesystemAdapter.max_write_size | All (existing) |

New SandboxConfig fields:
  cpu_limit_seconds: Optional[int] = 10
  max_processes: Optional[int] = 50
  max_output_mb: Optional[int] = 50

---

## H. Network Isolation Design

Stage 4 approach (no kernel namespaces needed):

For Tier 0 (in-process Python handlers):
- Browser handlers (Playwright) manage their own browser process.
- No additional network restriction at Python level.
- Browser actions are LEVEL_2_MODIFY --> require human approval before execution.

For Tier 1 (subprocess):
- Subprocess env does NOT contain http_proxy, https_proxy, HTTP_PROXY, HTTPS_PROXY,
  ALL_PROXY, NO_PROXY, or any network credential.
- Command allowlist does NOT include: wget, curl, nc, ssh, scp, rsync, ftp, nmap.

Future (NOT Stage 4):
- CLONE_NEWNET namespace via bubblewrap (bwrap) for full network isolation.
- Requires: sudo apt install bubblewrap (no root execution, but binary required).

---

## I. Integration Points: PolicyEngine

No change to evaluation logic. Only add classifier rules:

In RiskClassifier.classify():

    elif action.action_type == "terminal.safe":
        return RiskLevel.LEVEL_1_NON_DESTRUCTIVE  # --> ALLOW (no approval)

    # Existing rule (unchanged):
    elif action.action_type.startswith("terminal.execute") or action.action_type.startswith("shell"):
        return RiskLevel.LEVEL_5_BLOCKED

PolicyEngine invariants (MUST NOT change):
- PolicyEngine must NEVER call any LLM.
- PolicyEngine must NEVER be bypassed, even if sandbox setup fails.
- PolicyEngine runs BEFORE sandbox setup, not after.
- PolicyEngine runs on the validated ActionDefinition, not on raw LLM text.

---

## J. Integration Points: ApprovalQueue

No change to approval mechanism.

Flow with Stage 4:
  PolicyEngine --> REQUIRE_APPROVAL --> human --> resume_from_approval() --> sandbox setup --> execute

The sandbox is entered AFTER approval is granted, not before.

The Approval model's action_parameters field must NOT include sandbox internal details
(workspace paths, resource limits). Only user-visible action type and parameters are shown.

---

## K. Integration Points: ExecutionEngine

### K.1 Critical Fix: Timeout Enforcement

Current code (BROKEN -- checks timeout after handler returns):
    def _run_handler():
        res = handler.execute(action)
        if time.time() - start_time > action.timeout_seconds:
            return ActionExecutionResult(...)  # NEVER REACHED if handler hangs
        return res

Replacement (CORRECT -- enforces timeout with future.result):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(handler_func)
        try:
            if action.sandbox_config.required:
                sandbox = SandboxManager()
                return sandbox.execute_in_sandbox(action, handler_func)
            else:
                return future.result(timeout=action.timeout_seconds)
        except concurrent.futures.TimeoutError:
            return ActionExecutionResult(
                success=False, output=None,
                error=f"ACTION_TIMEOUT: exceeded {action.timeout_seconds}s"
            )

### K.2 Sandbox Error Return Contract

All sandbox failures MUST return ActionExecutionResult(success=False, error=...).
They must NEVER raise exceptions to the orchestrator.

SandboxManager.execute_in_sandbox() error mapping:
  SandboxTimeoutError --> ActionExecutionResult(error="SANDBOX_TIMEOUT: ...")
  SandboxInitializationError --> ActionExecutionResult(error="SANDBOX_INIT_FAILED: ...")
  UnsupportedPlatformError --> ActionExecutionResult(error="UNSUPPORTED_PLATFORM")
  SubprocessNotAllowedError --> ActionExecutionResult(error="COMMAND_NOT_ALLOWED: ...")
  Exception --> ActionExecutionResult(error="SANDBOX_ERROR: ...")

Always in finally block: cgroup_manager.cleanup(task_id)

---

## L. Integration Points: Verifier

No change to VerificationEngine.verify() signature.

New deterministic verification for terminal.safe:
  In DeterministicVerifier.verify():
    elif action.action_type == "terminal.safe":
        if output and isinstance(output, dict) and output.get("returncode") == 0:
            return VerificationResult(success=True, ...)
        else:
            return VerificationResult(success=False, retry_suggested=True, ...)

Subprocess output passed to LLMSemanticVerifier is already truncated at 5000 chars
(existing behavior in verifier.py). This applies to terminal.safe stdout as well.

---

## M. Integration Points: RecoveryEngine

No change to RecoveryEngine.determine_recovery() signature.

Sandbox failure --> ActionExecutionResult(success=False) --> orchestrator calls
RecoveryEngine.determine_recovery() identically to any handler failure.

Expected recovery decisions by error type:
  SANDBOX_TIMEOUT --> RETRY (if retries remain), else REPLAN
  SANDBOX_INIT_FAILED --> FAIL (permanent, platform issue)
  UNSUPPORTED_PLATFORM --> FAIL (permanent)
  SANDBOX_ERROR (general) --> RETRY once, then REPLAN
  Exit code non-zero --> RETRY (if retries remain), else REPLAN
  COMMAND_NOT_ALLOWED --> FAIL (policy violation, not retriable)

No new RecoveryDecisionResult values needed.

---

## N. Ubuntu-Specific Implementation Approach

### N.1 Compatibility Matrix

| Feature | Ubuntu 20.04 | Ubuntu 22.04 | Ubuntu 24.04 |
|---------|-------------|-------------|-------------|
| resource.setrlimit() (no root) | YES | YES | YES |
| subprocess.run(timeout=) | YES | YES | YES |
| cgroups v2 default | NO (hybrid) | YES | YES |
| systemd-run --user scope | YES | YES | YES |
| bubblewrap (optional) | apt install | apt install | apt install |
| python3-seccomp (optional) | apt install | apt install | apt install |
| O_NOFOLLOW open flag | YES | YES | YES |

Target: Ubuntu 22.04 LTS as primary runtime.
All Stage 4 features work on Ubuntu 22.04+ WITHOUT ROOT.

### N.2 No Root Required

resource.setrlimit(): standard POSIX API, no privileges
subprocess.run(shell=False): standard library
ThreadPoolExecutor: standard library
O_NOFOLLOW: standard open flag (POSIX)
command allowlist: Python-level check

Optional future hardening requiring system config (NOT Stage 4):
- cgroups v2 delegation: default on Ubuntu 22.04+ desktop sessions
- bubblewrap: sudo apt install bubblewrap (no root at runtime)
- seccomp: sudo apt install libseccomp-dev (no root at runtime)

---

## O. Required Files to Create / Modify

### Create (New Files)

| File | Purpose |
|------|---------|
| apps/api/app/agent/sandbox/subprocess_runner.py | SafeSubprocessRunner class |
| apps/api/app/agent/sandbox/resource_limits.py | Platform-aware resource.setrlimit() wrapper |
| apps/api/app/tests/agent/test_safe_subprocess.py | Subprocess isolation tests |
| apps/api/app/tests/agent/test_resource_limits.py | Resource limit tests (skip on Windows) |
| apps/api/app/tests/agent/test_execution_timeout.py | Timeout enforcement tests |

### Modify (Existing Files)

| File | Change | Risk |
|------|--------|------|
| executor.py | Fix timeout: ThreadPoolExecutor.result(timeout=) | Low |
| sandbox/manager.py | Real coordination + guaranteed finally cleanup | Medium |
| sandbox/cgroups.py | Implement resource.setrlimit() via preexec_fn | Medium |
| sandbox/namespaces.py | Workspace-CWD enforcement | Low |
| sandbox/seccomp.py | Graceful unavailable message (Phase 4e optional) | Low |
| sandbox/exceptions.py | Add SandboxTimeoutError, SandboxResourceError, SubprocessNotAllowedError | Low |
| policy.py | Add terminal.safe --> LEVEL_1_NON_DESTRUCTIVE | Low |
| actions/registry.py | Register terminal.safe handler | Low |
| planner.py | Add terminal.safe support to LLMActionParameters | Low |
| adapters/linux/terminal/safe_commands.py | Add SafeSubprocessRunner integration | Medium |
| adapters/linux/filesystem/security.py | O_NOFOLLOW helper + NEVER_ALLOWED list | Low |
| agent/models.py | Add cpu_limit_seconds, max_processes, max_output_mb to SandboxConfig | Low |
| requirements.txt | Add seccomp (optional, marked Linux-only) | Low |
| tests/agent/test_sandbox.py | Replace stub tests with real behavior tests | Low |

### Must NOT Change (verified working E2E)

apps/api/app/agent/orchestrator.py        -- verified Stage 3
apps/api/app/agent/verifier.py            -- verified Stage 3
apps/api/app/agent/recovery.py            -- verified Stage 3
apps/api/app/agent/goal_understanding.py  -- verified Stage 3
apps/api/app/agent/llm/provider.py        -- verified Stage 3
apps/api/app/adapters/linux/filesystem/operations.py  -- stable
apps/api/app/adapters/linux/filesystem/snapshot.py    -- stable
apps/api/app/adapters/linux/filesystem/rollback.py    -- stable
apps/api/app/models/domain.py             -- DB schema
apps/api/app/api/                         -- API routes
apps/web/                                 -- frontend
docker-compose.yml                        -- infrastructure
.env.example                              -- no new secrets needed

---

## P. Required Dependencies

Stage 4 core: Python standard library only
  concurrent.futures (timeout)
  subprocess (execution)
  resource (Linux: resource limits)
  os (O_NOFOLLOW flags)
  signal (SIGTERM/SIGKILL)

Optional (graceful fallback if absent):
  seccomp==0.2.1 (pip) + libseccomp-dev (apt) -- syscall filtering, Phase 4e

requirements.txt addition:
  # seccomp -- optional, Linux only, Phase 4e
  # seccomp==0.2.1

Import in code:
  try:
      import seccomp
      SECCOMP_AVAILABLE = True
  except ImportError:
      SECCOMP_AVAILABLE = False

---

## Q. Test Strategy

### Q.1 Categories

1. Unit tests (Windows + Linux): Mock-based, no real OS interaction
2. Integration tests (Linux only): Real subprocess with actual limits
3. Security tests: Verify specific threat mitigations
4. Failure/recovery tests: Verify sandbox failures route to RecoveryEngine

### Q.2 Coverage Targets

| Component | Target |
|-----------|--------|
| subprocess_runner.py | 95% |
| resource_limits.py | 90% |
| executor.py (timeout fix) | 100% |
| sandbox/manager.py | 90% |
| Policy classification (terminal.safe) | 100% |

---

## R. Security Test Cases

### R.1 Path Security

test_path_traversal_blocked:
  path = "../../etc/passwd" --> FilesystemSecurityError

test_symlink_nofollow (Linux only):
  Symlink to /etc/passwd --> OSError (O_NOFOLLOW)

test_env_file_blocked:
  path = ".env" --> FilesystemSecurityError

test_ssh_key_blocked:
  path = "~/.ssh/id_rsa" --> FilesystemSecurityError

test_allowed_workspace_path:
  path = "~/.linuxpilot/workspace/test.txt" --> succeeds

test_never_allowed_system_path:
  path = "/etc/hosts" --> FilesystemSecurityError

### R.2 Subprocess Security

test_allowlist_rejects_rm:
  command = "rm" --> SubprocessNotAllowedError

test_allowlist_rejects_curl:
  command = "curl" --> SubprocessNotAllowedError

test_allowlist_rejects_bash:
  command = "bash" --> SubprocessNotAllowedError

test_allowlist_rejects_python:
  command = "python3" --> SubprocessNotAllowedError

test_no_shell_injection:
  args = ["; rm -rf /"] --> treated as literal arg (shell=False)

test_env_no_secrets:
  subprocess env must not contain LLM_API_KEY, DATABASE_URL, JWT_SECRET

test_env_home_redirected:
  HOME in subprocess env = workspace, not actual ~

test_cwd_is_workspace:
  subprocess cwd = workspace directory

### R.3 Resource Limits (Linux only)

test_memory_limit_enforced:
  command that allocates >256MB --> killed by RLIMIT_AS

test_cpu_limit_enforced:
  infinite loop command --> killed by RLIMIT_CPU after 10s

test_fork_bomb_limited:
  rapid fork command --> limited by RLIMIT_NPROC

### R.4 Policy Security

test_terminal_execute_blocked:
  action_type = "terminal.execute.rm -rf /" --> BLOCK

test_shell_blocked:
  action_type = "shell.run" --> BLOCK

test_terminal_safe_allowed:
  action_type = "terminal.safe" --> ALLOW (LEVEL_1)

test_unknown_action_blocked:
  action_type = "unknown.action" --> UnknownActionError

test_policy_evaluated_before_sandbox:
  Even if sandbox would fail, PolicyEngine runs first and can BLOCK

---

## S. Failure / Recovery Test Cases

test_sandbox_timeout_triggers_retry:
  subprocess times out --> RecoveryEngine --> RETRY

test_sandbox_init_failed_triggers_fail:
  Platform not Linux --> ActionExecutionResult(success=False) --> RecoveryEngine --> FAIL

test_sandbox_oom_triggers_replan:
  Memory limit hit --> RecoveryEngine --> REPLAN

test_sandbox_cleanup_always_runs:
  Subprocess crashes --> finally block runs cleanup

test_sandbox_error_no_exception_leak:
  Any sandbox error --> returns ActionExecutionResult, never raises to orchestrator

test_rollback_after_high_risk_sandbox_failure:
  High-risk action fails in sandbox --> ROLLING_BACK state entered

test_max_replans_then_fail:
  Repeated sandbox failures --> after max_replans=2, FAILED state

test_approval_not_bypassed_by_sandbox:
  LEVEL_2 action --> WAITING_APPROVAL still triggered (not skipped by sandbox)

test_terminal_safe_no_approval_needed:
  terminal.safe --> LEVEL_1 --> ALLOW (no approval required)

---

## T. Rollout Plan

### Stage 4a -- Timeout Enforcement (Priority: CRITICAL, Risk: LOW)

What: Fix executor.py timeout check.
Files: executor.py only.
New tests: test_execution_timeout.py
Validation: 64/64 existing tests pass + new timeout tests.
No Linux dependency. No new classes.

### Stage 4b -- Safe Subprocess Runner (Priority: HIGH, Risk: MEDIUM)

What: New terminal.safe action type with full subprocess isolation.
Files:
  sandbox/subprocess_runner.py (new)
  sandbox/resource_limits.py (new)
  sandbox/exceptions.py (new exceptions)
  policy.py (add terminal.safe classification)
  actions/registry.py (register handler)
  planner.py (add terminal.safe to LLMActionParameters)
New tests: test_safe_subprocess.py, test_resource_limits.py
Validation: All 64 + new tests pass.
Manual: Run terminal.safe with ls on Linux.

### Stage 4c -- Sandbox Manager Wiring (Priority: HIGH, Risk: LOW)

What: Implement CgroupManager.apply_limits() using resource.setrlimit() preexec_fn.
      Update SandboxManager to properly coordinate subsystems with guaranteed cleanup.
      Add new SandboxConfig fields.
Files:
  sandbox/cgroups.py
  sandbox/manager.py
  agent/models.py (SandboxConfig)
New tests: test_resource_limits.py extended.
Validation: All tests pass. Linux: resource limits actually enforced.

### Stage 4d -- Filesystem Hardening (Priority: MEDIUM, Risk: LOW)

What: Add O_NOFOLLOW to FilesystemAdapter opens.
      Add NEVER_ALLOWED list to FilesystemSecurityPolicy.
Files:
  adapters/linux/filesystem/security.py
  adapters/linux/filesystem/operations.py
New tests: test_filesystem_security.py extended with symlink tests.
Validation: All 64 + new tests pass.

### Stage 4e -- Seccomp (Priority: LOW, Optional)

What: Implement SeccompManager.apply_filters() using python-seccomp.
      Graceful fallback if libseccomp not installed.
Files:
  sandbox/seccomp.py
  requirements.txt
New tests: test_sandbox.py extended (skip on Windows, skip if unavailable).
Validation: Tests pass on Linux with and without libseccomp.

---

## Summary

Current sandbox status:         STUBS ONLY -- zero enforcement
Actions currently sandboxed:    NONE (sandbox_config.required never set)
Timeout enforcement:            BROKEN (post-hoc check)
Path security:                  ACTIVE (but no TOCTOU protection)
PolicyEngine:                   FULLY ACTIVE
Approval gate:                  FULLY ACTIVE
Snapshot/Rollback:              FULLY ACTIVE
LLM->shell injection:           PREVENTED (structured output + whitelist)

After Stage 4:
Timeout enforcement:            REAL (ThreadPoolExecutor.result(timeout=))
Safe terminal commands:         ACTIVE (terminal.safe with allowlist)
Resource limits:                ACTIVE (resource.setrlimit() on Linux)
TOCTOU protection:              ACTIVE (O_NOFOLLOW on Linux)
Never-allowed paths:            ACTIVE (NEVER_ALLOWED list in security policy)
Subprocess env isolation:       ACTIVE (minimal cleaned env, no secrets)
Root required:                  NO -- works on standard Ubuntu 22.04+ desktop
Docker/CI compatible:           YES
Free/open-source:               YES (Python stdlib + optional LGPL seccomp)
