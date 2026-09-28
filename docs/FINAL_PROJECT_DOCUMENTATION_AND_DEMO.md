# LinuxPilot: Final Project Documentation & Demo Script

---

## Part 1: Project Overview & Understanding

### 1. Executive Summary
LinuxPilot is a "Trust-First" Artificial Intelligence Desktop Agent for Linux (specifically Ubuntu 24.04+). Unlike traditional AI agents that execute irreversible actions directly on a user's machine (which often leads to data loss or system corruption when the AI makes a mistake), LinuxPilot borrows **ACID semantics from database architecture** to protect the host system.

### 2. The Core Philosophy
The guiding principle of LinuxPilot is the **Reliability Contract**:
> *"The AI will make mistakes, but no mistake is ever allowed to reach the user's real files. Every mistake is detected, undone, and cryptographically recorded."*

### 3. Architecture & Security (How it works)
When you ask LinuxPilot to perform a task, it does **not** touch your hard drive directly. Instead, it operates through a strict, 4-pillar security model:

1. **OverlayFS (The Sandbox):** The agent works in a temporary "upper layer" filesystem. If it deletes a file, it only deletes it in the sandbox. The real file remains untouched until the user explicitly clicks "Commit".
2. **Cgroups v2 (Resource Limits):** The agent is restricted in how much CPU and RAM it can use. If the AI accidentally creates a "fork bomb" (infinite loop of processes), the OS automatically kills it before the computer freezes.
3. **Seccomp-bpf (System Call Filtering):** The agent is blocked from executing dangerous kernel commands (like mounting drives or opening unauthorized network ports).
4. **Write-Ahead Log (WAL) & Hash Chain:** Every single action the AI takes is recorded in a cryptographic hash chain. If a step fails, the system rolls back to a previous checkpoint automatically.

### 4. The Action Ladder
When LinuxPilot executes a task, it uses an "Action Ladder". It always tries to use the safest, most reliable method (Level 0) before escalating to riskier, visual methods (Level 4).

* **Level 0 (Filesystem API):** Moving, copying, and reading files programmatically (100% reliable).
* **Level 1 (AT-SPI Accessibility):** Reading the state of a GUI application by querying the Linux desktop accessibility tree.
* **Level 2 (Text Injection):** Injecting text directly into a focused GUI input field.
* **Level 3 (Keyboard Automation):** Sending specific keyboard shortcuts (like `Ctrl+S` to save) using `xdotool`.
* **Level 4 (Coordinate Mouse Clicks):** Moving the mouse to specific X/Y pixels (Least reliable, used only as a last resort).

---

## Part 2: Comprehensive Command & Task Reference

### CLI Commands (Terminal)
These commands are executed in your terminal (after running `source ~/LinuxPilot/.venv/bin/activate`).

| Command | Description |
|---------|-------------|
| `lp doctor` | Runs system diagnostics. Verifies your kernel supports `overlayfs`, checks `cgroup v2` status, tests AT-SPI accessibility, and validates your LLM API keys. |
| `lp daemon` | Starts the backend FSM (Finite State Machine) server and hosts the Next.js Dashboard on `http://localhost:8000`. |
| `lp run "<task>"` | Submits a task to the agent directly from the terminal. |
| `lp diff <task_id>` | Shows a Git-style diff of exactly what files the AI changed inside its sandbox. |
| `lp commit <task_id>` | Approves the changes in the sandbox and permanently writes them to your real hard drive. |
| `lp undo <task_id>` | Reverses a previously committed task using the Write-Ahead Log. |
| `lp audit verify <task_id>`| Cryptographically verifies the hash chain of a task to prove the logs were not tampered with. |

### Example Tasks you can ask LinuxPilot to perform:
1. **File Organization:** *"Organize my Downloads folder. Group all PDFs into a Documents folder, and all PNGs into an Images folder."*
2. **Data Extraction:** *"Read the 5 invoice PDFs in my Documents folder and create an Excel spreadsheet summarizing the Vendor Name, Date, and Total Amount."*
3. **GUI Automation:** *"Open Firefox, read the text on the currently active tab, and summarize it into a new text file on my Desktop."*

---

## Part 3: Faculty Presentation Demo Script

*Use this script step-by-step during your presentation/viva to perfectly demonstrate the project's unique selling points (USPs).*

### **Preparation (Before Faculty Arrives)**
1. Ensure your Ubuntu 26.04 machine is on.
2. Open two terminal windows.
3. In Terminal 1, start the daemon: 
   `cd ~/LinuxPilot && source .venv/bin/activate && lp daemon`
4. Open Firefox and go to `http://localhost:8000/dashboard`.
5. Ensure you have a messy `Downloads` folder with some PDFs, images, and text files.

### **Phase 1: Introduction (The Problem)**
**You say:** *"Good morning. Today we are presenting LinuxPilot. Most AI desktop agents are dangerous. If you tell an AI to organize your files, and it hallucinates, it might permanently delete your thesis. Our project solves this by treating the Operating System like a Database."*

### **Phase 2: The Dashboard & The Request**
**Action:** Show them the Dashboard in the browser.
**You say:** *"This is our control room. We are going to ask the AI to organize my Downloads folder."*
**Action:** Type *"Organize my Downloads folder by file extension"* into the New Task box on the Dashboard and hit **Run**.

### **Phase 3: Real-Time Monitoring & Sandboxing (The USP)**
**Action:** Point to the Live Timeline on the Dashboard as events populate.
**You say:** *"Notice how fast the events are appearing. The AI is currently generating a plan, checking security policies, and executing file moves. But here is the critical part: **It is not touching my actual files.** It is doing all of this inside an isolated `overlayfs` sandbox. If it makes a mistake right now, my computer is 100% safe."*

### **Phase 4: The Diff Review (Proof of Safety)**
**Action:** Once the task status changes to `review`, click the **Changes (Diff)** tab on the Dashboard.
**You say:** *"The AI has finished. Before we let it touch the real hard drive, we get a Git-style Diff. As you can see here, it wants to delete the original files (red) and add them to new categorized folders (green). Because I am the human in the loop, I have full control."*

### **Phase 5: The Commit**
**Action:** Click the **Commit Changes** button on the dashboard. Then open your Linux file manager and show them the newly organized Downloads folder.
**You say:** *"I clicked commit. The system used a Write-Ahead Log to safely merge the sandbox into my real filesystem. As you can see, the files are perfectly organized."*

### **Phase 6: The Tamper-Evident Audit (The Defense)**
**Action:** Click the **Audit Trail** tab on the Dashboard.
**You say:** *"Finally, for enterprise security, every single API call, file read, and state transition was cryptographically hashed into a chain. If malware or a bad actor tried to alter the logs to hide what the AI did, this chain would immediately break and alert the system administrator. Our system is completely transparent and tamper-proof."*

### **Conclusion**
**You say:** *"In conclusion, LinuxPilot isn't just a wrapper around ChatGPT. It is a robust, kernel-level orchestration engine that makes AI safe for enterprise desktop environments. Thank you."*
