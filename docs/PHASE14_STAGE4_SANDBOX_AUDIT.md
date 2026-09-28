# Phase 14 Stage 4 — Sandbox Architecture Audit

> **Read-only audit — NO production code was modified to produce this document.**
> Generated: 2026-09-23

---

## 1. Executive Summary

The current LinuxPilot sandbox is **entirely stub code**. All three isolation subsystems (cgroups, namespaces, seccomp) contain no real enforcement logic — only `pass` statements and Linux platform guards. On Windows the sandbox gracefully returns `UNSUPPORTED_PLATFORM`. On Linux the sandbox call chain runs but applies **zero isolation** before handing control back to the Python handler.

This means that today, any approved action on a Linux host runs with the full privileges of the LinuxPilot process. The application-level `FilesystemSecurityPolicy` (path validation) and the `PolicyEngine` (risk classification + approval gating) are the **only active security controls**.

The goal of Stage 4 is to replace the stub with a real, layered isolation engine that can run safely on an ordinary Ubuntu 24.04 desktop **without root** where possible, and with clearly scoped privilege where unavoidable.

---

## 2. Current Architecture

### 2.1 Sandbox Module Files

| File | Current State | Purpose |
|------|--------------|---------|
| `sandbox/manager.py` | Active | Orchestrates setup; correctly guards on non-Linux |
| `sandbox/cgroups.py` | **STUB** | `apply_limits()` = `pass`; `add_process()` = `pass`; `cleanup()` = `pass` |
| `sandbox/namespaces.py` | **STUB** | `setup_namespaces()` = `pass`; `mount_filesystem()` = `pass` |
| `sandbox/seccomp.py` | **STUB** | `apply_filters()` = `pass` |
| `sandbox/exceptions.py` | Active | `UnsupportedPlatformError`, `SandboxInitializationError` |

### 2.2 Execution Flow: LLM Action → Sandbox

```
User NL Goal
  │
  ▼
AgentOrchestrator.run_lifecycle()
  │  [UNDERSTANDING]  LLMGoalInterpreter → GoalUnderstanding
  │  [PLANNING]       LLMPlanner → ExecutionPlan (DAG)
  │  [POLICY_CHECK]   PolicyEngine → BLOCK / REQUIRE_APPROVAL / ALLOW
  │                   (If REQUIRE_APPROVAL → suspend → human resumes)
  │  [EXECUTING]
  ├─► ExecutionEngine.execute_action(ActionDefinition)
  │         ├─ policy re-check (defense-in-depth)
  │         └─ if sandbox_config.required == True
  │                 └─► SandboxManager.execute_in_sandbox()
  │                       ├─ CgroupManager.apply_limits()    [STUB: pass]
  │                       ├─ NamespaceManager.setup_namespaces() [STUB: pass]
  │                       ├─ SeccompManager.apply_filters()  [STUB: pass]
  │                       └─► handler_func()  ← actual Python handler
  │  [VERIFYING]      VerificationEngine.verify()
  └─► COMPLETED / FAILED  (RecoveryEngine handles retry/replan/rollback)
```

### 2.3 Active Security Controls (Working Today)

| Layer | Location | What It Does |
|-------|----------|--------------|
| Action Registry whitelist | `registry.py` | LLM can only name registered action types |
| Risk Classifier | `policy.py` | Maps `action_type` → `RiskLevel`; `terminal.execute.*` → LEVEL_5_BLOCKED |
| Policy Engine | `policy.py` | BLOCK ≥ 5; REQUIRE_APPROVAL ≥ 2; REQUIRE_SNAPSHOT ≥ 3 |
| Approval Gate | `orchestrator.py` | Suspends at WAITING_APPROVAL; resumes on human approval |
| Path Security | `filesystem/security.py` | `Path.resolve()` + `relative_to(allowed_roots)` |
| Read/Write Size Cap | `filesystem/operations.py` | 5 MB read; 50 MB write |
| Snapshot Before Modify | `filesystem/snapshot.py` | SHA-256 snapshot before WRITE/DELETE/MOVE/RENAME |
| Rollback | `filesystem/rollback.py` | Restores files from snapshots in reverse order |
| LLM Structured Output | `provider.py` | `beta.chat.completions.parse` enforces strict schema |
| Exponential Backoff | `provider.py` | tenacity retry on RateLimitError, Timeout |

### 2.4 Critical Gap: Sandbox Is Never Triggered

`executor.py` line 46: `if action.sandbox_config.required:` — but no registered action
sets `sandbox_config.required = True`. The `LLMPlanner` produces
`SandboxConfig(required=False)` for every step. The sandbox path is **dead code** in
normal operation today. On Linux, the stub sandbox runs but applies zero isolation.

---

## 3. Security Gaps Discovered

| ID | Gap | Severity |
|----|-----|---------|
| GAP-1 | Sandbox stubs — zero runtime enforcement | Critical |
| GAP-2 | Sandbox never triggered — dead code path | Critical |
| GAP-3 | No process isolation for any action | High |
| GAP-4 | Timeout checked after execution (post-hoc, unenforceable) | High |
| GAP-5 | No enforcement preventing future handlers from calling subprocess/os.system | High |
| GAP-6 | No filesystem workspace boundary at OS level | High |
| GAP-7 | No memory/CPU resource limits — OOM possible | Medium |
| GAP-8 | Network access unrestricted for all handlers | Medium |
| GAP-9 | Symlink TOCTOU race between validate_path() and file open | Medium |
| GAP-10 | No privilege drop / user separation | Medium |
| GAP-11 | Snapshot directory outside FilesystemSecurityPolicy bounds | Low |
| GAP-12 | No `terminal.safe` action type for curated safe commands | Low |

---

## 4. Required Isolation Boundaries

```
┌────────────────────────────────────────────────────────────────────┐
│  TRUSTED APPLICATION PROCESS                                        │
│  FastAPI + AgentOrchestrator + PolicyEngine + ApprovalGate          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  SAFE HANDLERS (no subprocess; runs in-process with timeout)  │  │
│  │  FilesystemAdapter · SafeTerminalCommands · DocumentHandlers  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  SANDBOXED EXECUTION (new: subprocess isolation)              │  │
│  │  Workspace: ~/.linuxpilot/workspace/                          │  │
│  │  Resource limits: resource.setrlimit() (AS, CPU, NPROC)       │  │
│  │  Network: env cleaned; proxy vars removed                     │  │
│  │  Timeout: subprocess timeout → SIGTERM → SIGKILL              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  PROTECTED HOST FILESYSTEM (NEVER accessible)                       │
│  /etc  /usr  /bin  /sys  /proc  /dev                                │
└────────────────────────────────────────────────────────────────────┘
```

---

## 5. Isolation Strategy

### 5.1 Filesystem Isolation

**Keep:** `validate_path()` + `allowed_roots` + size caps

**Add:**
1. **TOCTOU fix**: Open files using `os.open(path, os.O_RDONLY | os.O_NOFOLLOW)` instead
   of `pathlib.open()` to prevent symlink swap between validate and open.
2. **Dedicated workspace**: `~/.linuxpilot/workspace/` as the only writable root for
   agent-created files.
3. **Snapshot directory hardening**: Add `~/.linuxpilot/snapshots/` to a separate
   write-only `FilesystemSecurityPolicy` instance.

**Not needed (require root):** OverlayFS, chroot, per-action Docker containers.

### 5.2 Process Isolation — Tiered Approach

| Tier | Actions | Mechanism |
|------|---------|-----------|
| Tier 1 | All existing Python handlers | `ThreadPoolExecutor.result(timeout=N)` — kills thread on timeout |
| Tier 2 | New `terminal.safe` action type | `subprocess.run(shell=False, args=[cmd]+args, cwd=workspace, timeout=N, env=minimal)` |
| Tier 3 (future) | High-impact shell operations | `systemd-run --user --scope` — documented, not in Stage 4 |

**Never allowed:** `os.system()`, `Popen(shell=True)`, `eval()`, `exec()`

**Tier 2 command allowlist (proposed):**
`ls`, `cat`, `pwd`, `find`, `which`, `file`, `du`, `df`, `echo`, `wc`, `sort`, `head`, `tail`, `grep`

### 5.3 Resource Limits

**Mechanism:** `resource.setrlimit()` via `preexec_fn` in `subprocess.Popen` — works
without root on Ubuntu 22.04+.

```python
import resource

def apply_resource_limits(memory_mb: int, cpu_seconds: int):
    resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024**2, memory_mb * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    resource.setrlimit(resource.RLIMIT_NPROC, (50, 50))  # fork bomb protection
```

**cgroups v2** (optional hardening, requires systemd user slice delegation):
Write to `/sys/fs/cgroup/user.slice/user-$(id -u).slice/` — available on Ubuntu 24.04
desktop sessions without root. Not required for Stage 4.

**Windows:** `resource` module unavailable — `apply_resource_limits()` returns no-op
with a logged warning.

### 5.4 Network Isolation

**Stage 4:** Pass a minimal `env` dict to subprocess that strips all proxy, DNS, and
credential variables (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `LD_PRELOAD`, etc.).

**Future (not Stage 4):** `CLONE_NEWNET` namespace — requires `CAP_SYS_ADMIN`.

### 5.5 Privilege Strategy

Do NOT attempt to drop to a separate OS user in Stage 4 (requires `sudo`/`setuid`).

Layered defense instead:
1. Path validation (existing)
2. Explicit subprocess allowlist (new)
3. `resource.setrlimit()` in child (new)
4. `shell=False` enforced (new)
5. Policy Engine approval gate (existing)

Future: `systemd-run --user --scope` for scoped resource limits without root.

### 5.6 Timeout Enforcement

**Current bug:** `executor.py` checks timeout after handler returns — non-functional.

**Fix:**
```python
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
    future = ex.submit(handler_func)
    try:
        return future.result(timeout=action.timeout_seconds)
    except concurrent.futures.TimeoutError:
        return ActionExecutionResult(
            success=False, output=None,
            error="ACTION_TIMEOUT: Handler exceeded time limit"
        )
```

For subprocess Tier 2: `subprocess.run(timeout=N)` → `TimeoutExpired` → SIGTERM
→ 2s wait → SIGKILL.

### 5.7 Kill / Cleanup Sequence

1. `TimeoutExpired` or error caught
2. `process.terminate()` (SIGTERM)
3. `time.sleep(2)` then `process.kill()` (SIGKILL) if still alive
4. `cgroups.cleanup(task_id)` in `finally` block
5. Return `ActionExecutionResult(success=False, error="ACTION_TIMEOUT")`
6. `RecoveryEngine` handles `REPLAN` or `ROLLBACK`

### 5.8 Rollback Interaction

Sandbox introduces no new rollback mechanism. The existing `SnapshotManager` +
`RollbackManager` remains the rollback path. Sandbox layer MUST:
- NOT bypass snapshot creation (snapshot happens in handler before write — correct)
- Return `success=False` on sandbox failure so orchestrator triggers recovery
- Never silently swallow exceptions from the cleanup path

---

## 6. Ubuntu Compatibility

| Requirement | Ubuntu 22.04 | Ubuntu 24.04 | Notes |
|-------------|-------------|-------------|-------|
| cgroups v2 (default) | ✅ | ✅ | Check `/sys/fs/cgroup/cgroup.controllers` |
| `resource.setrlimit()` (no root) | ✅ | ✅ | Standard library |
| `subprocess` with `timeout=` | ✅ | ✅ | Standard library |
| `systemd --user` scopes | ✅ | ✅ | Future hardening |
| `python-seccomp` | ✅ | ✅ | `sudo apt install libseccomp-dev` required |
| Cgroup delegation (no root) | ⚠️ Needs config | ✅ default | Optional for Stage 4 |
| OverlayFS (no root) | ❌ | ❌ | Not planned |

**Conclusion:** Stage 4 can be fully implemented on Ubuntu 22.04+ **without root** using
`resource.setrlimit()` + `subprocess.run(shell=False)` + Python path enforcement.

---

## 7. Docker / CI Compatibility

- No additional Docker service needed
- `subprocess` with `shell=False` works in Docker containers
- `resource.setrlimit()` works in Docker (container provides process isolation)
- Avoid cgroups v2 in Docker to skip `--cgroupns=host` dependency

---

## 8. Windows Development / Testing Strategy

1. `SandboxManager.is_linux` guard already exists — keep this pattern
2. New `SafeSubprocessRunner` checks `platform.system()`; returns `UNSUPPORTED_PLATFORM` on Windows
3. All tests use `MockSandbox` that records calls without executing
4. Linux-specific tests: `@pytest.mark.skipif(platform.system() != 'Linux', ...)`
5. Timeout tests use `concurrent.futures` — works cross-platform
6. Path security tests work cross-platform (`pathlib` handles both)

---

## 9. Security Threat Model

| Threat | Current Mitigation | Stage 4 Mitigation |
|--------|-------------------|-------------------|
| Path traversal / symlink escape | `validate_path()` + `resolve()` | + `O_NOFOLLOW` open flag |
| Arbitrary shell command injection | `terminal.execute.*` blocked | + subprocess allowlist for `terminal.safe` |
| Host filesystem modification | `allowed_roots` whitelist | + dedicated writable workspace |
| Process fork bomb | None | + `resource.setrlimit(RLIMIT_NPROC)` |
| Memory exhaustion | 5 MB read cap (Python-only) | + `resource.setrlimit(RLIMIT_AS)` |
| CPU exhaustion | None | + `resource.setrlimit(RLIMIT_CPU)` |
| Handler hangs indefinitely | None | + `ThreadPoolExecutor.result(timeout=)` |
| Subprocess survives handler return | N/A (no subprocess today) | + SIGTERM/SIGKILL + cgroup cleanup |
| Privilege escalation via SUID binary | None | + `env` cleared in subprocess |
| Network exfiltration | None | + env cleanup removes proxy/credential vars |
| LLM → arbitrary shell | Structured output schema | Unchanged (action whitelist) |
| Snapshot directory poisoning | None | + secondary `FilesystemSecurityPolicy` |

---

## 10. What Must Remain OUTSIDE the Sandbox

- `PolicyEngine` logic — always runs in the trusted application process
- `ApprovalGate` — must be in the trusted process; never delegatable to a subprocess
- JWT authentication — API auth layer
- Database connections — PostgreSQL, audit log
- Snapshot storage — written by the trusted process, not by the sandbox
- LLM API key — never passed to subprocess environment
- `/etc`, `/usr`, `/bin`, `/sbin`, `/sys`, `/proc`, `/dev` — never in `allowed_roots`

---

## 11. Proposed Implementation Phases

### Phase 4a — Timeout Enforcement (no Linux dependency)
Fix `executor.py` timeout check to use `ThreadPoolExecutor.result(timeout=)`.
Works on Windows and Linux. Highest priority — fixes GAP-4.

### Phase 4b — Safe Subprocess Runner (`terminal.safe`)
New `SafeSubprocessRunner` with explicit command allowlist, `shell=False`, `cwd=workspace`,
minimal `env`, and `timeout=N` with SIGKILL cleanup.
Register `terminal.safe` in `registry.py`.
`PolicyEngine`: `terminal.safe` → `LEVEL_1_NON_DESTRUCTIVE` → `ALLOW`.
Fixes GAP-5, GAP-6, GAP-8, GAP-12.

### Phase 4c — Resource Limits via `resource.setrlimit()`
Implement `CgroupManager.apply_limits()` using `preexec_fn` in `subprocess.Popen`.
Works without root on Ubuntu. Fixes GAP-7.

### Phase 4d — Seccomp Filtering (Linux only, optional)
Use `python-seccomp` for syscall whitelist in child process.
Graceful fallback if `libseccomp` not installed. Addresses GAP-3 at kernel level.

### Phase 4e — Sandbox Configuration Wiring
Wire `SandboxConfig` fields to `LLMPlanner` for high-risk actions.
Update `PolicyEngine` for new action types. Fixes GAP-2.

---

## 12. Files Requiring Modification

### Modify
| File | Change |
|------|--------|
| `apps/api/app/agent/executor.py` | Fix timeout with `ThreadPoolExecutor` |
| `apps/api/app/agent/sandbox/manager.py` | Real coordination + guaranteed cleanup |
| `apps/api/app/agent/sandbox/cgroups.py` | `resource.setrlimit()` via `preexec_fn` |
| `apps/api/app/agent/sandbox/namespaces.py` | Workspace-CWD isolation |
| `apps/api/app/agent/sandbox/seccomp.py` | `python-seccomp` filter (Linux only) |
| `apps/api/app/agent/sandbox/exceptions.py` | Add `SandboxTimeoutError`, `SandboxResourceError` |
| `apps/api/app/agent/policy.py` | Add `terminal.safe` → `LEVEL_1` |
| `apps/api/app/agent/actions/registry.py` | Register `terminal.safe` handler |
| `apps/api/app/agent/planner.py` | Add `terminal.safe` to `LLMActionParameters` |
| `apps/api/app/adapters/linux/terminal/safe_commands.py` | Add `SafeSubprocessRunner` |
| `apps/api/app/adapters/linux/filesystem/security.py` | `O_NOFOLLOW` hardening |
| `apps/api/requirements.txt` | Add `seccomp` (optional) |
| `apps/api/app/tests/agent/test_sandbox.py` | Replace stub tests with real tests |

### Create (New Files)
| File | Purpose |
|------|---------|
| `apps/api/app/agent/sandbox/subprocess_runner.py` | `SafeSubprocessRunner` class |
| `apps/api/app/agent/sandbox/resource_limits.py` | Platform-aware resource limit application |
| `apps/api/app/tests/agent/test_safe_subprocess.py` | Subprocess isolation tests |
| `apps/api/app/tests/agent/test_resource_limits.py` | Resource limit tests (skip on Windows) |

---

## 13. Test Strategy

### Phase 4a (Timeout)
- `test_executor_timeout_enforcement` — handler sleeps > timeout → `ACTION_TIMEOUT` returned
- `test_executor_no_timeout_on_fast_action` — fast handler completes normally

### Phase 4b (Safe Subprocess)
- `test_safe_subprocess_allowlist_pass` — `ls -la workspace` executes on Linux
- `test_safe_subprocess_allowlist_block` — `rm -rf /` raises `SubprocessNotAllowedError`
- `test_safe_subprocess_no_shell_injection` — `; rm -rf /` treated as literal arg, not shell
- `test_safe_subprocess_cwd_restriction` — command cannot escape workspace directory
- `test_safe_subprocess_timeout` — sleeping command killed; returns `ACTION_TIMEOUT`
- `test_safe_subprocess_env_clean` — subprocess env lacks `HOME`, `PATH`, `LD_PRELOAD`
- `test_safe_subprocess_windows_stub` — returns `UNSUPPORTED_PLATFORM` on Windows

### Phase 4c (Resource Limits)
- `test_resource_limits_memory` — subprocess limited to N MB (Linux only)
- `test_resource_limits_cpu` — CPU-intensive subprocess hits `RLIMIT_CPU` (Linux only)
- `test_resource_limits_noproc` — subprocess cannot fork excessively (Linux only)
- `test_resource_limits_windows_noop` — `apply_limits()` is no-op on Windows

### Phase 4d (Seccomp)
- `test_seccomp_blocks_exec` — subprocess cannot `execve()` arbitrary binaries (Linux only)
- `test_seccomp_allows_reads` — subprocess can still `read()` files within workspace (Linux only)
- `test_seccomp_graceful_unavailable` — fallback if `libseccomp` not installed

### Phase 4e (Wiring)
- `test_policy_terminal_safe_allowed` — `terminal.safe` → `LEVEL_1` → `ALLOW`
- `test_policy_terminal_execute_blocked` — `terminal.execute.arbitrary` → `LEVEL_5` → `BLOCK`
- `test_orchestrator_sandbox_triggered` — action with `sandbox_config.required=True` reaches `SandboxManager`
- `test_orchestrator_sandbox_failure_recovery` — sandbox error → `RecoveryEngine` REPLAN path

---

## 14. Open Questions

> **Q1: Workspace root location**
> Should the sandboxed writable workspace be `~/.linuxpilot/workspace/` (hidden) or
> `~/LinuxPilot/` (user-visible)? Affects user discoverability of agent output.

> **Q2: Seccomp — required or optional?**
> `python-seccomp` requires `libseccomp` on the host (`sudo apt install libseccomp-dev`).
> Required (adds system dependency) vs. optional/graceful-fallback (simpler install)?

> **Q3: `terminal.safe` allowlist scope**
> Proposed: `ls`, `cat`, `pwd`, `find`, `which`, `file`, `du`, `df`, `echo`, `wc`,
> `sort`, `head`, `tail`, `grep`. Does this match the target Ubuntu task scope?

> **Q4: Approval for `terminal.safe`**
> Proposed: `LEVEL_1` → `ALLOW` (no approval for read-only curated commands).
> Should any curated commands require approval (e.g., `grep` over sensitive directories)?

---

## 15. Status Summary

| Item | Status |
|------|--------|
| Current sandbox enforcement | ❌ None (all stubs) |
| Sandbox triggered in practice | ❌ Never (no action sets `required=True`) |
| Timeout enforcement | ❌ Post-hoc check only (non-functional) |
| Filesystem path security | ✅ Active (`validate_path`) |
| Approval gate | ✅ Active |
| Policy Engine risk classification | ✅ Active |
| Snapshot / Rollback | ✅ Active |
| LLM → shell injection prevention | ✅ Active (structured output + whitelist) |
| Can run on Ubuntu without root | ✅ Yes (proposed design: `resource.setrlimit` + subprocess) |
| Requires dangerous kernel privileges | ❌ No |
| Windows dev/test compatibility | ✅ Yes (platform guards + mocks) |
