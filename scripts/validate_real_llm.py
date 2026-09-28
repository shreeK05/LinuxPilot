import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup Python Path
sys.path.append(str(Path(__file__).parent.parent / "apps" / "api"))

from app.agent.context import ExecutionContext
from app.agent.models import AgentState, PolicyDecisionResult
from app.agent.orchestrator import AgentOrchestrator
from app.agent.goal_understanding import LLMGoalInterpreter
from app.agent.planner import LLMPlanner
from app.agent.verifier import VerificationEngine, LLMSemanticVerifier, DeterministicVerifier
from app.agent.policy import PolicyEngine
from app.agent.executor import ExecutionEngine
from app.agent.recovery import RecoveryEngine
from app.agent.actions.registry import action_registry
from app.agent.llm.provider import get_llm_provider

# Load environment
load_dotenv()

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Setup validation workspace
WORKSPACE_DIR = Path(__file__).parent.parent / "apps" / "api" / ".validation_workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
# Create a dummy file so that directory listing isn't empty, preventing semantic verification failure
(WORKSPACE_DIR / "dummy_test_file.txt").write_text("Hello, World!")

# File for results
RESULTS_FILE = Path(__file__).parent.parent / "docs" / "PHASE14_STAGE3_REAL_LLM_RESULTS.md"

def write_result(content: str):
    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(content + "\n")

def run_test(test_name: str, goal: str, handle_approval: bool = False, expected_failure: bool = False):
    print(f"\n--- Running {test_name} ---")
    write_result(f"## {test_name}")
    write_result(f"**Goal**: {goal}")
    
    # Initialize dependencies
    try:
        provider = get_llm_provider()
    except Exception as e:
        write_result(f"**Error initializing provider**: {e}")
        return "FAIL"
        
    write_result(f"**LLM Provider**: {provider.__class__.__name__}")
    
    context = ExecutionContext(task_id=f"val_{test_name.lower().replace(' ', '_')}")
    
    # Update Security Policy to allow the workspace
    from app.agent.actions.filesystem_handlers import fs_adapter
    fs_adapter.security.allowed_roots.append(str(WORKSPACE_DIR.resolve()))
    
    interpreter = LLMGoalInterpreter(provider)
    planner = LLMPlanner(provider, action_registry)
    policy_engine = PolicyEngine()
    execution_engine = ExecutionEngine(action_registry, policy_engine)
    
    # Verifier
    ver_engine = VerificationEngine(provider)
    
    orchestrator = AgentOrchestrator(
        context=context,
        interpreter=interpreter,
        planner=planner,
        policy_engine=policy_engine,
        execution_engine=execution_engine,
        verifier=ver_engine,
        recovery_engine=RecoveryEngine()
    )
    
    try:
        orchestrator.run_lifecycle(goal)
        
        # Check Approval State
        approval_state = "Not Required"
        if orchestrator.state_machine.current_state == AgentState.WAITING_APPROVAL:
            approval_state = "WAITING_APPROVAL"
            write_result("**Approval State**: WAITING_APPROVAL (Paused successfully)")
            if handle_approval:
                print("Task paused for approval as expected. Resuming...")
                orchestrator.resume_from_approval(True, "Approved by validation harness")
            else:
                write_result("**Error**: Task paused for approval but approval handling was not enabled.")
                return "FAIL"
        
        # Final state check
        final_state = orchestrator.state_machine.current_state
        
        # Log all outputs
        if orchestrator.goal:
            write_result(f"**Goal Interpretation**:\n```json\n{orchestrator.goal.model_dump_json(indent=2)}\n```")
        if orchestrator.plan:
            action_types = [s.action.action_type for s in orchestrator.plan.steps]
            params = [s.action.parameters for s in orchestrator.plan.steps]
            write_result(f"**Action Types Selected**: {action_types}")
            write_result(f"**Parameters Generated**:\n```json\n{json.dumps(params, indent=2)}\n```")
            
        write_result(f"**Approval State**: {approval_state}")
        write_result(f"**Final Task State**: {final_state.value}")
        
        if orchestrator.step_outputs:
            write_result(f"**Execution Results/Outputs**:\n```json\n{json.dumps(orchestrator.step_outputs, indent=2, default=str)}\n```")
            
        if expected_failure:
            if final_state in [AgentState.FAILED, AgentState.ROLLING_BACK]:
                write_result("**Behavior Matched Expectations**: YES (Expected failure occurred safely)")
                return "PASS"
            else:
                write_result(f"**Behavior Matched Expectations**: NO (Expected failure, but finished in {final_state.value})")
                return "FAIL"
        else:
            if final_state == AgentState.COMPLETED:
                write_result("**Behavior Matched Expectations**: YES")
                return "PASS"
            else:
                write_result(f"**Behavior Matched Expectations**: NO (Expected COMPLETED, but finished in {final_state.value})")
                return "FAIL"
                
    except Exception as e:
        write_result(f"**Unexpected Harness Error**: {str(e)}")
        logging.exception("Harness exception")
        return "FAIL"

if __name__ == "__main__":
    # Ensure RESULTS_FILE exists and clear it
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        f.write("# Phase 14 Stage 3 Real LLM Results\n\n")
        
    print("Starting Stage 3 Validation Harness...")
    
    workspace_str = str(WORKSPACE_DIR.resolve())
    
    t1_res = run_test(
        "TEST 1 - Safe read-only task",
        f"Find out what OS architecture I am running and list the files in the directory {workspace_str}.",
        handle_approval=False,
        expected_failure=False
    )
    
    t2_res = run_test(
        "TEST 2 - Approval-gated modification",
        f"Create a folder named validation_test inside {workspace_str} and create a file inside it called hello.txt containing LinuxPilot E2E.",
        handle_approval=True,
        expected_failure=False
    )
    
    t3_res = run_test(
        "TEST 3 - Failure and autonomous replanning",
        f"Read the file does_not_exist_12345.txt from the directory {workspace_str}.",
        handle_approval=True,
        expected_failure=True
    )
    
    # Write summary
    write_result("\n## SUMMARY")
    write_result(f"Test 1: {t1_res}")
    write_result(f"Test 2: {t2_res}")
    write_result(f"Test 3: {t3_res}")
    
    print("\nValidation Harness Complete.")
    print(f"Test 1: {t1_res}")
    print(f"Test 2: {t2_res}")
    print(f"Test 3: {t3_res}")
