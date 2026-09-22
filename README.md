# LinuxPilot

A high-end, production-style, self-hosted Linux desktop AI agent. 
Built with a free-tier/open-source-first architecture.

## Architecture

The project strictly follows a phased architecture to prevent LLM hallucination mapping directly to OS execution:

1. **State Machine Driven**: All execution follows explicit states (UNDERSTANDING -> PLANNING -> POLICY -> EXECUTING).
2. **DAG Planner**: Complex goals are separated into Directed Acyclic Graphs with topological sorting.
3. **Policy Engine Gatekeeper**: Actions are evaluated against Risk Levels before any execution occurs.
4. **Decoupled Orchestrator**: The central agent lifecycle exists entirely independent of FastAPI routes.

*See `docs/architecture/agent-core.md` for a comprehensive architecture overview.*

## Setup Instructions

### 1. Requirements
- Docker and Docker Compose
- Python 3.10+
- Node.js 18+

### 2. Configure Environment Variables
Copy `.env.example` to `.env` in the root folder:
```bash
cp .env.example .env
```
Ensure ports do not conflict with your host machine.

### 3. Start Database
Run the PostgreSQL database via Docker Compose:
```bash
docker compose up -d
```

### 4. Setup Backend
```bash
cd apps/api
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000
```

### 5. Setup Frontend
```bash
cd apps/web
npm install

# Start Vite dev server
npm run dev
```

### 6. Usage
Visit the dashboard at `http://localhost:5173`. The UI will communicate with the backend at `http://localhost:8000/api/v1`.
