# LinuxPilot — A Trust-First OS Agent for Linux

> **"ACID for AI Desktop Agents"** — LinuxPilot may make mistakes, but no mistake ever reaches your real files. Every change is detected, sandboxed, reviewed, and committed only with your explicit approval.

<p align="center">
  <img src="docs/images/architecture.svg" alt="LinuxPilot Architecture" width="700">
</p>

[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Ubuntu 24.04](https://img.shields.io/badge/Ubuntu-24.04%20LTS-orange.svg)](https://ubuntu.com/download)

---

## What Is This?

LinuxPilot is an **AI desktop agent** that automates tasks on Ubuntu Linux using a unique **transactional architecture** borrowed from databases. Just like a database ensures your money transfer either completes fully or not at all, LinuxPilot ensures your files are either organized perfectly or left completely untouched.

### The Reliability Contract

```
LinuxPilot may make mistakes,
but no mistake is ever allowed to reach your real files,
and every mistake is detected, undone, and recorded.
```

### Key USP: ACID Semantics for Desktop Automation

| Property | Database | LinuxPilot |
|----------|----------|------------|
| **Atomicity** | Transaction commits fully or rolls back | `overlayfs` upper layer: discard → zero changes |
| **Consistency** | Constraints checked after each statement | Machine-checkable postconditions after each step |
| **Isolation** | Other transactions can't see uncommitted data | `cgroup v2` + `namespaces` + `seccomp-bpf` sandbox |
| **Durability** | WAL ensures crash recovery | Write-ahead journal with `fsync` before each commit |

---

## Features

- 🔒 **Transactional Workspace** — All changes happen in an `overlayfs` sandbox. Your real files are never touched until you explicitly commit.
- 🛡️ **Kernel-Enforced Isolation** — `cgroup v2` for resource limits, `namespaces` for process isolation, `seccomp-bpf` for syscall filtering.
- ✅ **Machine-Checkable Verification** — Every step has postconditions (file exists, count matches, cell value correct) verified automatically.
- 🔗 **Tamper-Evident Audit** — SHA-256 hash chain records every action. Flip one byte and the chain breaks.
- 🔄 **Automatic Recovery** — Failed steps trigger rollback to the last good checkpoint, then replan with error context.
- 📊 **Live Dashboard** — WebSocket-powered real-time view of step execution, diffs, and audit trail.
- 🤖 **Multi-LLM Support** — Works with Ollama (local), Groq, and Google Gemini.
- 🎯 **Action Ladder** — Prefers deterministic file ops (L0) over GUI automation (L4), escalating only when necessary.

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Build the desktop image
docker build -t linuxpilot-desktop .

# Run with required capabilities for overlayfs
docker run --cap-add SYS_ADMIN --cap-add SYS_PTRACE \
    --security-opt apparmor=unconfined \
    -p 6080:6080 -p 8000:8000 \
    linuxpilot-desktop

# Access:
#   Desktop:   http://localhost:6080    (noVNC)
#   API:       http://localhost:8000/api/v1
#   Dashboard: http://localhost:8000/dashboard
```

### Option 2: Direct Install (Ubuntu 24.04)

```bash
# One-liner install
curl -sL https://raw.githubusercontent.com/linuxpilot/linuxpilot/main/install.sh | bash

# Or manual install
git clone https://github.com/linuxpilot/linuxpilot.git
cd linuxpilot
bash install.sh

# Start daemon
source .venv/bin/activate
lp daemon

# In another terminal
lp run "Organize my Downloads folder by file type"
```

### Option 3: VM Setup

```bash
cd LinuxPilot
bash scripts/setup_vm.sh
source .venv/bin/activate
lp doctor    # Verify all components
lp daemon    # Start API server
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `lp doctor` | Run system diagnostics (kernel, cgroup, AT-SPI, LLMs) |
| `lp daemon` | Start the API daemon on port 8000 |
| `lp run "goal"` | Submit a natural language task |
| `lp run "goal" --mode gui` | Force GUI-only mode |
| `lp diff <task-id>` | Show changes (git diff for your desktop) |
| `lp commit <task-id>` | Commit changes to real files |
| `lp undo <task-id>` | Undo a committed task |
| `lp audit verify <task-id>` | Verify audit chain integrity |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         LinuxPilot                               │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │ CLI / API │───►│ Planner  │───►│ Policy   │───►│ Approval  │  │
│  │          │    │ (LLM)    │    │ Engine   │    │ Gate      │  │
│  └──────────┘    └──────────┘    └──────────┘    └─────┬─────┘  │
│                                                        │        │
│  ┌─────────────────────────────────────────────────────┴─────┐  │
│  │                    Orchestrator (FSM)                       │  │
│  │  INIT → PLAN → POLICY → READY → EXECUTE → VERIFY → REVIEW │  │
│  │                   ↑                           │              │  │
│  │                   └──── ROLLBACK ◄── FAIL ◄───┘              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │ Action Ladder │  │ Postcondition │  │ Invariant Checker    │  │
│  │ L0: fs.*     │  │ Verifier      │  │ I1: Real data intact │  │
│  │ L1: ui.invoke│  │ fs.exists     │  │ I2: No content lost  │  │
│  │ L2: ui.text  │  │ xlsx.cell     │  │ I3: Path confined    │  │
│  │ L3: ui.key   │  │ ui.element    │  │ I4: Resources OK     │  │
│  │ L4: ui.click │  │ http.record   │  │ I5: No seccomp viol. │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Trusted Computing Base                    │  │
│  │  overlayfs │ cgroup v2 │ seccomp-bpf │ namespaces │ WAL    │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Demo Workflows

| # | Workflow | Difficulty | Mode |
|---|----------|------------|------|
| W1 | Organize ~/Downloads by file type | Easy | API (fs tools) |
| W2 | Extract invoice data → Excel + rename PDFs | Medium | API + PDF |
| W3 | Fill web form from CSV | Medium | GUI (AT-SPI + xdotool) |
| W4 | Content-aware rename (photos by EXIF date) | Medium | API |
| W5 | Adversarial prompt injection resistance | Hard | Security |

### Run Testbed

```bash
# Generate test data
python -m linuxpilot.testbed.generators all ./testbed_data

# Run benchmarks
python -m linuxpilot.testbed.benchmark ./testbed_data ./results
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/health` | GET | Health check |
| `POST /api/v1/tasks/` | POST | Create task |
| `GET /api/v1/tasks/{id}` | GET | Get task status |
| `POST /api/v1/tasks/{id}/approve` | POST | Approve/reject |
| `GET /api/v1/tasks/{id}/diff` | GET | View changes |
| `POST /api/v1/tasks/{id}/commit` | POST | Commit to real data |
| `POST /api/v1/tasks/{id}/discard` | POST | Discard changes |
| `POST /api/v1/tasks/{id}/rollback` | POST | Manual rollback |
| `POST /api/v1/tasks/{id}/kill` | POST | Emergency stop |
| `GET /api/v1/tasks/{id}/audit` | GET | Audit log |
| `GET /api/v1/tasks/{id}/checkpoints` | GET | List checkpoints |
| `WS /api/v1/ws/tasks/{id}/events` | WS | Live events |
| `GET /metrics` | GET | Prometheus metrics |

---

## Project Structure

```
LinuxPilot/
├── src/linuxpilot/
│   ├── actions/          # L0-L5 action ladder
│   │   ├── ladder.py     # Action dispatcher
│   │   ├── fs_tools.py   # Filesystem operations
│   │   ├── ui_tools.py   # AT-SPI + xdotool GUI automation
│   │   └── keys.py       # Keyboard tools
│   ├── api/              # FastAPI server
│   │   ├── app.py        # Application factory
│   │   └── routes/       # REST + WebSocket endpoints
│   ├── audit/            # Tamper-evident hash chain
│   ├── llm/              # LLM gateway (Ollama/Groq/Gemini)
│   ├── orchestrator/     # FSM + task lifecycle
│   │   ├── orchestrator.py  # Main engine
│   │   ├── fsm.py        # State machine
│   │   └── janitor.py    # Resource cleanup
│   ├── perception/       # AT-SPI tree + compression
│   ├── planning/         # LLM planner + policy engine
│   ├── sandbox/          # cgroup + namespace + seccomp
│   ├── verify/           # Postconditions + invariants + wait
│   ├── workspace/        # overlayfs + checkpoints + WAL commit
│   ├── cli.py            # Command-line interface
│   ├── config.py         # Settings
│   └── models.py         # Pydantic schemas
├── tests/                # pytest test suite
├── testbed/              # Dataset generators + benchmarks
├── desktop/              # VNC/noVNC entrypoint
├── scripts/              # VM setup
├── Dockerfile            # Desktop container
├── install.sh            # One-shot Ubuntu installer
└── pyproject.toml        # Package config
```

---

## Development

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=linuxpilot --cov-report=html

# Lint
ruff check src/ tests/

# Type check
mypy src/linuxpilot/
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
