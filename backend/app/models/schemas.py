"""Pydantic schemas for API requests and responses."""
from pathlib import Path

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, List, Generic, TypeVar

from app.models.chart import ChartStyle, ChartInfo
from app.models.difficulty_type import DifficultyType
from app.models.game_state import GameState
from app.models.song import Song
from app.utils.logger import logger

T = TypeVar("T")


class ChartInfoDetail(BaseModel):
    """Individual chart information from a specific mod."""
    model_config = ConfigDict(populate_by_name=True)

    level: float                  # Star rating
    edition: int = 0              # Edition number
    scriptPath: Optional[str] = None
    isExtra: bool = False
    isOriginal: bool = False
    isSlide: bool = False
    modId: int                    # Source mod ID
    modName: Optional[str] = None # Source mod name
    enabled: bool = True          # Whether this specific chart is enabled


class DifficultyTypeDetail(BaseModel):
    """Difficulty type containing all its charts across mods."""
    model_config = ConfigDict(populate_by_name=True)

    type: int                     # 0-4 (EASY to EXTRA_EXTREME)
    name: str                     # "EASY", "NORMAL", etc.
    shortName: str                # "E", "N", "H", "Ex", "EX"
    chartInfos: List[ChartInfoDetail] = []  # Charts for this difficulty
    hasEnabledCharts: bool = False  # Whether any chart in this difficulty is enabled


class ChartStyleDetail(BaseModel):
    """Chart style (ARCADE/CONSOLE/Mixed) containing all difficulties."""
    model_config = ConfigDict(populate_by_name=True)

    style: str                    # "ARCADE", "CONSOLE", "MIXED"
    displayName: str              # "街机", "主机", "混合"
    difficulties: List[DifficultyTypeDetail] = []
    hasEnabledDifficulties: bool = False


class DifficultyDetail(BaseModel):
    """[DEPRECATED] Old flat difficulty structure - kept for reference."""
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
    modIds: List[int] = []   # 来源 Mod ID 列表
    enabled: bool = True     # 难度是否可用


class ModInfoResponse(BaseModel):
    """Response schema for Mod information."""
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    path: Optional[Path]
    enabled: bool
    author: Optional[str] = None
    version: Optional[str] = None


class SongResponse(BaseModel):
    """Response schema for a single song."""
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str  # 日文原名
    nameEn: Optional[str] = None
    nameReading: Optional[str] = None
    difficultyDetails: List[ChartStyleDetail] = []  # 新的层级结构：ChartStyle -> DifficultyType -> ChartInfo
    hidden: bool = False
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

    isFavorite: bool = False  # 是否已收藏

    @classmethod
    def from_song(cls, song: Song, favorites: set[int] | None = None) -> "SongResponse":
        """Create SongResponse from a Song dataclass with hierarchical difficulty structure."""
        # Build Mod lookup: mod_id -> ModInfo
        mod_map = {m.id: m for m in song.mod_infos}

        # Group chart_infos by ChartStyle and then by DifficultyType
        # Structure: {ChartStyle: {DifficultyType: [ChartInfo]}}
        style_groups: dict[ChartStyle, dict[DifficultyType, list[ChartInfo]]] = {}

        for chart in song.chart_infos:
            style = chart.style if chart.style else ChartStyle.MIXED
            diff_type = chart.type

            if style not in style_groups:
                style_groups[style] = {}
            if diff_type not in style_groups[style]:
                style_groups[style][diff_type] = []

            style_groups[style][diff_type].append(chart)

        # Build hierarchical difficulty details
        difficulty_details = []

        # Define style order and display names
        style_order = [ChartStyle.ARCADE, ChartStyle.CONSOLE, ChartStyle.MIXED]
        style_display_names = {
            ChartStyle.ARCADE: "Arcade",
            ChartStyle.CONSOLE: "Console",
            ChartStyle.MIXED: "Mixed",
        }

        # Define difficulty order
        diff_order = [
            DifficultyType.EASY,
            DifficultyType.NORMAL,
            DifficultyType.HARD,
            DifficultyType.EXTREME,
            DifficultyType.EXTRA_EXTREME,
        ]

        for style in style_order:
            if style not in style_groups:
                continue

            style_difficulties = []
            style_has_enabled = False

            for diff_type in diff_order:
                if diff_type not in style_groups[style]:
                    continue

                charts = style_groups[style][diff_type]
                chart_infos = []
                diff_has_enabled = False

                for chart in charts:
                    # Determine if chart is enabled
                    if chart.is_original:
                        is_enabled = True
                    else:
                        mod = mod_map.get(chart.mod_id)
                        is_enabled = mod.enabled if mod else song.is_vanilla

                    if is_enabled:
                        diff_has_enabled = True
                        style_has_enabled = True

                    # Get mod name
                    mod = mod_map.get(chart.mod_id)
                    mod_name = mod.name if mod else None

                    try:
                        chart_infos.append(
                            ChartInfoDetail(
                                level=chart.level,
                                edition=chart.edition,
                                scriptPath=chart.script_file_name,
                                isExtra=chart.is_extra,
                                isOriginal=chart.is_original,
                                isSlide=chart.is_slide,
                                modId=chart.mod_id,
                                modName=mod_name,
                                enabled=is_enabled,
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to parse chart info: song_id={song.id} diff={chart.type} "
                                     f"style={chart.style.name if chart.style else None} mod_name='{mod_name}', "
                                     f"with exception: {e}")

                # Sort chart_infos: enabled first, then by level
                chart_infos.sort(key=lambda c: (-c.enabled, -c.level))

                style_difficulties.append(
                    DifficultyTypeDetail(
                        type=diff_type.value,
                        name=diff_type.display_name,
                        shortName=diff_type.short_name,
                        chartInfos=chart_infos,
                        hasEnabledCharts=diff_has_enabled,
                    )
                )

            if style_difficulties:
                difficulty_details.append(
                    ChartStyleDetail(
                        style=style.value,
                        displayName=style_display_names.get(style, style.value),
                        difficulties=style_difficulties,
                        hasEnabledDifficulties=style_has_enabled,
                    )
                )

        return cls(
            id=song.id,
            name=song.name,
            nameEn=song.name_en,
            nameReading=song.name_reading,
            difficultyDetails=difficulty_details,
            hidden=song.hidden,
            modInfos=[
                ModInfoResponse(
                    id=m.id,
                    name=m.name,
                    path=m.path,
                    enabled=m.enabled,
                    author=m.author,
                    version=m.version,
                ) for m in song.mod_infos
            ],
            # For multiple mods: if any mod is enabled, modEnabled is True
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
            isFavorite=song.id in favorites if favorites else False,
        )


class SongAlias(BaseModel):
    """Song alias entry."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    alias: str
    songName: str


class SongAliasMatchItem(BaseModel):
    """Matched alias item for search results."""
    model_config = ConfigDict(populate_by_name=True)

    alias: str
    songName: str


class ModInfoSearchItem(BaseModel):
    """Mod search result item."""
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    path: Optional[str] = None
    enabled: bool = True
    author: Optional[str] = None
    version: Optional[str] = None
    songCount: int = Field(default=0, alias="songCount")  # Number of songs in this mod


class CreateAliasRequest(BaseModel):
    """Request schema for creating an alias."""
    model_config = ConfigDict(populate_by_name=True)

    alias: str = Field(..., description="The alias text")
    songName: str = Field(..., description="The actual song name")


class UpdateAliasRequest(BaseModel):
    """Request schema for updating an alias."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="The alias ID to update")
    alias: Optional[str] = Field(None, description="New alias text")
    songName: Optional[str] = Field(None, description="New song name")


class ToggleFavoriteRequest(BaseModel):
    """Request schema for toggling favorite status."""
    model_config = ConfigDict(populate_by_name=True)

    songId: int = Field(..., description="The song ID to toggle favorite status")


class SongListResponse(BaseModel):
    """Response schema for song list."""
    model_config = ConfigDict(populate_by_name=True)

    songs: List[SongResponse]
    total: int
    page: int = 1
    pageSize: int = Field(default=20)
    totalPages: int = Field(default=1)
    hiddenCount: int = Field(default=0)
    matchedAliases: List[SongAliasMatchItem] = Field(default_factory=list)


class CurrentSongDifficultyInfo(BaseModel):
    """当前选择歌曲的难度信息"""
    model_config = ConfigDict(populate_by_name=True)

    name: str  # 难度名称，如 "EASY", "NORMAL" 等
    enabled: bool = True  # 是否启用


class CurrentSongInfo(BaseModel):
    """当前选择歌曲的基本信息"""
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    nameEn: Optional[str] = None
    difficulties: List[CurrentSongDifficultyInfo] = []  # 难度信息列表


class GameStatusResponse(BaseModel):
    """Response schema for game status."""
    model_config = ConfigDict(populate_by_name=True)

    running: bool
    processId: Optional[int] = None
    currentSongId: Optional[int] = None
    gameState: Optional[str] = None
    currentSongInfo: Optional[CurrentSongInfo] = None  # 新增：当前歌曲信息
    currentChartStyle: Optional[str] = None  # 新增：当前 ChartStyle (ARCADE/CONSOLE/MIXED)
    isIngame: bool = False  # 新增：是否正在游玩中


class SwitchSongRequest(BaseModel):
    """Request schema for switching songs."""
    model_config = ConfigDict(populate_by_name=True)

    songId: int = Field(..., description="The song ID to switch to")
    difficulty: int = Field(default=2, ge=0, le=5, description="Difficulty level (0-5)")
    style: str = Field(default="ARCADE", description="Chart style (ARCADE, CONSOLE, MIXED)")
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
