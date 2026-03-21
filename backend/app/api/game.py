"""Game control API endpoints."""
import traceback

from fastapi import APIRouter, HTTPException

from ..core.bootstrap import (
    get_song_selector,
    get_pvdb_parser, get_game_status_processor,
)
from ..models import (
    GameStatusResponse,
    SwitchSongRequest,
    SwitchSongResponse,
    ApiResponse,
    ChartStyle,
    CurrentSongInfo,
    CurrentSongDifficultyInfo,
    DifficultyType, Song,
)
from ..utils.logger import logger

router = APIRouter(prefix="/game", tags=["game"])


def _build_current_song_info(song: Song, style: ChartStyle) -> CurrentSongInfo:
    """Build CurrentSongInfo from a Song object."""
    # Build Mod enabled status lookup table
    mod_enabled_map = {m.id: m.enabled for m in song.mod_infos}

    # Build difficulty info with enabled status
    difficulty_infos = []
    seen_difficulties = set()
    for d in song.chart_infos:
        # Skip duplicate difficulty types (we only need one entry per type)
        if d.type in seen_difficulties or style != d.style:
            continue
        seen_difficulties.add(d.type)

        # Original difficulty is always enabled
        if d.is_original:
            is_difficulty_enabled = True
        else:
            # Check if the mod providing this difficulty is enabled
            is_difficulty_enabled = mod_enabled_map.get(d.mod_id, False) if d.mod_id is not None else song.is_vanilla

        difficulty_infos.append(CurrentSongDifficultyInfo(
            name=d.type.display_name,
            enabled=is_difficulty_enabled
        ))

    return CurrentSongInfo(
        id=song.id,
        name=song.get_display_name(),
        nameEn=song.name_en,
        difficulties=difficulty_infos
    )


def get_game_status_internal() -> GameStatusResponse:
    """Get current game status."""
    gsp = get_game_status_processor()

    # Check if game is running, and try to attach to the game process.
    pid = gsp.attach_for_pid()

    if pid is None:
        return GameStatusResponse(running=False)

    # Get game state
    game_state = gsp.get_game_state()

    # Get current selection from memory
    pvid, is_ingame, style = gsp.get_current_selection()

    # Cast ChartStyle to string
    current_style = style.value if style else None

    # Get current song info
    current_song_info = None
    if pvid is not None:
        parser = get_pvdb_parser()
        song = parser.get_song(pvid)
        if song:
            current_song_info = _build_current_song_info(song, style)

    return GameStatusResponse(
        running=True,
        processId=pid,
        currentSongId=pvid,
        gameState=game_state.name if game_state is not None else None,
        currentSongInfo=current_song_info,
        currentChartStyle=current_style,
        isIngame=is_ingame if is_ingame is not None else False,
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

        # Convert style string to ChartStyle
        style = ChartStyle.from_string(request.style)

        # Attempt song switch
        success, message, actual_difficulty, mode = selector.switch_song(
            song=song,
            difficulty=difficulty,
            style=style
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


@router.get("/current", response_model=ApiResponse[CurrentSongInfo])
async def get_current_song():
    """Get currently selected song in game."""
    try:
        parser = get_pvdb_parser()
        gsp = get_game_status_processor()

        # Get current selection from selector (reads from game memory)
        pvid, is_ingame, style = gsp.get_current_selection()

        if pvid is None:
            return ApiResponse(success=True, data=CurrentSongInfo(id=0, name=""))

        # Get song info from parser
        song = parser.get_song(pvid)

        if song is None:
            return ApiResponse(
                success=True,
                data=CurrentSongInfo(
                    id=pvid,
                    name=f"Unknown Song ({pvid})"
                )
            )

        current_song_info = _build_current_song_info(song, style)

        return ApiResponse(success=True, data=current_song_info)
    except Exception as e:
        logger.error(f"Failed to get current song: {e}")
        raise HTTPException(status_code=500, detail=str(e))
