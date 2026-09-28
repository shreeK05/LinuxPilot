# Phase 14 Stage 3: Real LLM End-to-End Validation Plan

## 1. Objective
Validate the complete Real-LLM execution path within the `AgentOrchestrator` using the `OpenAICompatibleProvider`, ensuring that the LLM can autonomously understand goals, plan actions, pass security checks, execute tasks, and semantically verify outputs in a real environment.

## 2. Pre-Validation Audit Findings
- **Inspected Components**: `.env.example`, `OpenAICompatibleProvider`, `LLMPlanner`, `LLMGoalInterpreter`, `LLMSemanticVerifier`, `AgentOrchestrator`, `PolicyEngine`, `ExecutionEngine`, `RecoveryEngine`.
- **What already works**: The deterministic pipeline, policy boundaries, Pydantic structured output mappings, execution engine routing, and Stage 2 reliability protections (exponential backoff & prompt truncation).
- **What needs validation**: The LLM's real-world capability to map open-ended natural language to exact action handlers (`action_type`) within the registry, handle parameters correctly, and intelligently replan if a step fails.
- **Bugs/Issues**: None discovered in Stage 2 implementation. 

## 3. Environment Configuration Required
To execute the real LLM validation script, the following environment variables MUST be set in a `.env` file (or exported in the shell) replacing the mock values.

```bash
# Example for OpenAI
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-real-key
LLM_MODEL=gpt-4o-mini

# OR Example for Groq
# LLM_PROVIDER=groq
# LLM_BASE_URL=https://api.groq.com/openai/v1
# LLM_API_KEY=gsk-your-real-key
# LLM_MODEL=llama-3.1-70b-versatile
```
*(CRITICAL: Do not commit the `.env` file containing the actual API key.)*

## 4. Test Matrix & Expected Behaviors

### Test Case 1: Non-Destructive Read (Risk Level 1)
- **Prompt**: *"Find out what OS architecture I am running and list the files in the current directory."*
- **Expected Behavior**: 
  - **Understanding**: Intent identifies OS info and directory listing.
  - **Planning**: Generates a DAG using `system.info` and `filesystem.list_directory`.
  - **Policy**: Evaluates to `RiskLevel.LEVEL_1_NON_DESTRUCTIVE` -> `ALLOW`.
  - **Execution**: Runs successfully without approval.
  - **Verification**: `LLMSemanticVerifier` correctly confirms the OS info and directory contents meet the objective.

### Test Case 2: Approval-Gated Modification (Risk Level 2)
- **Prompt**: *"Create a folder named 'validation_test' and write a file inside it called 'hello.txt' containing 'LinuxPilot E2E'."*
- **Expected Behavior**:
  - **Planning**: Generates `filesystem.create_directory` -> `filesystem.write_file`.
  - **Policy**: Evaluates to `RiskLevel.LEVEL_2_MODIFY` -> `REQUIRE_APPROVAL`.
  - **Approval**: Orchestrator pauses at `WAITING_APPROVAL`. The test script must manually inject `resume_from_approval(True)`.
  - **Execution**: Folder and file are created.
  - **Verification**: Verifier confirms file existence and content.

### Test Case 3: Autonomous Replanning (Failure Handling)
- **Prompt**: *"Read the file 'does_not_exist_12345.txt'."*
- **Expected Behavior**:
  - **Execution**: `filesystem.read_file` fails due to `FileNotFound`.
  - **Recovery Engine**: Identifies failure, decides to `REPLAN`.
  - **Replanning**: `LLMPlanner` receives the truncated error context and attempts to generate a fallback DAG (e.g. searching for the file or safely returning an error action).
  - **Termination**: If replans exceed `max_replans` (2), orchestrator safely transitions to `FAILED`.

## 5. Safety Constraints
- All validation tests must use safe, non-destructive filesystem operations (e.g., creating temporary test folders, reading system info). 
- Do NOT test `filesystem.delete` or raw `terminal.execute` commands during this phase to avoid accidental system modification.
- The `PolicyEngine` must NOT be weakened. Do not bypass the `RiskLevel.LEVEL_2_MODIFY` approval requirement; simulate the human approval via code in the test harness instead.

## 6. Execution Commands
Create a dedicated python script `scripts/validate_real_llm.py` that sets up the Orchestrator with the real LLM dependencies.

To run the validation:
```powershell
$env:PYTHONPATH="."
.venv\Scripts\python scripts/validate_real_llm.py
```

## 7. Readiness
Stage 3 is **READY TO EXECUTE** pending user approval. No blocking implementation bugs were discovered in the Phase 1-13 + Stage 2 architecture.
