# LinuxPilot — High-End Production-Grade Project Blueprint
## Trust-First, Accessibility-Native, Autonomous Linux Desktop Agent
### Student Edition — Production Architecture with a Free/Open-Source-First Technology Policy

---

## 0. Document Purpose

This document upgrades the original LinuxPilot concept from a **3–4 workflow academic prototype** into a **high-end, production-style Linux desktop automation platform** while keeping the implementation realistic for a student team and enforcing a strict rule:

> **No paid infrastructure is required for the core project.**

The system should be capable of performing a broad range of Linux desktop tasks through a combination of:

- Natural-language goal understanding
- Task planning and replanning
- Accessibility-tree perception
- Screenshot/VLM perception fallback
- Browser automation
- Terminal/CLI automation
- File-system operations
- Application launching and control
- Structured document and spreadsheet processing
- Multi-step workflow orchestration
- Verification after every meaningful action
- Risk-aware execution
- Snapshots and rollback
- Sandboxing
- Full audit/replay
- Human approval gates
- Observability and evaluation

The original blueprint established the core idea: LinuxPilot should operate a real or VM-hosted Linux desktop, use AT-SPI2 as the primary perception mechanism, use a VLM as fallback, classify actions by risk, apply namespaces/cgroups/seccomp, snapshot destructive operations, verify state, and maintain an audit trail. fileciteturn0file0L25-L31

This version keeps those principles but expands the system into a **platform rather than a single demo workflow**.

---

# 1. Executive Vision

## 1.1 Product Definition

**LinuxPilot** is an autonomous Linux desktop agent that accepts a natural-language objective such as:

> "Organize my Downloads folder, extract the important information from the invoices, create a spreadsheet, and open it for review."

LinuxPilot converts that objective into an executable workflow.

The agent can:

1. Understand the user's goal.
2. Inspect the current Linux environment.
3. Discover relevant applications, files, windows, and UI elements.
4. Build a structured execution plan.
5. Break the plan into atomic actions.
6. Assign risk levels to actions.
7. Request approval where required.
8. Execute actions through safe adapters.
9. Observe the resulting OS state.
10. Verify whether the expected state was achieved.
11. Retry or replan when an action fails.
12. Roll back reversible/destructive changes when policy permits.
13. Produce a complete execution report.
14. Replay the run for debugging and evaluation.

The key product principle is:

> **LinuxPilot should not merely "do things"; it should know what it intended to do, what it actually did, whether it worked, and what changed.**

---

# 2. Project Goals

## 2.1 Primary Goals

### Goal A — Broad task execution

Move from four hard-coded workflows to a reusable set of action primitives.

The agent should support categories such as:

- File management
- Folder management
- Application control
- Browser automation
- Web form interaction
- Terminal commands
- Text editing
- Document processing
- PDF extraction
- Spreadsheet creation/editing
- CSV processing
- Data transformation
- Screenshot and screen inspection
- UI navigation
- Search and information extraction
- Batch operations
- Cross-application workflows
- Repetitive administrative tasks

### Goal B — High reliability

Every important action follows:

**Observe → Plan → Act → Observe → Verify → Continue / Retry / Replan / Rollback**

### Goal C — Trust and safety

The system must distinguish:

- Read-only
- Low-risk
- Reversible
- Potentially destructive
- High-impact
- Irreversible

The original design already requires risk classification and mandatory snapshots for destructive operations. fileciteturn0file0L114-L124

### Goal D — Production-style architecture

The implementation should resemble a real product:

- Modular services
- Typed contracts
- REST/WebSocket APIs
- Persistent database
- Job execution engine
- Event bus
- Authentication
- RBAC-ready architecture
- Structured logs
- Metrics
- Traces
- Health checks
- Configuration management
- Automated tests
- CI/CD
- Versioned APIs
- Migration strategy
- Recovery strategy

### Goal E — Student-friendly cost

The core system should run on:

- Student laptop/desktop
- Local Linux VM
- Local Docker environment
- Free/open-source software
- Optional free API quotas

No paid cloud dependency should be required for the demonstration.

---

# 3. What Makes LinuxPilot High-End?

The original project differentiated itself around Linux-native computer use and verifiable safety. fileciteturn0file0L8-L10

The upgraded system adds seven major layers:

1. **Universal action engine**
2. **Multi-modal perception**
3. **Hierarchical planning**
4. **Autonomous recovery**
5. **Security policy engine**
6. **Observability and replay**
7. **Professional control dashboard**

This transforms LinuxPilot from:

> "An AI that performs four demonstrations"

into:

> "A general-purpose, safety-first Linux computer-use platform with controlled autonomous execution."

---

# 4. Product Scope

## 4.1 Supported Environment

Primary:

- Ubuntu/Debian-based Linux
- XFCE or another accessibility-friendly desktop
- X11 for the initial implementation

Secondary/stretch:

- Wayland compatibility
- GNOME
- KDE

The original blueprint recommends a lightweight Linux desktop such as XFCE for AT-SPI stability. fileciteturn0file0L161-L172

---

# 5. Capability Matrix

| Capability | Core | Advanced | Stretch |
|---|---:|---:|---:|
| Natural-language commands | ✓ | | |
| File management | ✓ | ✓ | |
| Terminal automation | ✓ | ✓ | |
| Browser automation | ✓ | ✓ | |
| Accessibility perception | ✓ | ✓ | |
| Screenshot perception | ✓ | ✓ | |
| VLM grounding | | ✓ | ✓ |
| PDF processing | ✓ | ✓ | |
| Spreadsheet automation | ✓ | ✓ | |
| Cross-application workflows | | ✓ | ✓ |
| Automatic retry | ✓ | ✓ | |
| Automatic replanning | | ✓ | ✓ |
| Rollback | ✓ | ✓ | |
| Snapshot history | ✓ | ✓ | |
| Syscall auditing | | ✓ | |
| Policy engine | ✓ | ✓ | |
| Human approval gates | ✓ | ✓ | |
| Execution replay | | ✓ | ✓ |
| Task templates | ✓ | ✓ | |
| Scheduling | | ✓ | ✓ |
| Workflow memory | | ✓ | ✓ |
| Voice input | | | ✓ |
| Remote Linux execution | | | ✓ |
| Multi-agent execution | | | ✓ |

---

# 6. High-Level Architecture

```text
                         ┌──────────────────────────┐
                         │        USER / ADMIN       │
                         │ Web UI / CLI / Voice      │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │       API GATEWAY         │
                         │ REST + WebSocket + Auth   │
                         └────────────┬─────────────┘
                                      │
                    ┌─────────────────┴──────────────────┐
                    ▼                                    ▼
          ┌───────────────────┐                ┌───────────────────┐
          │ Task Manager      │                │ Control Dashboard │
          │ Jobs / History    │                │ Logs / Metrics    │
          └─────────┬─────────┘                └───────────────────┘
                    │
                    ▼
          ┌────────────────────────────┐
          │     ORCHESTRATION ENGINE   │
          │                            │
          │ Goal → Plan → Execute      │
          │ Retry → Replan → Complete  │
          └─────────────┬──────────────┘
                        │
       ┌────────────────┼─────────────────┐
       ▼                ▼                 ▼
┌──────────────┐ ┌───────────────┐ ┌───────────────┐
│ Goal Parser  │ │ Planner       │ │ Policy Engine │
│ Intent       │ │ DAG / State   │ │ Risk / Auth   │
└──────────────┘ └───────────────┘ └───────────────┘
       │                │                 │
       └────────────────┼─────────────────┘
                        ▼
              ┌────────────────────┐
              │ PERCEPTION ENGINE  │
              │                    │
              │ AT-SPI             │
              │ Screenshot         │
              │ OCR                │
              │ VLM                │
              │ File/OS state      │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │ ACTION ROUTER      │
              │                    │
              │ UI / Browser       │
              │ Terminal           │
              │ File System        │
              │ App APIs           │
              │ Keyboard/Mouse     │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │ SAFETY RUNTIME     │
              │                    │
              │ Sandbox            │
              │ Namespaces         │
              │ cgroups            │
              │ seccomp            │
              │ Snapshot           │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │ LINUX DESKTOP      │
              │                    │
              │ Browser            │
              │ Terminal           │
              │ Files              │
              │ Applications       │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │ VERIFICATION       │
              │                    │
              │ Expected vs Actual │
              │ State Diff         │
              │ Confidence         │
              └─────────┬──────────┘
                        │
                 success / failure
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
        Continue                Recover
                                  │
                         retry / replan /
                           rollback
                                  │
                                  ▼
                           AUDIT STORE
```

---

# 7. Architecture Principles

## 7.1 Local-first

The system should work without a cloud backend.

Recommended:

- Local LLM through Ollama-compatible runtime
- Local VLM where hardware allows
- Local PostgreSQL or SQLite
- Local Redis-compatible queue if required
- Local Prometheus
- Local Grafana
- Local object storage directory

Cloud APIs should be optional adapters.

## 7.2 Provider abstraction

Never hard-code one LLM.

Create:

```text
LLMProvider
 ├── LocalProvider
 ├── GroqProvider
 ├── OpenAICompatibleProvider
 └── MockProvider
```

The application talks to an interface rather than directly to a model.

## 7.3 Action abstraction

Every operation becomes an action:

```text
Action
 ├── FileAction
 ├── TerminalAction
 ├── BrowserAction
 ├── UIAction
 ├── DocumentAction
 ├── SpreadsheetAction
 └── ApplicationAction
```

This makes the project extensible.

## 7.4 Verification-first

The executor should never assume that a command worked.

Example:

```text
Plan:
Move report.pdf → Documents/Reports/

Execute:
move()

Verify:
Does destination exist?
Does source no longer exist?
Did file metadata remain valid?

Result:
SUCCESS
```

---

# 8. Major System Modules

## 8.1 User Interface

Build a professional web dashboard.

### Main screens

1. Dashboard
2. New Task
3. Live Execution
4. Plan Viewer
5. Approval Center
6. Execution History
7. Run Details
8. File Changes
9. Rollback Center
10. System Monitor
11. Policy Manager
12. Settings
13. Workflow Templates
14. Agent Memory
15. Developer/Debug Console

### Live execution view

Show:

```text
Task:
Organize Downloads

Status:
RUNNING

Progress:
██████████████░░░░ 72%

Current step:
Classifying invoice files

Agent reasoning summary:
Found 23 files.
18 are documents.
5 are images.

Current action:
Create Documents/Invoices

Safety:
REVERSIBLE

Verification:
PASSED
```

Do not expose hidden chain-of-thought. Display concise, user-safe action explanations and structured execution state instead.

---

# 9. Goal Understanding Engine

Input:

> "Clean my Downloads folder, move PDFs into documents, rename invoices using their dates, and create a spreadsheet of all invoices."

Convert to:

```json
{
  "objective": "Organize and summarize Downloads",
  "constraints": [],
  "entities": ["Downloads", "PDF", "invoice"],
  "operations": [
    "inspect",
    "classify",
    "create_folder",
    "move",
    "extract",
    "rename",
    "create_spreadsheet"
  ]
}
```

The parser should identify:

- Intent
- Entities
- Constraints
- Preconditions
- Expected outputs
- Risk
- Required permissions
- Potentially destructive steps

---

# 10. Planning Engine

## 10.1 Hierarchical planning

Instead of one giant LLM prompt:

```text
Goal
 ↓
High-level plan
 ↓
Subtasks
 ↓
Atomic actions
 ↓
Execution
```

Example:

```text
Goal:
Prepare monthly invoice report

Task 1:
Find invoice files

Task 2:
Extract invoice metadata

Task 3:
Normalize data

Task 4:
Create spreadsheet

Task 5:
Save spreadsheet

Task 6:
Verify output

Task 7:
Open result for user
```

## 10.2 DAG execution

The planner creates dependencies.

```text
Find PDFs
    │
    ├── Extract metadata
    │        │
    │        ▼
    │    Normalize data
    │        │
    │        ▼
    │    Create XLSX
    │
    └── Generate audit summary
```

Independent operations can execute in parallel when safe.

---

# 11. Perception Engine

The original blueprint specifies AT-SPI2 as primary perception with VLM fallback. fileciteturn0file0L67-L70

Upgrade this into a multimodal perception stack.

## 11.1 Perception hierarchy

Priority:

1. Direct application API
2. File-system state
3. AT-SPI
4. Browser DOM/accessibility
5. OCR
6. Screenshot analysis
7. VLM

Use the cheapest and most deterministic source first.

## 11.2 AT-SPI

Use for:

- Buttons
- Text fields
- Menus
- Windows
- Labels
- Roles
- States
- Focus
- Accessible names

## 11.3 Browser DOM

For supported browser workflows, prefer DOM selectors over visual clicking.

Possible adapter:

```text
Browser
 ├── Playwright
 ├── DOM inspection
 ├── Accessibility snapshot
 └── Screenshot fallback
```

## 11.4 OCR

Use local OCR for:

- Text extraction
- Screen labels
- Error messages
- Coordinates
- Verification

## 11.5 VLM

Use only when structured perception cannot solve the task.

Example:

```text
Screenshot
   ↓
VLM
   ↓
Detected UI elements
   ↓
Coordinates + semantic labels
   ↓
Action
```

---

# 12. Universal Action Engine

The project should not depend on one automation mechanism.

## 12.1 File actions

Support:

- List
- Search
- Copy
- Move
- Rename
- Delete
- Create
- Compress
- Extract
- Compare
- Hash
- Metadata inspection

## 12.2 Terminal actions

Support:

- Command execution
- Environment inspection
- Package operations inside sandbox
- Script execution
- Output capture
- Exit-code verification

Commands must pass through policy validation.

## 12.3 UI actions

Support:

- Click
- Double click
- Type
- Key press
- Hotkey
- Scroll
- Drag
- Select
- Focus
- Wait

## 12.4 Browser actions

Support:

- Navigate
- Search
- Click
- Type
- Select
- Extract
- Download
- Upload
- Submit
- Verify

## 12.5 Document actions

Support:

- PDF text extraction
- Table extraction
- Document creation
- Markdown conversion
- DOCX generation
- CSV generation
- XLSX generation

## 12.6 Application actions

Support:

- Open
- Close
- Focus
- Minimize
- Maximize
- Switch window
- Detect application state

---

# 13. Safety Policy Engine

The safety engine is a central component rather than an afterthought.

## 13.1 Risk levels

### LEVEL 0 — READ

Examples:

- List files
- Read text
- Inspect UI
- Check system information

No confirmation.

### LEVEL 1 — LOW RISK

Examples:

- Open application
- Create temporary file
- Search browser

Normally automatic.

### LEVEL 2 — REVERSIBLE

Examples:

- Move
- Rename
- Create directory
- Edit a recoverable document

Snapshot where appropriate.

### LEVEL 3 — HIGH IMPACT

Examples:

- Modify many files
- Submit forms
- Send messages
- Change system configuration

Require explicit approval depending on policy.

### LEVEL 4 — DESTRUCTIVE

Examples:

- Delete
- Overwrite
- Package/system configuration changes
- Permission changes

Mandatory confirmation + recovery strategy.

### LEVEL 5 — BLOCKED

Examples:

- Unsafe commands
- Attempts to escape the sandbox
- Unauthorized credential access
- Dangerous system modification

Hard block.

---

# 14. Human Approval System

A production-style agent must have a clear approval mechanism.

Example:

```text
LinuxPilot wants to perform:

DELETE 17 files

Location:
~/Downloads/Old

Risk:
HIGH

Recovery:
Snapshot available

[ Cancel ] [ Review Files ] [ Approve ]
```

Approval should support:

- One-time approval
- Approve current step
- Approve task
- Always allow safe operation
- Deny
- Cancel entire task

---

# 15. Sandbox Architecture

The original blueprint calls for namespaces, cgroups v2, seccomp-bpf, and overlayfs. fileciteturn0file0L73-L79

The upgraded system should use a layered model.

## Layer 1 — Process isolation

Use Linux namespaces where feasible:

- PID
- Mount
- Network
- User
- IPC

## Layer 2 — Resource isolation

Use cgroups:

- CPU
- Memory
- Process count
- I/O limits

## Layer 3 — Syscall policy

Use seccomp-bpf.

## Layer 4 — Filesystem isolation

Expose only required paths.

## Layer 5 — Snapshot

Before risky operations:

```text
Current State
     ↓
Snapshot
     ↓
Action
     ↓
Verification
     ↓
Commit / Rollback
```

---

# 16. Snapshot and Rollback Manager

The original design proposes overlayfs-based rollback. fileciteturn0file0L108-L109

The upgraded manager should maintain:

```text
Snapshot
 ├── ID
 ├── Task ID
 ├── Created At
 ├── Scope
 ├── Files
 ├── Hashes
 ├── Parent Snapshot
 ├── Status
 └── Rollback Status
```

### Snapshot states

```text
CREATED
ACTIVE
COMMITTED
ROLLED_BACK
EXPIRED
FAILED
```

### Rollback center

The UI should show:

```text
Run #1042
12:31 PM

Changes:
+ 3 folders
~ 17 renamed files
→ 23 moved files
- 0 deleted

[View Changes]
[Rollback]
[Keep Changes]
```

---

# 17. Verification Engine

Verification is one of the most important differentiators.

## 17.1 Verification types

### File verification

- Exists?
- Correct location?
- Correct hash?
- Correct size?
- Correct permissions?

### UI verification

- Element exists?
- Text changed?
- Window opened?
- Button state changed?

### Browser verification

- URL correct?
- DOM state correct?
- Submission result detected?

### Spreadsheet verification

- File exists?
- Workbook opens?
- Expected sheets exist?
- Row count correct?

### Command verification

- Exit code
- Expected output
- Side effects

---

# 18. Recovery Engine

If verification fails:

```text
ACTION FAILED
     ↓
Retry?
     ↓
Yes → retry with adjusted parameters
     ↓
No
     ↓
Replan?
     ↓
Yes → rebuild remaining plan
     ↓
No
     ↓
Rollback?
     ↓
Yes → restore snapshot
     ↓
Ask user
```

The original blueprint explicitly defines mismatch handling through bounded retry or rollback. fileciteturn0file0L83-L86

---

# 19. Autonomous Replanning

Example:

The agent plans:

```text
Open LibreOffice
→ Create spreadsheet
```

But LibreOffice is not installed.

Instead of failing:

```text
Detect missing application
       ↓
Search installed alternatives
       ↓
Use compatible spreadsheet application
       ↓
Continue
```

Or:

```text
Browser page changed
       ↓
Original selector failed
       ↓
Inspect current accessibility/DOM state
       ↓
Find semantic equivalent
       ↓
Continue
```

---

# 20. Workflow Memory

LinuxPilot can maintain non-sensitive task metadata:

```text
Previous task:
"Organize Downloads"

Observed preference:
Use Documents/Invoices for invoice PDFs.

Next time:
Reuse the known destination.
```

Memory must be:

- User-visible
- Editable
- Deletable
- Scoped
- Auditable

Do not silently store credentials or sensitive content.

---

# 21. Workflow Templates

Provide reusable templates.

Examples:

### File organization

```text
Organize Downloads
```

### PDF processing

```text
Extract invoices from PDFs
```

### Spreadsheet

```text
Create monthly expense report
```

### Browser

```text
Process rows from CSV through web form
```

### Development

```text
Run project tests and summarize failures
```

### System administration

```text
Check disk usage and identify large directories
```

Templates are not hard-coded workflows. They are reusable planning hints.

---

# 22. Scheduler

Add a local task scheduler.

Examples:

```text
Every Monday:
Check Downloads for unorganized files.

Every evening:
Generate development workspace report.

At 8 AM:
Run system health check.
```

The scheduler should use the same safety engine as interactive tasks.

---

# 23. Task Queue

Use a persistent task state machine.

```text
CREATED
   ↓
QUEUED
   ↓
PLANNING
   ↓
WAITING_APPROVAL
   ↓
EXECUTING
   ↓
VERIFYING
   ↓
COMPLETED
```

Failure paths:

```text
EXECUTING
   ↓
FAILED
   ├── RETRYING
   ├── REPLANNING
   ├── ROLLING_BACK
   └── CANCELLED
```

---

# 24. Database Design

Use PostgreSQL for the production-style architecture, with SQLite as a lightweight development option.

## Main entities

### User

```text
id
username
created_at
settings
```

### Task

```text
id
user_id
goal
status
risk_level
created_at
started_at
completed_at
```

### Plan

```text
id
task_id
version
status
created_at
```

### PlanStep

```text
id
plan_id
sequence
action_type
parameters
risk_level
status
```

### Execution

```text
id
task_id
worker_id
status
started_at
completed_at
```

### ActionExecution

```text
id
execution_id
step_id
input
output
status
latency
```

### Verification

```text
id
action_execution_id
expected_state
actual_state
result
confidence
```

### Snapshot

```text
id
task_id
scope
path
status
created_at
```

### AuditEvent

```text
id
task_id
timestamp
event_type
actor
payload
```

### Approval

```text
id
task_id
step_id
decision
approved_by
timestamp
```

---

# 25. API Design

Base:

```text
/api/v1
```

## Tasks

```http
POST   /tasks
GET    /tasks
GET    /tasks/{id}
POST   /tasks/{id}/cancel
POST   /tasks/{id}/retry
POST   /tasks/{id}/rollback
```

## Planning

```http
POST   /tasks/{id}/plan
GET    /tasks/{id}/plan
POST   /tasks/{id}/replan
```

## Approval

```http
GET    /approvals
POST   /approvals/{id}/approve
POST   /approvals/{id}/deny
```

## Snapshots

```http
GET    /snapshots
GET    /snapshots/{id}
POST   /snapshots/{id}/rollback
```

## Audit

```http
GET    /tasks/{id}/audit
GET    /tasks/{id}/events
```

## System

```http
GET /health
GET /ready
GET /metrics
GET /version
```

---

# 26. Real-Time Communication

Use WebSockets for:

- Live task progress
- Current action
- Approval requests
- Logs
- Verification status
- Agent state
- Errors

Example:

```json
{
  "event": "ACTION_COMPLETED",
  "task_id": "task_1042",
  "step_id": "step_12",
  "status": "SUCCESS"
}
```

---

# 27. Event-Driven Architecture

Events:

```text
TASK_CREATED
PLAN_CREATED
STEP_STARTED
APPROVAL_REQUIRED
ACTION_STARTED
ACTION_COMPLETED
VERIFICATION_STARTED
VERIFICATION_PASSED
VERIFICATION_FAILED
RETRY_STARTED
REPLAN_STARTED
SNAPSHOT_CREATED
ROLLBACK_STARTED
ROLLBACK_COMPLETED
TASK_COMPLETED
TASK_FAILED
```

This makes the system easier to monitor and replay.

---

# 28. Observability

The project should have a professional observability layer.

## Metrics

Track:

- Tasks completed
- Tasks failed
- Success rate
- Average task duration
- Step latency
- Retry count
- Replan count
- Rollback count
- Approval wait time
- VLM usage
- LLM latency
- Sandbox violations
- Verification failures

The original project already defines task success, verification accuracy, rollback correctness, sandbox violations, and latency as evaluation metrics. fileciteturn0file0L137-L142

## Dashboard

Recommended:

```text
Prometheus
    ↓
Grafana
```

Both can run locally.

---

# 29. Structured Logging

Every event should contain:

```json
{
  "timestamp": "...",
  "task_id": "...",
  "run_id": "...",
  "step_id": "...",
  "component": "executor",
  "event": "ACTION_COMPLETED",
  "action": "MOVE_FILE",
  "status": "SUCCESS",
  "latency_ms": 182
}
```

Logs should never contain secrets.

---

# 30. Replay Engine

A powerful feature for the final demonstration.

User can select:

```text
Run #1024
```

and view:

```text
Goal
 ↓
Plan v1
 ↓
Step 1
 ↓
Observation
 ↓
Action
 ↓
Verification
 ↓
Step 2
 ↓
Failure
 ↓
Replan v2
 ↓
Success
```

This turns debugging into a visible product feature.

---

# 31. Professional Dashboard

## Dashboard widgets

### Active tasks

```text
3 Running
1 Waiting Approval
12 Completed
```

### Success rate

```text
94.2%
```

### Safety

```text
0 Sandbox Escapes
2 Rollbacks
7 Approval Gates
```

### Performance

```text
Avg step latency: 420 ms
Avg task duration: 21.4 s
```

### Recent activity

```text
10:32  Task completed
10:31  Verification passed
10:31  File moved
10:30  Snapshot created
```

---

# 32. Authentication and Authorization

Even for a student project, design the system as if multiple users could exist.

## Roles

```text
ADMIN
USER
VIEWER
```

Permissions:

```text
task:create
task:execute
task:cancel
task:rollback
audit:view
policy:modify
system:view
```

For the local student demo, authentication can remain optional or use a simple local login.

---

# 33. Secrets Management

Never give the LLM direct access to:

```text
.env
SSH private keys
browser cookies
password stores
API keys
```

Use:

- Environment variables
- OS keyring where appropriate
- Redaction middleware
- Secret detection
- Allowlisted environment variables

---

# 34. Security Boundaries

The system should enforce:

```text
LLM
 ↓
Planner
 ↓
Policy Engine
 ↓
Executor
```

The LLM must never directly execute an arbitrary shell command.

Instead:

```text
LLM:
"delete file"

Planner:
DELETE_FILE

Policy:
HIGH RISK → approval required

Executor:
approved_delete(file_id)
```

This is one of the most important architecture rules.

---

# 35. Plugin / Adapter Architecture

Make capabilities pluggable.

```text
plugins/
 ├── browser/
 ├── filesystem/
 ├── terminal/
 ├── pdf/
 ├── spreadsheet/
 ├── desktop/
 └── applications/
```

Every plugin exposes:

```text
name
description
input_schema
risk_level
execute()
verify()
rollback()
```

This makes adding new capabilities straightforward.

---

# 36. Example Universal Task

User:

> "Find all PDF invoices in Downloads, extract invoice number, date, vendor and amount, create an Excel report, move the processed PDFs into an archive folder, and show me the report."

LinuxPilot:

### Step 1
Inspect Downloads.

### Step 2
Find PDFs.

### Step 3
Classify likely invoices.

### Step 4
Create snapshot.

### Step 5
Extract invoice information.

### Step 6
Validate extracted values.

### Step 7
Create spreadsheet.

### Step 8
Verify spreadsheet.

### Step 9
Create archive directory.

### Step 10
Move processed PDFs.

### Step 11
Verify source/destination state.

### Step 12
Open spreadsheet.

### Step 13
Present execution summary.

---

# 37. Example Failure Recovery

Suppose the browser's submit button moves.

Original:

```text
Click coordinates 920,740
```

Fails verification.

LinuxPilot:

```text
Verification failed
      ↓
Capture new state
      ↓
Inspect DOM / AT-SPI
      ↓
Find semantic "Submit" button
      ↓
Execute
      ↓
Verify
```

If still unsuccessful:

```text
Retry limit reached
      ↓
Replan
```

If state was modified:

```text
Rollback available
      ↓
Restore
      ↓
Notify user
```

---

# 38. Example Terminal Workflow

User:

> "Check why my project is not building and fix the issue."

Safe behavior:

1. Inspect project.
2. Detect build system.
3. Read configuration.
4. Run build in controlled environment.
5. Capture error.
6. Identify candidate cause.
7. Propose change.
8. Ask for approval before modifying source if policy requires it.
9. Apply patch.
10. Run tests.
11. Verify build.
12. Show changed files.
13. Offer rollback.

The agent should not silently rewrite an entire project.

---

# 39. Example Developer Workflow

User:

> "Run my tests, find failures, fix obvious issues, and run the tests again."

Possible plan:

```text
Detect repository
→ Detect language
→ Install/use existing environment
→ Run tests
→ Parse failures
→ Group failures
→ Inspect relevant source
→ Generate candidate patch
→ Approval
→ Apply patch
→ Run targeted tests
→ Run full tests
→ Report
```

This significantly increases the practical scope of the project.

---

# 40. Example Browser Workflow

User:

> "Take the rows from this CSV and fill the website form."

Pipeline:

```text
CSV
 ↓
Validate schema
 ↓
Open browser
 ↓
Navigate
 ↓
Inspect page
 ↓
Map CSV columns to form fields
 ↓
Fill
 ↓
Verify
 ↓
Submit
 ↓
Capture confirmation
 ↓
Move to next row
```

The system should stop when the website structure changes rather than blindly clicking.

---

# 41. Example System Administration Workflow

User:

> "Check my system for large files and show me what can be cleaned."

The agent should:

- Inspect disk
- Identify large files
- Group by directory
- Identify caches
- Never delete automatically
- Produce recommendations
- Ask before cleanup

This demonstrates safety.

---

# 42. Free/Open-Source Technology Stack

## Frontend

Recommended:

- React
- Vite
- TypeScript
- Tailwind CSS or plain CSS
- Recharts/Chart.js if needed

## Backend

Recommended:

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

Python is especially suitable because the OS, automation, AI, and document ecosystem is strong.

## Agent orchestration

Use:

- LangGraph if useful
- Otherwise a custom state-machine/DAG engine

Do not make the project dependent on a framework for basic execution.

## LLM

Primary:

- Local Ollama-compatible model

Optional:

- OpenAI-compatible providers
- Free API quota providers when available

The provider must be replaceable.

## VLM

Optional/local:

- Qwen-VL family or another locally runnable vision-language model

Fallback only.

## Desktop perception

- pyatspi
- AT-SPI2
- Python X11 bindings
- OCR

## Browser

- Playwright

## Input automation

- PyAutoGUI
- xdotool where appropriate

## OS security

- Linux namespaces
- cgroups v2
- seccomp
- overlayfs

## Database

- PostgreSQL
- SQLite for development

## Cache/queue

- Redis-compatible local server, or a database-backed queue for the first version

## Observability

- Prometheus
- Grafana
- OpenTelemetry where practical

## Packaging

- Docker/Podman for supporting services
- Linux VM for the desktop agent

## CI/CD

- GitHub Actions free tier for the public/student repository

---

# 43. Free-Tier Policy

## Rule 1

No paid cloud service should be required for core functionality.

## Rule 2

Local execution is the default.

## Rule 3

Cloud AI providers are optional.

## Rule 4

Every external provider must have a local fallback.

## Rule 5

The project must still work if internet access is unavailable, except for explicitly web-dependent tasks.

---

# 44. Recommended Deployment

## Student Laptop

```text
Windows
  ↓
WSL2 / Linux VM
  ↓
Ubuntu + XFCE
  ↓
LinuxPilot
```

For the strongest OS demonstration, use a dedicated Linux VM.

## Production-style local stack

```text
LinuxPilot UI
    ↓
FastAPI
    ↓
Agent Engine
 ┌──┼──────────────┐
 ↓  ↓              ↓
DB Queue       Model Runtime
 ↓  ↓              ↓
Postgres       Local LLM/VLM
    ↓
Monitoring
Prometheus + Grafana
```

---

# 45. Docker Architecture

Use containers for backend services, not necessarily for the entire desktop.

```text
docker-compose.yml

services:
  api
  postgres
  redis
  prometheus
  grafana
```

The desktop executor can run in the Linux VM because GUI and accessibility integration are easier there.

---

# 46. Repository Structure

```text
linuxpilot/
│
├── apps/
│   ├── web/
│   ├── api/
│   └── worker/
│
├── agent/
│   ├── planner/
│   ├── executor/
│   ├── perception/
│   ├── verification/
│   ├── recovery/
│   ├── memory/
│   └── policy/
│
├── adapters/
│   ├── filesystem/
│   ├── terminal/
│   ├── browser/
│   ├── desktop/
│   ├── documents/
│   └── spreadsheets/
│
├── sandbox/
│   ├── namespaces/
│   ├── cgroups/
│   ├── seccomp/
│   └── snapshots/
│
├── database/
│   ├── models/
│   ├── migrations/
│   └── repositories/
│
├── observability/
│   ├── metrics/
│   ├── tracing/
│   └── dashboards/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   ├── workflow/
│   └── chaos/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── security/
│   ├── workflows/
│   └── evaluation/
│
├── scripts/
├── docker-compose.yml
├── Makefile
├── README.md
└── LICENSE
```

---

# 47. Testing Strategy

## 47.1 Unit tests

Test:

- Planner
- Policy engine
- Risk classifier
- Verifier
- Snapshot manager
- Action schemas

## 47.2 Integration tests

Test:

```text
API → Planner → Executor → Verification
```

## 47.3 End-to-end tests

Examples:

- Organize files
- Create spreadsheet
- Browser form
- Terminal task

## 47.4 Security tests

Attempt:

- Unauthorized file access
- Blocked syscalls
- Sandbox escape
- Path traversal
- Command injection
- Privilege escalation

## 47.5 Failure injection

Deliberately:

- Kill executor
- Change UI
- Delete target during execution
- Make command fail
- Corrupt output
- Simulate model failure

Then verify recovery.

---

# 48. Evaluation Framework

Create a benchmark suite.

Each task should define:

```text
Task ID
Goal
Initial State
Expected Final State
Allowed Actions
Forbidden Actions
Risk
Success Criteria
Rollback Criteria
```

Example:

```text
LP-FS-001

Goal:
Move all PDF files to Documents/PDF.

Initial:
10 PDFs in Downloads.

Expected:
10 PDFs in Documents/PDF.
0 PDFs remain in Downloads.

Success:
10/10 moved and verified.
```

---

# 49. Key Metrics

## Task Success Rate

```text
successful tasks / total tasks
```

## Step Success Rate

```text
successful steps / total steps
```

## Verification Accuracy

```text
correct verification decisions / total verification decisions
```

## Recovery Rate

```text
successfully recovered failures / total recoverable failures
```

## Rollback Correctness

```text
correctly restored states / rollback attempts
```

## Safety Violation Rate

```text
blocked unsafe attempts / total executions
```

## Average Latency

Measure:

```text
perception
planning
execution
verification
```

---

# 50. Reliability Target

For the student evaluation, define targets rather than claiming production guarantees.

Example targets:

```text
Simple deterministic tasks: >95% success
Moderate workflows: >85% success
Verification accuracy: >95%
Rollback test success: >95%
Unsafe-action blocking: 100% for tested policies
```

These are project targets, not externally validated production claims.

---

# 51. Agent State Machine

```text
IDLE
 ↓
UNDERSTANDING
 ↓
PLANNING
 ↓
POLICY_CHECK
 ↓
WAITING_APPROVAL
 ↓
EXECUTING
 ↓
OBSERVING
 ↓
VERIFYING
 ├── PASS → NEXT_STEP
 ├── FAIL → RETRY
 ├── FAIL → REPLAN
 └── FAIL → ROLLBACK
                    ↓
                 RECOVERED
                    ↓
                COMPLETED
```

---

# 52. Confidence Model

Each action can have:

```text
Perception confidence
Planning confidence
Execution confidence
Verification confidence
```

Example:

```text
Action:
Click "Submit"

Perception: 0.97
Planning:    0.94
Execution:   0.99
Verification:0.91
```

Do not use a single confidence number to override safety policy.

---

# 53. Deterministic vs AI Execution

Use AI where ambiguity exists.

Use deterministic code where certainty exists.

### Good AI usage

- Goal interpretation
- Classification
- Semantic mapping
- Recovery planning
- Content understanding

### Good deterministic usage

- File movement
- Hash calculation
- Database operations
- Snapshot creation
- Policy checks
- Verification
- Logging

This makes the system cheaper, safer and easier to debug.

---

# 54. Cost-Control Strategy

AI can become the expensive or unreliable part of an agent.

Therefore:

1. Use deterministic tools first.
2. Use structured state before screenshots.
3. Use OCR before VLM where sufficient.
4. Use small/local models for classification.
5. Use larger models only for difficult planning.
6. Cache repeated observations.
7. Avoid sending entire screenshots unnecessarily.
8. Keep prompts structured.
9. Store reusable workflow templates.
10. Provide mock providers for testing.

---

# 55. Offline Mode

LinuxPilot should support:

```text
OFFLINE MODE
```

Capabilities:

- Filesystem
- Terminal
- Desktop
- Local applications
- Local documents
- Local models
- Local database
- Local monitoring

Internet-dependent workflows should clearly show:

```text
NETWORK REQUIRED
```

---

# 56. Network Safety

Default:

```text
Network = restricted
```

A task that needs network access must explicitly request it.

Examples:

```text
Browser automation → allowed browser network
Terminal curl → policy check
Unknown executable → blocked
```

---

# 57. Audit Trail

The original blueprint requires an append-only, replayable audit trail covering plans, actions, syscall traces and verification results. fileciteturn0file0L89-L92

Upgrade it into an event timeline:

```text
14:20:01 TASK_CREATED
14:20:02 PLAN_CREATED
14:20:03 POLICY_APPROVED
14:20:03 SNAPSHOT_CREATED
14:20:04 STEP_STARTED
14:20:05 ACTION_EXECUTED
14:20:05 VERIFICATION_PASSED
14:20:06 STEP_STARTED
...
14:20:19 TASK_COMPLETED
```

---

# 58. Explainability

The system should explain actions in simple terms:

```text
I found 18 PDF files in Downloads.

I classified 12 as invoices.

I created:
Documents/Invoices/

I moved 12 files.

All 12 files were verified successfully.
```

This is preferable to exposing private internal reasoning.

---

# 59. User Control

The user should always be able to:

- Pause
- Resume
- Cancel
- Approve
- Deny
- Inspect
- Roll back
- Change policy
- View files affected
- Export audit log

---

# 60. Emergency Stop

Add a prominent:

```text
STOP AGENT
```

button.

Behavior:

1. Stop new actions.
2. Cancel pending operations.
3. Safely terminate executor.
4. Preserve audit logs.
5. Offer rollback if needed.

---

# 61. Resource Management

Protect the system from runaway tasks.

Limits:

```text
Max task runtime
Max actions/task
Max retries/step
Max memory
Max CPU
Max child processes
Max files modified
Max browser tabs
```

When exceeded:

```text
TASK PAUSED
RESOURCE LIMIT REACHED
```

---

# 62. Policy Configuration

Example:

```yaml
policies:
  delete:
    require_confirmation: true

  move:
    snapshot: true

  browser_submit:
    require_confirmation: true

  terminal:
    network: restricted

  system_files:
    access: denied
```

Users can configure safety without changing code.

---

# 63. Application Profiles

Maintain profiles for common applications.

Example:

```text
Firefox
LibreOffice
Thunar
XFCE Terminal
VS Code
```

Each profile may define:

- Accessibility hints
- Known UI patterns
- Safe actions
- Verification rules

---

# 64. Knowledge Base

A local knowledge base can contain:

- Tool descriptions
- Action schemas
- Application profiles
- Workflow templates
- Recovery strategies
- Safety policies

The agent retrieves only relevant information.

---

# 65. Model Routing

Use different models for different jobs.

```text
Goal classification
→ small model

Simple planning
→ small/medium model

Complex planning
→ stronger model

Vision
→ VLM

Extraction
→ deterministic parser first
```

This reduces latency and resource use.

---

# 66. Model Failure Handling

If the model is unavailable:

```text
LLM unavailable
     ↓
Try local fallback
     ↓
If unavailable
     ↓
Use deterministic workflows/templates
     ↓
If impossible
     ↓
Ask user
```

The system must fail safely rather than execute an unvalidated guess.

---

# 67. Data Privacy

Default:

```text
User files stay local.
Screenshots stay local.
Audit logs stay local.
```

If a cloud model is enabled:

- Clearly show provider
- Clearly show data-sharing status
- Allow disabling
- Redact sensitive data where possible

---

# 68. Deployment Modes

## Mode A — Developer

```text
Local Python
Local DB
Local model
```

## Mode B — Student Demo

```text
Linux VM
Docker Compose
Web UI
Local model/API
Prometheus
Grafana
```

## Mode C — Advanced

```text
Linux host
Dedicated executor
PostgreSQL
Worker
Local model server
Monitoring
```

---

# 69. CI/CD

GitHub Actions pipeline:

```text
Push
 ↓
Lint
 ↓
Type check
 ↓
Unit tests
 ↓
Security tests
 ↓
Build
 ↓
Integration tests
 ↓
Docker image build
```

Keep CI within free/public-repository allowances.

---

# 70. Documentation

The final repository should contain:

```text
README
Architecture
Installation
Quick Start
Configuration
Security Model
API Reference
Workflow Guide
Developer Guide
Testing Guide
Deployment Guide
Troubleshooting
Threat Model
Evaluation
Demo Guide
```

---

# 71. Demo Scenarios

## Demo 1 — Simple

> "Open the file manager and find all PDF files in Downloads."

Shows:

- Goal understanding
- Perception
- UI control
- Verification

## Demo 2 — File automation

> "Organize Downloads by file type."

Shows:

- Classification
- File actions
- Snapshot
- Verification

## Demo 3 — Document intelligence

> "Extract invoice information from PDFs and create an Excel report."

Shows:

- Document processing
- Structured extraction
- Spreadsheet creation
- Verification

## Demo 4 — Browser

> "Fill this web form from the CSV."

Shows:

- Browser automation
- Data mapping
- Approval
- Verification

## Demo 5 — Recovery

Intentionally break a step.

Shows:

- Detection
- Retry
- Replanning
- Recovery

## Demo 6 — Rollback

Force a destructive test.

Shows:

- Snapshot
- Approval
- Action
- Failure
- Rollback

## Demo 7 — Security

Attempt a prohibited command.

Shows:

```text
REQUEST
 ↓
POLICY ENGINE
 ↓
BLOCKED
 ↓
AUDIT LOG
```

---

# 72. What "Mostly All Tasks" Means

The project should not promise literally every possible computer task.

Instead, define a **general action vocabulary**.

If a task can be decomposed into:

```text
Observe
Find
Open
Read
Click
Type
Select
Run
Create
Move
Copy
Rename
Transform
Submit
Verify
Recover
```

then LinuxPilot should be able to attempt it.

This gives the project broad practical coverage without pretending that an AI agent can guarantee arbitrary desktop behavior.

---

# 73. Scope Boundary

Do not build:

- Fully autonomous unrestricted root agent
- Kernel modifications
- Production multi-tenant SaaS
- Fully autonomous financial actions
- Unrestricted credential access
- Unbounded internet automation
- Multi-device orchestration in the first release

These increase risk and development time without improving the academic demonstration proportionally.

---

# 74. Development Phases

## Phase 1 — Foundation

- Linux VM
- XFCE
- Python
- FastAPI
- React
- Database
- Basic CLI

## Phase 2 — Perception

- AT-SPI
- Screenshot
- OCR
- Window detection

## Phase 3 — Action Engine

- Files
- Terminal
- Desktop
- Browser

## Phase 4 — Planner

- Goal parser
- DAG
- Action schemas
- Risk classification

## Phase 5 — Verification

- Expected state
- Actual state
- Diff
- Retry

## Phase 6 — Safety

- Policy engine
- Approval
- Sandbox
- Resource limits

## Phase 7 — Snapshot

- Snapshot manager
- Rollback
- Change viewer

## Phase 8 — Recovery

- Retry
- Replan
- Recovery policies

## Phase 9 — Dashboard

- Live execution
- History
- Logs
- Approvals
- Rollback UI

## Phase 10 — Observability

- Prometheus
- Grafana
- Metrics
- Structured logs

## Phase 11 — Advanced workflows

- PDFs
- XLSX
- Browser
- Cross-application workflows

## Phase 12 — Hardening

- Security tests
- Failure injection
- Performance tests
- Documentation

---

# 75. Suggested 12-Week Schedule

| Week | Main Deliverable |
|---|---|
| 1 | Linux VM + architecture + repository |
| 2 | Backend + frontend foundation |
| 3 | AT-SPI perception |
| 4 | File/terminal/UI action engine |
| 5 | Browser + document adapters |
| 6 | Planner + DAG |
| 7 | Verification + retry |
| 8 | Policy + approval + sandbox |
| 9 | Snapshot + rollback |
| 10 | Dashboard + audit + metrics |
| 11 | End-to-end workflows + failure injection |
| 12 | Hardening + demo + report |

---

# 76. Minimum Viable Product

The MVP should include:

- Natural-language task input
- Planner
- AT-SPI
- File actions
- Terminal actions
- Browser actions
- Verification
- Risk classification
- Approval
- Snapshot
- Rollback
- Audit log
- Basic dashboard

---

# 77. High-End Target

The final showcase should include:

```text
Natural Language
       ↓
Goal Understanding
       ↓
Planner
       ↓
Risk Engine
       ↓
Approval
       ↓
Multimodal Perception
       ↓
Universal Action Engine
       ↓
Sandbox
       ↓
Snapshot
       ↓
Execution
       ↓
Verification
       ↓
Retry / Replan / Rollback
       ↓
Audit
       ↓
Dashboard
```

---

# 78. Final Product Positioning

LinuxPilot should be presented as:

> **A safety-first autonomous Linux desktop agent that combines multimodal computer use, deterministic system automation, verification, sandboxing, snapshot-based recovery, and complete execution observability.**

The academic value comes from combining:

### Artificial Intelligence

- LLM planning
- VLM perception
- semantic task understanding

### Operating Systems

- Processes
- Namespaces
- cgroups
- seccomp
- filesystems
- resource management
- isolation

### Software Engineering

- APIs
- database
- modular architecture
- testing
- CI/CD

### Cybersecurity

- least privilege
- sandboxing
- syscall restrictions
- audit trails
- policy enforcement

### Human-Computer Interaction

- accessibility tree
- UI automation
- approval flows
- explainable execution

---

# 79. Final Success Criteria

LinuxPilot is considered a successful project when it can reliably demonstrate:

1. A user gives a natural-language goal.
2. LinuxPilot generates a structured plan.
3. The system identifies the required applications/files/UI elements.
4. The policy engine determines risk.
5. The system requests approval when necessary.
6. The executor performs actions through controlled adapters.
7. The system verifies every important state transition.
8. Failed actions trigger bounded recovery.
9. Destructive/reversible actions can be restored when configured.
10. Every important event appears in the audit trail.
11. The dashboard displays live execution.
12. Metrics show system performance.
13. A reviewer can replay the execution.
14. Security tests demonstrate blocked unsafe operations.
15. At least 5–7 different real-world workflows can be demonstrated using the same underlying action engine.

---

# 80. Final Recommended Technology Stack

| Layer | Recommended Technology | Cost Model |
|---|---|---|
| OS | Ubuntu + XFCE | Free |
| Frontend | React + Vite + TypeScript | Free |
| Backend | Python + FastAPI | Free |
| Agent | Python | Free |
| Planner | Custom DAG / LangGraph | Free/open source |
| LLM | Local Ollama-compatible runtime | Free/local |
| Optional LLM | Free-quota API adapter | Optional |
| VLM | Local open model | Free/local |
| Accessibility | AT-SPI2 / pyatspi | Free |
| Browser | Playwright | Free |
| UI Automation | PyAutoGUI / xdotool | Free |
| OCR | Local OCR engine | Free |
| Database | PostgreSQL | Free |
| Cache | Redis-compatible local deployment | Free |
| Security | namespaces + cgroups + seccomp | Linux built-in/open |
| Snapshot | overlayfs | Linux |
| Monitoring | Prometheus | Free |
| Dashboard | Grafana | Free |
| Tracing | OpenTelemetry | Free |
| Containers | Docker/Podman | Free |
| CI/CD | GitHub Actions free/public allowance | Free tier |
| Version Control | GitHub | Free tier |

---

# 81. Final Architecture Rule

The single most important engineering rule is:

> **The LLM proposes; the policy engine decides; the executor acts; the verifier confirms; the recovery engine repairs; the audit system records.**

Never allow:

```text
LLM → arbitrary shell command → Linux
```

Prefer:

```text
LLM
 ↓
Structured Action
 ↓
Schema Validation
 ↓
Risk Classification
 ↓
Policy Check
 ↓
Approval if required
 ↓
Sandboxed Executor
 ↓
Verification
 ↓
Audit
```

This architecture preserves the original LinuxPilot vision while making the project substantially broader, safer, more professional, and more suitable for a major student project.

---

# 82. Final Project Statement

## LinuxPilot

**LinuxPilot is a trust-first, accessibility-native autonomous Linux desktop agent designed to execute broad natural-language computer tasks through a controlled perception–planning–execution–verification loop. It combines AI-based planning and visual understanding with deterministic operating-system automation, Linux kernel isolation, risk-aware policies, snapshot-based rollback, recovery, and complete observability.**

The project is intentionally designed to achieve **production-style engineering quality without requiring paid infrastructure**, making it realistic for a student team while still demonstrating advanced concepts from AI, operating systems, cybersecurity, software engineering, and human-computer interaction.

The final system should feel less like a classroom script and more like a **small, self-hosted Linux automation platform**.
