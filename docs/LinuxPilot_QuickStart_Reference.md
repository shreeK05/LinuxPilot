# LinuxPilot Quick Start & Command Reference

## 1. Easy Setup on Ubuntu (24.04 LTS)

Follow these simple steps to install and run LinuxPilot on a fresh Ubuntu installation.

### Step 1: Run the One-Shot Installer
Open your terminal and run this single command. It will clone the repository, install all system dependencies (like AT-SPI and `cgroup-tools`), and set up the Python environment automatically:

```bash
curl -sL https://raw.githubusercontent.com/shreeK05/LinuxPilot/master/install.sh | bash
```

### Step 2: Add your API Key
The installer will create a folder called `LinuxPilot` in your home directory. Open the environment configuration file to add your Groq (or Gemini) API key:

```bash
cd ~/LinuxPilot
nano .env
```
*(Find the line `LLM_API_KEY=gsk_your_api_key_here`, replace it with your actual key, and press `Ctrl+O`, `Enter`, then `Ctrl+X` to save and exit).*

### Step 3: Start the Application
Activate the virtual environment and start the background daemon:

```bash
source .venv/bin/activate
lp daemon
```

### Step 4: Open the Dashboard
Open your web browser and navigate to:
**http://localhost:8000/dashboard**

From this control panel, you can submit tasks, watch the agent execute them in real-time, review the file diffs before approving changes, and view the tamper-evident audit logs.

---

## 2. Command-Line Interface (CLI) Reference

If you prefer using the terminal instead of the web dashboard, LinuxPilot offers a comprehensive set of CLI commands. To use these, ensure your virtual environment is active (`source ~/LinuxPilot/.venv/bin/activate`).

| Command | Description | Example |
|---------|-------------|---------|
| `lp doctor` | Runs system diagnostics to check kernel features (cgroup v2, overlayfs), AT-SPI availability, and LLM configuration. | `lp doctor` |
| `lp daemon` | Starts the LinuxPilot backend API server and serves the Next.js web dashboard on port 8000. | `lp daemon --port 8000` |
| `lp run <goal>` | Submits a new natural language task to the agent. | `lp run "Organize my Downloads"` |
| `lp diff <task-id>` | Shows the file changes (Git-style diff) made by the agent inside the sandbox overlay. | `lp diff t-1a2b3c4d` |
| `lp commit <task-id>` | Approves and writes the sandboxed changes to your actual hard drive. | `lp commit t-1a2b3c4d` |
| `lp undo <task-id>` | Uses the Write-Ahead Log (WAL) to completely roll back a previously committed task. | `lp undo t-1a2b3c4d` |
| `lp audit verify <task-id>`| Checks the cryptographic hash chain of a task to ensure no log tampering occurred. | `lp audit verify t-1a2b3c4d` |

---

## 3. Supported Tasks & Workflows (The Action Ladder)

LinuxPilot utilizes a layered "Action Ladder" to interact with your system. It prefers safe, deterministic operations but can escalate to GUI manipulation if necessary.

Here are examples of the types of tasks you can ask LinuxPilot to perform:

### Level 0: Deterministic Filesystem Operations (Safest)
* **Organize files:** *"Organize my ~/Downloads folder by grouping files into Images, Documents, and Archives directories."*
* **Content-aware renaming:** *"Read the contents of these invoices in ~/Documents and rename them based on the Vendor Name and Date."*
* **Batch processing:** *"Extract all text from the PDFs in the reports folder and save them as a single CSV file."*

### Level 1: Application State (AT-SPI Accessibility)
* **Read Application Data:** *"Open Calculator and read the current value."*
* **Extract Web Content:** *"Read the text currently visible in the active Firefox tab."*

### Level 2: Editable Text Injection
* **Form filling:** *"Fill out the currently focused web form in Firefox using the user data from `data.csv`."*
* **Text Replacement:** *"Replace the selected text in Mousepad with 'Approved by LinuxPilot'."*

### Level 3: Keyboard Automation (xdotool)
* **Shortcut Execution:** *"Press Ctrl+S to save the current document, then close the window with Alt+F4."*
* **Navigation:** *"Tab through the fields in the LibreOffice Calc window until you reach the 'Total' column."*

### Level 4: Coordinate Mouse Clicks (Fallback)
* **GUI Navigation:** *"Click the 'Submit' button located at the bottom right of the screen."*
* *(Note: Level 4 is only used when the application does not expose its buttons via the AT-SPI accessibility tree).*

---

## 4. Understanding the Sandbox (ACID Guarantees)

Whenever you issue a task, LinuxPilot operates under strict safety guarantees:

1. **OverlayFS:** Changes are made to a temporary upper layer. If the agent makes a mistake (e.g., deletes the wrong file), you simply hit "Discard" in the dashboard, and your real files remain untouched.
2. **Cgroup v2:** The agent's resource usage (CPU/Memory) is capped. If a task spawns a "fork bomb", the cgroup automatically kills the processes to protect your OS.
3. **Seccomp-bpf:** The agent's system calls are filtered. It is forbidden from making unauthorized network connections or attempting to mount external drives. 
4. **Write-Ahead Logging (WAL):** When you click "Commit", changes are written sequentially. If power is lost mid-commit, LinuxPilot will either fully complete or fully reverse the changes on the next boot.
