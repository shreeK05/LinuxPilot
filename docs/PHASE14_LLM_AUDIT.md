# Phase 14 LLM Integration Audit

## 1. Current LLM Architecture
The current architecture effectively wraps the LLM interactions within robust boundaries utilizing Pydantic for structured validation. 
- **GoalInterpreter (`LLMGoalInterpreter`)**: Parses raw natural language inputs into a highly structured `GoalUnderstanding` object.
- **Planner (`LLMPlanner`)**: Maps the structured goal into a Directed Acyclic Graph (DAG) of `PlanStep` elements using `ActionDefinition` objects (registered handlers only).
- **Verifier (`LLMSemanticVerifier`)**: Semantically verifies outputs against expected states dynamically.
- **Orchestrator**: Ties these LLM-driven components together with deterministic loops (e.g. up to 3 bounded retries during planning, and up to `max_replans=2` for dynamic execution failure replanning loops).

## 2. Supported Providers
The `LLMProvider` interface abstracts interactions. 
The primary implementation is `OpenAICompatibleProvider`, which leverages the official OpenAI Python SDK (`client.beta.chat.completions.parse`). Because of this design, it is inherently compatible out-of-the-box with any OpenAI-compatible API, specifically including:
- OpenAI (GPT-4o, GPT-4o-mini)
- Groq
- Ollama (Local)

There is also a `MockProvider` used for deterministic fallback and local testing.

## 3. Required Environment Variables
The application configures the LLM provider through `.env`:
- `LLM_PROVIDER`: Either `mock`, `openai`, `groq`, or `ollama`.
- `LLM_BASE_URL`: Defines the provider's API endpoint (defaults to `https://api.openai.com/v1`).
- `LLM_API_KEY`: API authentication key.
- `LLM_MODEL`: Which model string to invoke (e.g. `gpt-4o-mini`).

## 4. How a user request reaches the LLM
1. The user submits a natural-language request via the Chat UI to the API.
2. The `AgentOrchestrator` triggers the `UNDERSTANDING` state.
3. The `LLMGoalInterpreter` formulates a strict `system_prompt` and sends the `raw_goal` to the LLM via `LLMProvider.generate_structured()`.

## 5. How structured output is validated
The `OpenAICompatibleProvider` uses the `beta.chat.completions.parse` function of the OpenAI SDK. It passes the specific Pydantic models (e.g., `GoalUnderstanding`, `LLMPlanResponse`, `LLMVerificationResponse`) directly as the `response_format`. The SDK and the OpenAI API guarantee that the output matches the exact JSON schema required by the application.

## 6. How the generated plan reaches the Policy Engine
The `LLMPlanner` constructs standard `PlanStep` objects representing the LLM's plan, applies topological sorting for DAG resolution, and hands the `ExecutionPlan` to the `AgentOrchestrator`.
The Orchestrator then enters the `POLICY_CHECK` state, iterating over each `PlanStep.action` and deterministically evaluating it with the `PolicyEngine` to determine if any action is `BLOCK`, `REQUIRE_APPROVAL`, or `REQUIRE_SNAPSHOT`.

## 7. How actions are executed
If approved (or no approval required), the Orchestrator safely interpolates parameters using deterministic regex matching from past step outputs, then delegates the raw action execution payload to the `ExecutionEngine`. The LLM has **no direct path** to shell execution; it only constructs schemas for known handlers.

## 8. How verification happens
After execution, the output is passed back to the `Verifier`. If the action lacks semantic requirements, it uses `DeterministicVerifier`. Otherwise, it uses `LLMSemanticVerifier`, sending the expected state and actual output back to the LLM Provider to semantically determine `success`, `diff`, and any `recovery_suggestion`.

## 9. Current mock/deterministic fallback behavior
If `LLM_PROVIDER=mock`, the system routes to `MockProvider`. It bypasses network calls entirely, directly validating predefined dictionary payloads against the requested Pydantic models. `DeterministicPlanner` and `DeterministicGoalInterpreter` exist for older tests mapped strictly to manual test behaviors (e.g. "Create Test Folder").

## 10. Missing reliability features
- **Timeout & Retries**: `OpenAICompatibleProvider` currently lacks resilience for `httpx` timeouts, `HTTP 429` (Rate Limits), or `5xx` transient failures (no exponential backoff library like `tenacity`).
- **Context/Output Bounds**: There are no protections in place against excessively large execution outputs (e.g. `cat massive_file.log`). The `LLMSemanticVerifier` and `replan` loops will naively append this to the LLM context, which will throw a context window error.
- **Circuit Breakers**: If the LLM provider fails globally, the system attempts to retry 3 times in quick succession in the orchestrator before crashing hard without a graceful user fallback.
- **Token Usage Enforcement**: No hard bounds on context payload size before calling the model.

## 11. Risks discovered
- **Infinite Replanning / Token Bleed**: Although bounded to `max_replans=2`, large failure traces concatenated with the full `executed_steps` history could rapidly bleed tokens or hit max-context bounds.
- **Provider Outages**: Without exponential backoff on `HTTP 429` (Rate limits), tests or intensive tasks on free-tier APIs (like Groq) will crash the orchestrator immediately.
- **Structured Parsing Limits**: If the LLM persistently refuses (e.g. `response.choices[0].message.refusal`), the provider will just raise `LLMProviderError` and quickly exhaust the 3 Orchestrator retries, failing the task instead of generating an actionable user recovery message.

---

### Exact files that would need modification (Stage 2)
1. `apps/api/app/agent/llm/provider.py`: Add `tenacity` retry decorators to `generate_structured` for `RateLimitError` and `Timeout`.
2. `apps/api/app/agent/verifier.py`: Truncate excessively long `output` strings before sending them to the `LLMSemanticVerifier` prompt.
3. `apps/api/app/agent/planner.py`: Truncate the `error` string length inside `replan` to prevent context bloat.

### Proposed Implementation Order (Stage 2)
1. Add `tenacity` dependency to `apps/api/requirements.txt`.
2. Update `apps/api/app/agent/llm/provider.py` to handle transient network errors safely using exponential backoff.
3. Introduce text truncation utilities inside `verifier.py` and `planner.py` to cap prompt injection sizes to a reasonable token limit (e.g. 5,000 characters).
4. Update `.env.example` with standard timeout or token limit defaults.

### Tests Required (Stage 3)
- Unit tests mocking `openai.OpenAI` that raise `RateLimitError` to verify `tenacity` backoff works.
- Unit tests passing enormous strings to `LLMSemanticVerifier` to ensure truncation bounds are enforced without breaking the verification attempt.
- Unit test ensuring `LLMProviderError` cleanly bubbles up to the orchestrator to fail gracefully when the provider is fully unavailable.
