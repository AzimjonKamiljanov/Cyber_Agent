"""Main application entrypoint for Cyber Agent.

Binds exclusively to 127.0.0.1 per MASTER_PLAN §5.1, §7.6.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from cyber_agent.api.routes import router as http_router
from cyber_agent.api.websocket import ws_router
from cyber_agent.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup initialization
    settings = get_settings()
    settings.cyber_data_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown cleanup


def create_app() -> FastAPI:
    app = FastAPI(
        title="Cyber Agent",
        description="Personal voice-first Uzbek AI assistant",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(http_router)
    app.include_router(ws_router)

    pwa_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "pwa"
    if pwa_dir.exists():
        app.mount("/", StaticFiles(directory=str(pwa_dir), html=True), name="pwa")

    return app


app = create_app()


def run_server() -> None:
    settings = get_settings()
    uvicorn.run(
        "cyber_agent.main:app",
        host=settings.cyber_host,  # 127.0.0.1
        port=settings.cyber_port,  # 8000
        reload=False,
    )


if __name__ == "__main__":
    run_server()
