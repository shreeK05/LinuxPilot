# Phase 14 Stage 4a — Timeout Implementation

## A. Problem found
The `ExecutionEngine` implemented a timeout check *after* the `handler.execute()` method returned. If a handler hung indefinitely (e.g., an infinite loop or a blocked I/O operation), the engine would block indefinitely and never trigger the timeout failure condition.

## B. Root cause
The previous code measured time before the execution and compared it to the current time after `handler.execute(action)` had finished synchronously. It lacked a mechanism to actively interrupt or bound the execution time of a hanging handler.

## C. Exact implementation change
Modified `apps/api/app/agent/executor.py` to run the handler execution in a `concurrent.futures.ThreadPoolExecutor`. We submit the execution task (`_execute_task`) to a worker thread and use `future.result(timeout=action.timeout_seconds)` to enforce a hard boundary.
We added `executor.shutdown(wait=False, cancel_futures=True)` in a `finally` block to ensure the ThreadPoolExecutor does not block the main thread waiting for the timed-out handler to finish. 
Sandbox execution (`SandboxManager.execute_in_sandbox`) is also wrapped within this task, ensuring that even if the stub hangs, the timeout correctly catches it.

## D. Timeout behavior
If the `action.timeout_seconds` is reached, `future.result()` raises a `concurrent.futures.TimeoutError`. The timeout is strictly enforced by Python's `concurrent.futures` implementation.

## E. Error handling behavior
Upon catching `TimeoutError`, the engine gracefully returns an `ActionExecutionResult` with `success=False` and `error="ACTION_TIMEOUT: Action exceeded {timeout}s limit"`. This avoids crashing the orchestrator and safely routes the error to the `RecoveryEngine` for replanning or retrying.

## F. Tests added
Created `apps/api/app/tests/agent/test_execution_timeout.py` containing three tests:
1. `test_fast_action_completes_successfully`: Verifies normal operations succeed.
2. `test_action_completing_just_before_timeout_succeeds`: Verifies close calls are not prematurely cancelled.
3. `test_slow_action_exceeds_timeout_returns_controlled_failure`: Verifies that a handler explicitly taking longer than the `timeout_seconds` configuration fails immediately and gracefully returns the expected error string.

## G. Validation results
- The new focused tests passed.
- The entire backend test suite (`pytest`) passed, confirming no regressions.
- The frontend build (`npm run build`) completed successfully.
- `git diff --check` confirmed no whitespace or structural issues.

## H. Files changed
1. `apps/api/app/agent/executor.py` (implementation)
2. `apps/api/app/tests/agent/test_execution_timeout.py` (tests)

## I. Security impact
Improved system robustness. Handlers (and in future stages, subprocesses) can no longer execute denial-of-service attacks by hanging the orchestrator process indefinitely. No new privileges were introduced, and no shell injections were made possible.

## J. Confirmation that Stage 4b/4c/4d/4e were NOT implemented
I confirm that NO subprocess isolation (`terminal.safe`), namespaces, seccomp filters, cgroup limits, or filesystem hardening (like `O_NOFOLLOW` or `NEVER_ALLOWED`) have been added yet. All existing approval gates, policy rules, and schemas remain strictly unmodified.
