"""Pydantic schemas for API requests and responses."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, List, Generic, TypeVar

T = TypeVar("T")


class DifficultyDetail(BaseModel):
    """Detailed difficulty information."""
    model_config = ConfigDict(populate_by_name=True)

    type: int
    name: str
    level: float
    edition: int
    scriptPath: Optional[str] = None
    isExtra: bool = False
    isOriginal: bool = False
    isSlide: bool = False
    index: int = 0


class ModInfoResponse(BaseModel):
    """Response schema for Mod information."""
    model_config = ConfigDict(populate_by_name=True)

    name: str
    path: str
    enabled: bool
    author: Optional[str] = None
    version: Optional[str] = None


class SongResponse(BaseModel):
    """Response schema for a single song."""
    model_config = ConfigDict(populate_by_name=True)

    id: int
    sortId: int
    name: str  # 日文原名
    nameEn: Optional[str] = None
    nameReading: Optional[str] = None
    difficultyDetails: List[DifficultyDetail] = []
    hidden: bool = False
    modPath: Optional[str] = None
    modInfo: Optional[ModInfoResponse] = None  # Mod信息（单个，向后兼容）
    modInfos: List[ModInfoResponse] = []  # 所有关联的Mod信息列表
    modEnabled: bool = True  # Mod是否启用
    isVanilla: bool = False  # 是否为原版歌曲
    bpm: Optional[str] = None
    description: Optional[str] = None
    attributes: dict = {}

    # Song credits from songinfo
    music: Optional[str] = None  # 作曲家
    arranger: Optional[str] = None # 编曲家
    lyrics: Optional[str] = None  # 作词家
    guitarPlayer: Optional[str] = None  # 吉他手
    illustrator: Optional[str] = None  # 画师/插画师
    manipulator: Optional[str] = None  # 调教师
    pvEditor: Optional[str] = None  # PV编辑

    @classmethod
    def from_song(cls, song) -> "SongResponse":
        """Create SongResponse from a Song dataclass."""
        return cls(
            id=song.id,
            sortId=song.sort_id,
            name=song.name,
            nameEn=song.name_en,
            nameReading=song.name_reading,
            difficultyDetails=[
                DifficultyDetail(
                    type=d.type.value,
                    name=d.type.display_name,
                    level=d.level,
                    edition=d.edition,
                    scriptPath=d.script_path,
                    isExtra=d.is_extra,
                    isOriginal=d.is_original,
                    isSlide=d.is_slide,
                    index=d.index,
                )
                for d in song.difficulty_details
            ],
            hidden=song.hidden,
            modPath=song.mod_path,
            modInfo=ModInfoResponse(
                name=song.mod_info.name,
                path=song.mod_info.path,
                enabled=song.mod_info.enabled,
                author=song.mod_info.author,
                version=song.mod_info.version,
            ) if song.mod_info else None,
            modInfos=[
                ModInfoResponse(
                    name=m.name,
                    path=m.path,
                    enabled=m.enabled,
                    author=m.author,
                    version=m.version,
                ) for m in song.mod_infos
            ],
            # For multiple mods: if any mod is enabled, modEnabled is True
            # This ensures song is usable if at least one mod is enabled
            modEnabled=any(m.enabled for m in song.mod_infos) if song.mod_infos else song.mod_enabled,
            isVanilla=song.is_vanilla,
            bpm=song.bpm,
            description=song.description,
            attributes=song.attributes,
            # Song credits from songinfo
            music=song.music,
            arranger=song.arranger,
            lyrics=song.lyrics,
            guitarPlayer=song.guitar_player,
            illustrator=song.illustrator,
            manipulator=song.manipulator,
            pvEditor=song.pv_editor,
        )


class SongListResponse(BaseModel):
    """Response schema for song list."""
    model_config = ConfigDict(populate_by_name=True)

    songs: List[SongResponse]
    total: int
    page: int = 1
    pageSize: int = Field(default=20)
    totalPages: int = Field(default=1)
    hiddenCount: int = Field(default=0)


class GameStatusResponse(BaseModel):
    """Response schema for game status."""
    model_config = ConfigDict(populate_by_name=True)

    running: bool
    processId: Optional[int] = None
    currentSongId: Optional[int] = None
    currentSortId: Optional[int] = None
    currentDifficulty: Optional[int] = None
    currentDifficultyName: Optional[str] = None
    gameState: Optional[int] = None
    edenVersion: bool = False
    edenOffset: int = 0


class SwitchSongRequest(BaseModel):
    """Request schema for switching songs."""
    model_config = ConfigDict(populate_by_name=True)

    songId: int = Field(..., description="The song ID to switch to")
    difficulty: int = Field(default=2, ge=0, le=5, description="Difficulty level (0-5)")
    force: bool = Field(default=False, description="Force switch even if game state is invalid")


class SwitchSongResponse(BaseModel):
    """Response schema for song switch operation."""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    message: str
    actualDifficulty: Optional[int] = None
    actualDifficultyName: Optional[str] = None
    requiresDelayedUpdate: bool = False


class ApiResponse(BaseModel, Generic[T]):
    """Generic API response wrapper."""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None


class ConfigResponse(BaseModel):
    """Response schema for configuration."""
    model_config = ConfigDict(populate_by_name=True)

    appName: str = Field(default="Quantum Switch")
    appVersion: str
    gameProcessName: str
    gameRunning: bool
    gameBaseAddress: Optional[str] = None
    edenOffsetApplied: Optional[bool] = None
    pvdbFiles: List[str] = Field(default_factory=list)


class CurrentSongResponse(BaseModel):
    """Response schema for current song."""
    model_config = ConfigDict(populate_by_name=True)

    songId: Optional[int] = None
    sortId: Optional[int] = None
    difficulty: Optional[int] = None
    difficultyName: Optional[str] = None
    songName: Optional[str] = None
