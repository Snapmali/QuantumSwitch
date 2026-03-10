"""Main FastAPI application entry point."""
import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings, IS_FROZEN, WORK_DIR
from .api import songs, game, system
from .utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Bootstrap dependency injection container
    from .core.bootstrap import bootstrap_services
    bootstrap_services()

    # Load songs cache on startup
    from .api.songs import load_songs_cache
    load_songs_cache()

    yield

    # Cleanup
    from .core.container import reset_container
    reset_container()
    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="External song selector for Hatsune Miku Project DIVA MegaMix+",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(songs.router, prefix="/api")
app.include_router(game.router, prefix="/api")
app.include_router(system.router, prefix="/api")

# Try to serve static frontend files
if IS_FROZEN:
    # In frozen mode, frontend files are in the bundle directory
    frontend_dist = Path(sys._MEIPASS) / "frontend" / "dist"
else:
    # In development mode, frontend files are relative to backend
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(frontend_dist / "index.html")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        # Serve index.html for all routes (SPA behavior)
        file_path = frontend_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


def main():
    """Main entry point for the application."""
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG and not IS_FROZEN,  # Disable reload in frozen mode
        log_level="debug" if settings.DEBUG else "info"
    )


if __name__ == "__main__":
    main()
