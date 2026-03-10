"""System API endpoints."""
from fastapi import APIRouter
from ..models import ApiResponse, ConfigResponse
from ..config import settings
from ..core.bootstrap import (
    get_process_manager,
    get_memory_operator
)

router = APIRouter(tags=["system"])


@router.get("/health", response_model=ApiResponse[dict])
async def health_check():
    """Health check endpoint."""
    pm = get_process_manager()
    is_running = pm.find_process() is not None

    return ApiResponse(
        success=True,
        data={
            "status": "healthy",
            "gameRunning": is_running,
            "version": settings.APP_VERSION
        }
    )


@router.get("/config", response_model=ApiResponse[ConfigResponse])
async def get_config():
    """Get application configuration."""
    pm = get_process_manager()
    mem = get_memory_operator()

    process_info = pm.get_process_info()

    return ApiResponse(
        success=True,
        data=ConfigResponse(
            appName=settings.APP_NAME if hasattr(settings, 'APP_NAME') else "Quantum Switch",
            appVersion=settings.APP_VERSION,
            gameProcessName=settings.GAME_PROCESS_NAME,
            gameRunning=process_info is not None,
            gameBaseAddress=hex(process_info["base_address"]) if process_info else None,
            edenOffsetApplied=mem.is_eden_version if process_info else None,
            pvdbFiles=settings.PVDB_FILES if hasattr(settings, 'PVDB_FILES') else ["mod_pv_db.txt", "mdata_pv_db.txt"]
        )
    )
