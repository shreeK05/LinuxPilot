"""
FastAPI Application
Main API server for LinuxPilot
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from linuxpilot.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("LinuxPilot API starting up")

    # Startup tasks
    # 1. Recover incomplete commits
    try:
        from linuxpilot.workspace.commit import CommitManager
        workspace_base = settings.WORKSPACE_BASE / "tasks"
        if workspace_base.exists():
            for task_dir in workspace_base.iterdir():
                if task_dir.is_dir():
                    journal_dir = task_dir / "journal"
                    if journal_dir.exists():
                        workspace_info = {
                            "journal_dir": str(journal_dir),
                            "trash_dir": str(task_dir / "trash"),
                            "upper_dir": str(task_dir / "upper"),
                            "lower_dir": str(settings.REAL_DATA_BASE),
                        }
                        mgr = CommitManager(workspace_info)
                        recovered = mgr.recover()
                        if recovered:
                            logger.warning(f"Recovered {len(recovered)} incomplete commits")
    except Exception as e:
        logger.warning(f"Commit recovery skipped: {e}")

    # 2. Cleanup leaked sandboxes and mounts
    try:
        from linuxpilot.orchestrator.janitor import Janitor
        janitor = Janitor()
        janitor.cleanup_all()
    except Exception as e:
        logger.warning(f"Janitor cleanup skipped: {e}")

    yield

    # Shutdown tasks
    logger.info("LinuxPilot API shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="A Trust-First OS Agent for Linux — ACID for AI Desktop Agents",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    from linuxpilot.api.routes import tasks, health, audit, websocket

    app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])
    app.include_router(
        tasks.router, prefix=f"{settings.API_V1_STR}/tasks", tags=["tasks"]
    )
    app.include_router(
        audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["audit"]
    )
    app.include_router(
        websocket.router, prefix=f"{settings.API_V1_STR}/ws", tags=["websocket"]
    )

    # Metrics endpoint
    try:
        from prometheus_client import make_asgi_app

        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
    except ImportError:
        logger.warning("prometheus_client not installed, metrics disabled")

    # Serve dashboard static files if available
    dashboard_dist = Path(__file__).parent.parent.parent.parent / "dashboard" / "out"
    if dashboard_dist.exists():
        app.mount(
            "/dashboard",
            StaticFiles(directory=str(dashboard_dist), html=True),
            name="dashboard",
        )

    return app
