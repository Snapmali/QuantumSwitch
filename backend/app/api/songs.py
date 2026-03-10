"""Song-related API endpoints."""
import traceback
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from ..models import (
    SongResponse,
    SongListResponse,
    ApiResponse,
)
from ..core.bootstrap import get_pvdb_parser
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
        _cached_songs = [SongResponse.from_song(song) for song in songs]
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


@router.get("", response_model=ApiResponse[SongListResponse])
async def get_all_songs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page", alias="pageSize"),
    search: Optional[str] = Query(None, description="Search query"),
):
    """Get paginated songs from cache."""
    try:
        songs = get_cached_songs()

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


@router.get("/search", response_model=ApiResponse[SongListResponse])
async def search_songs(
    q: str = Query(..., description="Search query"),
    difficulty: Optional[int] = Query(None, description="Filter by difficulty (0-5)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page", alias="pageSize"),
):
    """Search songs by name or PV ID with pagination."""
    try:
        songs = get_cached_songs()
        results = []
        query_lower = q.lower()

        for song in songs:
            # Search by ID
            if q.isdigit() and song.id == int(q):
                results.append(song)
                continue

            # Search by name
            if query_lower in song.name.lower():
                if difficulty is not None:
                    if any(d.type == difficulty for d in song.difficultyDetails):
                        results.append(song)
                else:
                    results.append(song)

        total = len(results)

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results[start:end]

        return ApiResponse(
            success=True,
            data=SongListResponse(
                songs=paginated_results,
                total=total,
                page=page,
                pageSize=page_size,
                totalPages=(total + page_size - 1) // page_size
            )
        )
    except Exception as e:
        logger.error(f"Failed to search songs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{song_id}", response_model=ApiResponse[SongResponse])
async def get_song(song_id: int):
    """Get a specific song by ID."""
    try:
        songs = get_cached_songs()
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
