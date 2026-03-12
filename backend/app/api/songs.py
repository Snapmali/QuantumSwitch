"""Song-related API endpoints."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from ..models import (
    SongResponse,
    SongListResponse,
    ApiResponse,
)
from ..core.bootstrap import get_pvdb_parser
from ..core.favorites_manager import get_favorites_manager
from ..utils.logger import logger

router = APIRouter(prefix="/songs", tags=["songs"])

# 歌曲缓存（数据缓存而非服务实例）
_cached_songs: list[SongResponse] = []
_cache_loaded: bool = False


def load_songs_cache() -> list[SongResponse]:
    """Load songs from PVDB files into cache."""
    global _cached_songs, _cache_loaded
    try:
        parser = get_pvdb_parser()
        songs = parser.scan_and_parse()
        favorites = get_favorites_manager().get_all_favorites()
        _cached_songs = [SongResponse.from_song(song, favorites) for song in songs]
        _cache_loaded = True
        logger.info(f"Songs cache loaded: {len(_cached_songs)} songs")
        return _cached_songs
    except Exception as e:
        logger.error(f"Failed to load songs cache: {e}")
        _cached_songs = []
        _cache_loaded = True
        return _cached_songs


def get_cached_songs() -> list[SongResponse]:
    """Get cached songs, load if not already loaded."""
    if not _cache_loaded:
        return load_songs_cache()
    return _cached_songs


def get_songs_with_favorites() -> list[SongResponse]:
    """Get cached songs with current favorites applied."""
    global _cached_songs
    if not _cache_loaded:
        return load_songs_cache()
    # Refresh favorites status
    favorites = get_favorites_manager().get_all_favorites()
    for song in _cached_songs:
        song.isFavorite = song.id in favorites
    return _cached_songs


@router.get("", response_model=ApiResponse[SongListResponse])
async def get_songs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page", alias="pageSize"),
    search: Optional[str] = Query(None, description="Search query"),
    favorites: bool = Query(False, description="Filter to show only favorites"),
):
    """Get paginated songs from cache."""
    try:
        songs = get_songs_with_favorites()

        # Filter by favorites if requested
        if favorites:
            songs = [s for s in songs if s.isFavorite]

        # Filter by search if provided
        if search:
            search_lower = search.lower()
            filtered_songs = []
            for s in songs:
                # Search by ID (exact match)
                if str(s.id) == search:
                    filtered_songs.append(s)
                    continue
                # Search by Japanese name
                if search_lower in s.name.lower():
                    filtered_songs.append(s)
                    continue
                # Search by English name
                if s.nameEn and search_lower in s.nameEn.lower():
                    filtered_songs.append(s)
                    continue
            songs = filtered_songs

        total = len(songs)

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_songs = songs[start:end]

        return ApiResponse(
            success=True,
            data=SongListResponse(
                songs=paginated_songs,
                total=total,
                page=page,
                pageSize=page_size,
                totalPages=(total + page_size - 1) // page_size
            )
        )
    except Exception as e:
        logger.error(f"Failed to get songs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload", response_model=ApiResponse[SongListResponse])
async def reload_songs():
    """Reload songs from PVDB files into cache."""
    try:
        songs = load_songs_cache()
        return ApiResponse(
            success=True,
            data=SongListResponse(
                songs=songs[:20],  # Return first page for convenience
                total=len(songs),
                page=1,
                pageSize=20,
                totalPages=(len(songs) + 19) // 20
            )
        )
    except Exception as e:
        logger.error(f"Failed to reload songs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites", response_model=ApiResponse[list[int]])
async def get_favorites():
    """Get all favorite song IDs."""
    try:
        manager = get_favorites_manager()
        favorites = manager.get_all_favorites()
        return ApiResponse(
            success=True,
            data=sorted(list(favorites))
        )
    except Exception as e:
        logger.error(f"Failed to get favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{song_id}", response_model=ApiResponse[SongResponse])
async def get_song(song_id: int):
    """Get a specific song by ID."""
    try:
        songs = get_songs_with_favorites()  # 使用带收藏状态的函数
        song = next((s for s in songs if s.id == song_id), None)
        if song is None:
            raise HTTPException(status_code=404, detail=f"Song with ID {song_id} not found")
        return ApiResponse(
            success=True,
            data=song
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get song {song_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{song_id}/favorite", response_model=ApiResponse[dict])
async def toggle_favorite(song_id: int):
    """Toggle favorite status for a song."""
    try:
        manager = get_favorites_manager()
        is_favorite = manager.toggle_favorite(song_id)
        return ApiResponse(
            success=True,
            data={"isFavorite": is_favorite}
        )
    except Exception as e:
        logger.error(f"Failed to toggle favorite for song {song_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
