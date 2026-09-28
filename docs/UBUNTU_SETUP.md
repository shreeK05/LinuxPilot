# LinuxPilot — Ubuntu Setup Guide

This guide walks you through setting up LinuxPilot on a fresh Ubuntu 22.04 / 24.04 machine.

---

## Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Install Node.js 20+
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install build tools (needed for some Python packages)
sudo apt install -y build-essential libpq-dev git curl
```

---

## 1. Transfer the Project

Copy the project zip to your Ubuntu machine and extract it:

```bash
# If transferring via SCP from Windows:
# scp "LinuxPilot.zip" user@ubuntu-machine:~/

unzip LinuxPilot.zip -d ~/LinuxPilot
cd ~/LinuxPilot
```

---

## 2. Configure PostgreSQL

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << 'EOF'
CREATE USER postgres WITH PASSWORD 'postgres';
CREATE DATABASE linuxpilot OWNER postgres;
GRANT ALL PRIVILEGES ON DATABASE linuxpilot TO postgres;
\q
EOF
```

> **Note:** If you want a different port, update `POSTGRES_PORT` in the `.env` file.
> Default in `.env` is port `5433` — if your PostgreSQL uses the default port `5432`, update the `.env` accordingly.

---

## 3. Set Up the Backend

```bash
cd ~/LinuxPilot/apps/api

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Install Playwright browsers for browser actions
python -m playwright install chromium
```

---

## 4. Configure Environment

Create the root `.env` file (or edit it if it already exists):

```bash
cd ~/LinuxPilot
nano .env
```

Set these values (adjust to your setup):

```env
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=linuxpilot
POSTGRES_HOST=localhost
POSTGRES_PORT=5432          # Ubuntu default is 5432 (not 5433)

# API Configuration
API_PORT=8000
ENVIRONMENT=development

# Frontend Configuration
VITE_API_URL=http://localhost:8000/api/v1

# LLM Provider (Groq OpenAI-compatible API)
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_your_api_key_here
LLM_MODEL=openai/gpt-oss-120b
```

Also update the frontend `.env`:

```bash
cat > ~/LinuxPilot/apps/web/.env << 'EOF'
VITE_API_URL=http://localhost:8000/api/v1
EOF
```

---

## 5. Run Database Migrations

```bash
cd ~/LinuxPilot/apps/api
source .venv/bin/activate

# Run Alembic migrations
alembic upgrade head
```

> If migrations fail, check that PostgreSQL is running and the credentials match.

---

## 6. Run Backend Tests

```bash
cd ~/LinuxPilot/apps/api
source .venv/bin/activate

# Set PYTHONPATH and run tests
PYTHONPATH=. python -m pytest -v
```

**Expected result: 84 passed, 0 failed**

> On Linux, seccomp and resource limit tests will run properly (not just use the Windows fallback).

---

## 7. Start the Backend

```bash
cd ~/LinuxPilot/apps/api
source .venv/bin/activate

# Start with auto-reload for development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's running:

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

---

## 8. Set Up the Frontend

```bash
cd ~/LinuxPilot/apps/web

# Install dependencies
npm install

# Build for production
npm run build

# OR run dev server
npm run dev
```

The dev server will be at: `http://localhost:5173`

---

## 9. Verify the Full Stack

1. Open `http://localhost:5173` in your browser
2. Register with any username/password (e.g., `shreek` / `shree@123`)
3. Try these goals:
   - `What OS architecture am I running?` → should show `x86_64` or `arm64`
   - `List the files in my Downloads folder.` → shows actual files
   - `Make a LAB folder inside my Downloads folder.` → requires approval → creates `~/Downloads/LAB/`
   - `Find all PDF files in Downloads.`

---

## 10. Linux-Specific Features (Now Active)

On Ubuntu, these features are fully enabled:

| Feature | Status on Linux |
|---------|----------------|
| seccomp syscall filtering | ✅ Active |
| `resource.setrlimit` CPU/memory limits | ✅ Active |
| `O_NOFOLLOW` symlink protection | ✅ Active |
| Protected path blocking (`/etc`, `~/.ssh`) | ✅ Active |
| Filesystem security policy | ✅ Active |

---

## 11. Troubleshooting

### Backend won't start: `ModuleNotFoundError`
```bash
# Make sure you're in the right directory and venv is active
cd ~/LinuxPilot/apps/api
source .venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --reload
```

### Database connection error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check port (Ubuntu default is 5432, not 5433)
sudo -u postgres psql -c "\l"

# Update .env: POSTGRES_PORT=5432
```

### CORS errors in browser
```bash
# Backend must be accessible from the browser
# Update apps/web/.env:
echo "VITE_API_URL=http://localhost:8000/api/v1" > ~/LinuxPilot/apps/web/.env

# Restart frontend dev server
npm run dev
```

### Frontend can't reach backend (different machine)
```bash
# If Ubuntu is a remote VM, use the VM's IP in the frontend .env:
echo "VITE_API_URL=http://<ubuntu-ip>:8000/api/v1" > ~/LinuxPilot/apps/web/.env

# Also update BACKEND_CORS_ORIGINS in apps/api/app/core/config.py
# Add your browser origin (e.g., http://<your-pc-ip>:5173)
```

### Alembic: `Target database is not up to date`
```bash
cd ~/LinuxPilot/apps/api
source .venv/bin/activate
alembic upgrade head
```

---

## Important Notes for Ubuntu Testing

1. **PostgreSQL port**: Ubuntu default is `5432`. The Windows dev `.env` uses `5433`. Change `POSTGRES_PORT=5432` in `.env`
2. **seccomp**: Fully active on Linux. If it causes issues, it has a graceful fallback — check logs
3. **Home directory paths**: On Ubuntu, home is `/home/<username>/`. The planner uses `Path.home()` which resolves correctly
4. **Downloads folder**: The planner looks for `~/Downloads`. Make sure it exists: `mkdir -p ~/Downloads`
5. **LLM API key**: The key in `.env` is a Groq API key. Make sure it's valid, or set `LLM_PROVIDER=mock` for testing without LLM
