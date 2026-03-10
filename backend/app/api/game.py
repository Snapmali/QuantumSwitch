"""Game control API endpoints."""
import traceback
from fastapi import APIRouter, HTTPException

from ..models import (
    GameStatusResponse,
    SwitchSongRequest,
    SwitchSongResponse,
    ApiResponse,
    CurrentSongResponse,
)
from ..models.song import DifficultyType
from ..core.bootstrap import (
    get_process_manager,
    get_memory_operator,
    get_song_selector,
    get_pvdb_parser,
)
from ..utils.logger import logger

router = APIRouter(prefix="/game", tags=["game"])


def get_game_status_internal() -> GameStatusResponse:
    """Get current game status."""
    pm = get_process_manager()
    mem = get_memory_operator()
    selector = get_song_selector()  # Ensure selector is initialized

    # Check if game is running
    is_running = pm.find_process() is not None

    if not is_running:
        return GameStatusResponse(running=False)

    # Get current selection from memory
    pvid, sort_id, difficulty = mem.get_current_selection()

    # Get difficulty name
    difficulty_name = None
    if difficulty is not None:
        try:
            difficulty_name = DifficultyType(difficulty).display_name
        except ValueError:
            difficulty_name = f"Unknown({difficulty})"

    # Get game state
    game_state = mem.get_game_state()

    return GameStatusResponse(
        running=is_running,
        processId=pm.process_id,
        currentSongId=pvid,
        currentSortId=sort_id,
        currentDifficulty=difficulty,
        currentDifficultyName=difficulty_name,
        gameState=game_state,
        edenVersion=mem.is_eden_version,
        edenOffset=mem.eden_offset
    )


@router.get("/status", response_model=ApiResponse[GameStatusResponse])
async def get_game_status():
    """Get current game status."""
    try:
        status = get_game_status_internal()
        return ApiResponse(success=True, data=status)
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Failed to get game status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch", response_model=ApiResponse[SwitchSongResponse])
async def switch_song(request: SwitchSongRequest):
    """Switch to a specific song with difficulty."""
    try:
        selector = get_song_selector()

        # Check game status first
        status = get_game_status_internal()
        if not status.running:
            raise HTTPException(status_code=400, detail="Game is not running")

        # Get song info
        parser = get_pvdb_parser()
        song = parser.get_song(request.songId)
        if song is None:
            raise HTTPException(status_code=404, detail=f"Song with ID {request.songId} not found")

        # Convert difficulty int to DifficultyType
        try:
            difficulty = DifficultyType(request.difficulty)
        except ValueError:
            difficulty = DifficultyType.HARD

        # Attempt song switch
        success, message, actual_difficulty, mode = selector.switch_song(
            song=song,
            difficulty=difficulty
        )

        # Get actual difficulty name
        actual_difficulty_name = None
        if actual_difficulty:
            actual_difficulty_name = actual_difficulty.display_name

        return ApiResponse(
            success=success,
            data=SwitchSongResponse(
                success=success,
                message=message,
                actualDifficulty=actual_difficulty.value if actual_difficulty else None,
                actualDifficultyName=actual_difficulty_name,
                requiresDelayedUpdate=(mode is not None and mode.value == "delayed")
            ),
            error=None if success else message
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Failed to switch song: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current", response_model=ApiResponse[CurrentSongResponse])
async def get_current_song():
    """Get currently selected song in game."""
    try:
        mem = get_memory_operator()
        pvid, sort_id, difficulty = mem.get_current_selection()

        if pvid is None:
            return ApiResponse(success=True, data=CurrentSongResponse())

        parser = get_pvdb_parser()
        song = parser.get_song(pvid)

        if song is None:
            return ApiResponse(success=True, data=CurrentSongResponse(
                songId=pvid,
                sortId=sort_id,
                difficulty=difficulty
            ))

        # Get difficulty name
        difficulty_name = None
        if difficulty is not None:
            try:
                difficulty_name = DifficultyType(difficulty).display_name
            except ValueError:
                pass

        return ApiResponse(
            success=True,
            data=CurrentSongResponse(
                songId=pvid,
                sortId=sort_id,
                difficulty=difficulty,
                difficultyName=difficulty_name,
                songName=song.name
            )
        )
    except Exception as e:
        logger.error(f"Failed to get current song: {e}")
        raise HTTPException(status_code=500, detail=str(e))
