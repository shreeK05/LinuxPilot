# LinuxPilot: Complete Testing & Capability Guide

This guide provides a comprehensive list of every capability built into LinuxPilot. You can use these exact prompts during your testing or presentation to demonstrate the sheer power and versatility of the AI agent.

---

## 1. System Information & Diagnostics
*These tasks demonstrate the AI's ability to safely read system states without modifying anything.*

* **Command:** *"Give me a summary of the current system memory and CPU usage."*
* **Command:** *"What version of Ubuntu am I running, and what is my kernel version?"*
* **Command:** *"Check the status of the PostgreSQL service."*

---

## 2. Filesystem Operations (Read-Only)
*These tasks use the `filesystem.*` handlers and run instantly because they are low-risk.*

* **Command:** *"Find all `.pdf` files inside my Downloads folder."*
* **Command:** *"List all the contents of my Documents directory."*
* **Command:** *"Read the contents of `/etc/os-release` and tell me what it says."*
* **Command:** *"When was the file `~/Documents/LinuxPilot_ReadyForLinux/README.md` last modified, and how large is it?"*

---

## 3. Filesystem Operations (Modifications)
*These are High-Risk tasks. They demonstrate the **Human-in-the-Loop Approval Gate**. The AI will pause and wait for you to click "Approve" in the UI.*

* **Command:** *"Create a new folder in my Documents called 'ProjectData'."*
* **Command:** *"Create a new text file inside 'ProjectData' called 'notes.txt' and write 'Meeting at 5 PM' inside it."*
* **Command:** *"Rename the file 'notes.txt' to 'meeting_notes.txt'."*
* **Command:** *"Move 'meeting_notes.txt' from 'ProjectData' to my Desktop."*
* **Command:** *"Safely delete the 'ProjectData' folder."* (Will trigger the `FSDeleteHandler`).

---

## 4. Advanced Document Processing
*These tasks showcase the AI's ability to intelligently parse complex file formats.*

* **Command:** *"Extract the text from the PDF file located at `~/Documents/invoice.pdf` and summarize the total amount."*
* **Command:** *"Read the Excel file `~/Documents/budget.xlsx` and tell me what is in the first 5 rows."*
* **Command:** *"Create a new Excel file at `~/Desktop/report.xlsx` with columns for 'Name', 'Role', and 'Salary', and fill in 3 dummy employees."*

---

## 5. Safe Terminal Execution
*This demonstrates the AI safely falling back to terminal commands for utilities it doesn't have native Python handlers for, using the `terminal.execute_safe` handler.*

* **Command:** *"Ping google.com 3 times and show me the average latency."*
* **Command:** *"Run the `df -h` command to show my disk space usage."*
* **Command:** *"Use the `tar` command to compress my 'ProjectData' folder into an archive."*

---

## 6. Headless Browser Automation
*This is the most visually impressive feature. The AI uses Playwright to open a headless browser in the background and interact with the web.*

* **Command:** *"Go to Wikipedia, search for 'Linux', and extract the first paragraph of the main article."*
* **Command:** *"Navigate to HackerNews and give me the titles of the top 3 trending articles."*
* **Command:** *"Open the weather website for New York and extract the current temperature."*

---

### Tips for the Best Demo Experience:
1. **Mix and Match:** You can combine commands! For example: *"Read the CPU usage, and write the result into a new text file called `cpu_log.txt` on my Desktop."* The AI will automatically chain the `SystemInfoHandler` and the `FSWriteFileHandler` together!
2. **Emphasize the Sandbox:** If you test a command like *"Delete the root directory (/)"*, show the audience how the system immediately catches it and blocks it due to security policies.
3. **Show the Audit Logs:** After running 3 or 4 of these commands, go to the Audit Trail tab in the UI. Show that everything you just did is permanently recorded in the database.
