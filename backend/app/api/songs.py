"""Song-related API endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..core.bootstrap import get_pvdb_parser, get_favorites_manager, get_alias_manager
from ..models import (
    SongResponse,
    SongListResponse,
    SongAlias,
    SongAliasMatchItem,
    CreateAliasRequest,
    UpdateAliasRequest,
    ToggleFavoriteRequest,
    ApiResponse,
    ModInfoSearchItem,
)
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
    search_mode: str = Query("song", description="Search mode: 'song' or 'mod'", alias="searchMode"),
    mod_id: Optional[int] = Query(None, description="Filter by mod ID", alias="modId"),
):
    """Get paginated songs from cache."""
    try:
        songs = get_songs_with_favorites()

        # Filter by favorites if requested
        if favorites:
            songs = [s for s in songs if s.isFavorite]

        # Filter by mod_id if provided
        if mod_id is not None:
            songs = [s for s in songs if any(m.id == mod_id for m in s.modInfos)]

        # Search for matched aliases (only in song mode, and even if search is empty, return empty list)
        matched_aliases: list[SongAliasMatchItem] = []
        if search and search_mode == "song":
            alias_manager = get_alias_manager()
            alias_matches = alias_manager.search_aliases(search, limit=10)
            matched_aliases = [
                SongAliasMatchItem(
                    alias=a.alias,
                    songName=a.songName
                ) for a in alias_matches
            ]

            # Also filter songs by search
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
                totalPages=(total + page_size - 1) // page_size,
                matchedAliases=matched_aliases
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
                totalPages=(len(songs) + 19) // 20,
                matchedAliases=[]
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


# ==================== Alias Endpoints ====================

@router.get("/aliases", response_model=ApiResponse[list[SongAlias]])
async def get_all_aliases():
    """Get all song aliases."""
    try:
        manager = get_alias_manager()
        aliases = manager.get_all_aliases()
        return ApiResponse(
            success=True,
            data=[
                SongAlias(
                    id=a.id,
                    alias=a.alias,
                    songName=a.songName
                ) for a in aliases
            ]
        )
    except Exception as e:
        logger.error(f"Failed to get aliases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/aliases", response_model=ApiResponse[SongAlias])
async def create_alias(request: CreateAliasRequest):
    """Create a new song alias."""
    try:
        manager = get_alias_manager()

        alias_obj = manager.create_alias(
            alias=request.alias,
            song_name=request.songName
        )

        if alias_obj is None:
            raise HTTPException(status_code=500, detail="Failed to create alias")

        return ApiResponse(
            success=True,
            data=SongAlias(
                id=alias_obj.id,
                alias=alias_obj.alias,
                songName=alias_obj.songName
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create alias: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aliases/search", response_model=ApiResponse[list[SongAliasMatchItem]])
async def search_aliases(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """Search for aliases using fuzzy matching."""
    try:
        manager = get_alias_manager()
        matches = manager.search_aliases(query, limit=limit)

        return ApiResponse(
            success=True,
            data=[
                SongAliasMatchItem(
                    alias=a.alias,
                    songName=a.songName
                ) for a in matches
            ]
        )
    except Exception as e:
        logger.error(f"Failed to search aliases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/aliases", response_model=ApiResponse[SongAlias])
async def update_alias(request: UpdateAliasRequest):
    """Update an existing song alias."""
    try:
        manager = get_alias_manager()

        alias_obj = manager.update_alias(
            alias_id=request.id,
            alias=request.alias,
            song_name=request.songName
        )

        if alias_obj is None:
            raise HTTPException(status_code=404, detail=f"Alias with ID {request.id} not found")

        return ApiResponse(
            success=True,
            data=SongAlias(
                id=alias_obj.id,
                alias=alias_obj.alias,
                songName=alias_obj.songName
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update alias: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/aliases", response_model=ApiResponse[dict])
async def delete_alias(alias_id: str = Query(..., description="The alias ID to delete")):
    """Delete a song alias."""
    try:
        manager = get_alias_manager()
        success = manager.delete_alias(alias_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Alias with ID {alias_id} not found")

        return ApiResponse(
            success=True,
            data={"deleted": True}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete alias: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detail", response_model=ApiResponse[SongResponse])
async def get_song(song_id: int = Query(..., description="The song ID to get details for")):
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


@router.post("/favorite", response_model=ApiResponse[dict])
async def toggle_favorite(request: ToggleFavoriteRequest):
    """Toggle favorite status for a song."""
    try:
        manager = get_favorites_manager()
        is_favorite = manager.toggle_favorite(request.songId)
        return ApiResponse(
            success=True,
            data={"isFavorite": is_favorite}
        )
    except Exception as e:
        logger.error(f"Failed to toggle favorite for song {request.songId}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Mod Search Endpoints ====================

@router.get("/mods/search", response_model=ApiResponse[list[ModInfoSearchItem]])
async def search_mods(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """Search mods by name using fuzzy matching."""
    try:
        songs = get_cached_songs()
        query_lower = query.lower()

        # Collect all mods with matching counts
        mod_map: dict[int, ModInfoSearchItem] = {}
        mod_song_counts: dict[int, int] = {}

        for song in songs:
            for mod in song.modInfos:
                # Check if mod name matches query
                if query_lower in mod.name.lower():
                    if mod.id not in mod_map:
                        mod_map[mod.id] = ModInfoSearchItem(
                            id=mod.id,
                            name=mod.name,
                            path=str(mod.path) if mod.path else None,
                            enabled=mod.enabled,
                            author=mod.author,
                            version=mod.version,
                            songCount=0
                        )
                        mod_song_counts[mod.id] = 0
                    mod_song_counts[mod.id] += 1

        # Update song counts and convert to list
        result = []
        for mod_id, mod_item in mod_map.items():
            mod_item.songCount = mod_song_counts[mod_id]
            result.append(mod_item)

        # Sort by relevance: enabled first, then by song count (descending)
        result.sort(key=lambda m: (-m.enabled, -m.songCount, m.name.lower()))

        # Apply limit
        result = result[:limit]

        return ApiResponse(
            success=True,
            data=result
        )
    except Exception as e:
        logger.error(f"Failed to search mods: {e}")
        raise HTTPException(status_code=500, detail=str(e))
