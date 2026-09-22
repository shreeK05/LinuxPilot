# Linux Runtime Architecture

LinuxPilot is designed to execute deterministic tasks on Ubuntu 24.04 LTS.

## Core Principles
1. **No Arbitrary Shell Scripts:** Operations must use strictly bound ActionRegistry handlers mapped to native Python implementations (e.g. `shutil.copy` or `psutil`).
2. **Platform Separation:** The API and frontend can be developed on Windows, but OS-level tasks are checked and will return `UNSUPPORTED_PLATFORM` when run on Windows.
3. **Recovery Mechanism:** Snapshots are taken before any destructive filesystem operation (`MOVE`, `RENAME`, `WRITE`, `DELETE`) to allow rollback.
