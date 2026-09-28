# LinuxPilot: Complete Project Understanding Document

This document serves as an in-depth technical manual for LinuxPilot. It details the internal architecture, the flow of data, security implementations, and deployment infrastructure. This is your ultimate reference for writing your project report and understanding the precise mechanics of what you have built.

---

## 1. Project Overview & Objectives

**LinuxPilot** is an autonomous, AI-driven system administration agent. While standard chatbots (like ChatGPT) can tell you *how* to perform a task on Linux, LinuxPilot actually *executes* the task on the local machine on your behalf. 

### Primary Objectives:
1. **Automation of Routine Tasks:** Perform file operations, system checks, and configurations via natural language.
2. **Guaranteed Safety:** Never allow an AI to arbitrarily break the system. All actions must be sandboxed and verified.
3. **Accountability:** Maintain an immutable audit trail of every action taken by the AI and every approval given by the user.

---

## 2. System Architecture

The project is built on a decoupled, modern three-tier architecture:

### A. The Presentation Layer (Frontend)
* **Technology:** React.js, TypeScript, Vite, TailwindCSS (Custom Design System).
* **Role:** Provides a terminal-inspired, yet modern GUI. It handles user authentication (JWT), real-time task polling, and provides the "Approval Center" where humans review pending AI actions.

### B. The Application Layer (Backend)
* **Technology:** FastAPI (Python), Uvicorn, SQLAlchemy.
* **Role:** The brain of the operation. It exposes RESTful APIs for the frontend, manages the PostgreSQL database sessions, and houses the core AI Agent logic (The State Machine).

### C. The Infrastructure Layer (Deployment)
* **Technology:** Systemd, Nginx, PostgreSQL (Ubuntu Native).
* **Role:** Ensures the application is running 24/7 in the background. Nginx acts as a reverse proxy to route internet traffic securely, while Systemd manages the backend process lifecycle.

---

## 3. The Core AI Agent Engine (The State Machine)

When a user submits a goal (e.g., *"Find all logs from today"*), it does not just go to an LLM and run the output. It travels through a strict **State Machine**:

### Phase 1: Goal Understanding & Planning (`planner.py`)
1. The user's prompt is received.
2. The AI generates a structured JSON plan breaking the goal into step-by-step actions.
3. Each step maps to a specific predefined "Handler" (e.g., `filesystem.find_files`).

### Phase 2: Policy Enforcement (`policy.py`)
1. Before any step is executed, the **Policy Engine** intercepts it.
2. It evaluates the risk. 
   * *Low Risk (Read-Only):* Allowed to proceed.
   * *Medium/High Risk (Modifications):* The engine pauses the task and sets its state to `PENDING_APPROVAL`.
3. The frontend detects this state and prompts the user to manually click "Approve" or "Reject".

### Phase 3: Execution & Sandboxing (`executor.py`)
1. Once approved, the specific handler executes the code natively on Ubuntu.
2. **Crucial Detail:** The AI does *not* write bash scripts. It passes arguments to securely written Python functions (e.g., `os.makedirs`, `shutil.copy`). This prevents command injection vulnerabilities.
3. Timeouts are enforced so a task cannot run infinitely.

### Phase 4: Verification & Rollback (`verifier.py` & `rollback.py`)
1. After execution, the Verification Agent looks at the output and confirms if the original goal was met.
2. If the task failed or caused an error, the system attempts a rollback to restore the system to its previous state (e.g., deleting a file that was incorrectly created).

---

## 4. In-Depth Security Mechanics

Your faculty will be highly interested in how you prevented the AI from destroying the computer. LinuxPilot implements **Defense in Depth**:

1. **The Action Registry:** The LLM cannot hallucinate arbitrary commands. The backend maintains a strict registry of allowed tools. If the LLM requests a tool not in the registry, it is immediately rejected.
2. **Path Canonicalization:** If the user asks to delete a file, the `FilesystemSecurityPolicy` resolves the absolute path (e.g., removing `../` traversal attempts). It checks this against a whitelist of allowed directories (like `/home/user/Documents`). If it tries to access `/etc/passwd` or `/root`, the action is blocked.
3. **Stateless Authentication:** Passwords are mathematically hashed using `bcrypt` before entering the database. Authentication is handled via short-lived JWT (JSON Web Tokens), meaning sessions are secure and stateless.

---

## 5. Deployment & Production Operations

You successfully transitioned LinuxPilot from a "development script" to a "production software application" using native Linux utilities:

* **Systemd (`linuxpilot-api.service`):** This tells the Linux kernel to run your FastAPI backend as a daemon. It automatically restarts it if it crashes (`Restart=always`), manages environment variables securely (`EnvironmentFile`), and drops privileges so it doesn't run as root (`User=sahil`).
* **Nginx (`linuxpilot.nginx.conf`):** Acting as a Reverse Proxy, Nginx sits in front of the application. It serves your static React files at blazing-fast speeds and securely forwards API requests (`/api/v1/`) to your internal Python server running on `127.0.0.1:8000`. This prevents direct exposure of the application server to the outside world.
* **Database Migrations (Alembic):** Instead of manually creating tables, you used Alembic to track database schemas via code. When you ran `alembic upgrade head`, it generated the relational structures (Users, Tasks, Audit Logs) dynamically.

---

## 6. Summary for the Report

If you need a paragraph summarizing the technical achievement for your report introduction:

> *"LinuxPilot is a robust, production-deployed system administration agent leveraging large language models. Built on a decoupled React and FastAPI architecture, it bridges the gap between natural language processing and low-level Linux operations. To mitigate the inherent risks of autonomous agents, the system implements a strict state-machine workflow featuring rigid action registries, path-canonicalized sandboxing, and human-in-the-loop approval gates. The entire stack is deployed natively on Ubuntu utilizing Nginx for reverse proxying and Systemd for process management, resulting in a secure, enterprise-grade desktop utility."*
