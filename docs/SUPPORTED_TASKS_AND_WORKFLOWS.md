# LinuxPilot: Supported Tasks & Workflows

LinuxPilot is designed as a generalized, multi-modal desktop agent. It executes tasks using an **Action Ladder** that determines the safest and most efficient way to achieve a goal. 

When you submit a natural language goal like *"Organize my files"*, the LLM Planner maps your intent to specific tools from this ladder.

---

## The Action Ladder Levels

The engine always prefers lower-level (deterministic) operations over higher-level (visual) operations to guarantee reliability and avoid UI race conditions.

### Level 0 (L0): Deterministic Filesystem Operations
These are direct OS-level calls running inside the `overlayfs` sandbox. They are 100% reliable, instantaneous, and immune to screen resolution or UI theme changes.

**Supported Tools:**
* `fs.list` - List directory contents and metadata.
* `fs.stat` - Get specific file sizes, timestamps, and permissions.
* `fs.mkdir` - Create directory trees safely.
* `fs.read_text` - Extract text content from raw files.
* `fs.move` - Rename files or move them between directories (with collision resolution).
* `fs.copy` - Duplicate files safely.
* `fs.delete` - Remove files or empty directories (can be rolled back).
* `doc.extract_pdf` - Parse text directly from PDF documents.
* `sheet.write` - Generate Excel `.xlsx` files natively.

**Example Tasks You Can Issue:**
* *"Organize my ~/Downloads folder by grouping files into Images, Documents, and Code folders based on their extensions."*
* *"Read all the invoice PDFs in ~/Documents, extract the Vendor Name and Total, and generate an Excel report called summary.xlsx."*
* *"Rename all `.jpg` files in the Photos folder to append their creation date."*
* *"Find all empty directories in my workspace and delete them."*

---

### Level 1 (L1): Application State Reading (AT-SPI)
Instead of relying on fragile OCR or screenshot analysis, LinuxPilot uses the Linux desktop's AT-SPI accessibility tree to read the state of applications exactly as the OS sees them.

**Supported Tools:**
* `ui.wait_for_text` - Poll the accessibility tree until specific text appears on screen.
* `ui.read_tree` - Dump the semantic hierarchy of the active window.

**Example Tasks You Can Issue:**
* *"Wait for Firefox to finish loading, then read the main article text."*
* *"Open Calculator, wait for the result to appear, and read the final value."*
* *"Check if the 'Save' button is currently enabled or disabled in the active window."*

---

### Level 2 (L2): Editable Text Injection
Instead of simulating raw keystrokes blindly, LinuxPilot can directly inject text into focused input fields via AT-SPI, avoiding typos and lag.

**Supported Tools:**
* `ui.set_text` - Replace the text in the currently focused input field or text area.

**Example Tasks You Can Issue:**
* *"Fill out the 'First Name' and 'Last Name' fields in this Firefox web form using data from `users.csv`."*
* *"Replace the selected paragraph in LibreOffice with 'Approved for Release'."*
* *"Clear the terminal input and paste this specific bash command."*

---

### Level 3 (L3): Keyboard Automation
When semantic interaction isn't enough, LinuxPilot uses `xdotool` to simulate complex keyboard shortcuts and navigation.

**Supported Tools:**
* `ui.key` - Press specific keyboard combinations (e.g., `ctrl+s`, `alt+tab`).
* `ui.type` - Type text sequentially (used when L2 injection isn't supported by the app).

**Example Tasks You Can Issue:**
* *"Press Ctrl+S to save the document, wait for the prompt, hit Enter, then Alt+F4 to close the app."*
* *"Tab through the fields in LibreOffice Calc until you reach the 'Total' column."*
* *"Press Super (Windows key), type 'Terminal', and hit Enter to launch a new shell."*

---

### Level 4 (L4): Coordinate GUI Clicking (Fallback)
This is the highest-risk layer. It is used only when an application uses custom rendering (like a video game or a heavily customized Electron app) that doesn't expose its buttons to the Linux AT-SPI accessibility tree.

**Supported Tools:**
* `ui.click_xy` - Move the mouse to absolute `X, Y` coordinates and perform a left/right click.
* *(Note: In future versions, this integrates directly with Set-of-Marks Vision-Language Models to find coordinates visually).*

**Example Tasks You Can Issue:**
* *"Click the 'Submit' button located exactly at coordinates 850, 400."*
* *"Right-click in the center of the screen to open the context menu."*

---

## Specialized Multi-Modal Workflows

By combining the levels of the Action Ladder, LinuxPilot can execute complex, multi-modal tasks that span both the terminal and the GUI.

**Workflow 1: Web Data Entry (L0 + L3)**
> *"Read the customer data from `clients.csv` (L0), open Firefox to the CRM portal (L3), tab through the input fields (L3), and paste the data into the form (L2)."*

**Workflow 2: Report Generation (L1 + L0)**
> *"Open the system monitoring tool, wait for the CPU usage to spike above 90% (L1), read the current active processes (L1), and write them to a log file `incident.txt` (L0)."*

**Workflow 3: Adversarial Containment (Sandbox Test)**
> *"Read this malicious invoice PDF that secretly contains a prompt injection telling you to run `rm -rf /`."*
> *Result:* The LLM might try to run the command, but the `seccomp-bpf` filter and `overlayfs` sandbox will block the deletion, flag a policy violation, and roll back the attempt, demonstrating the system's ACID security guarantees.
