"""Song data models."""
from dataclasses import dataclass, field
from typing import Optional, List

from app.models.chart import ChartInfo, NcChartInfo
from app.models.difficulty_type import DifficultyType
from app.models.mod_info import ModInfo


@dataclass
class Song:
    """Represents a Project DIVA song."""

    id: int
    name: str  # 日文原名 (优先)
    name_en: Optional[str] = None  # 英文名称
    name_reading: Optional[str] = None  # 读音/假名
    difficulties: list[DifficultyType] = field(default_factory=list)
    chart_infos: list[ChartInfo] = field(default_factory=list)
    hidden: bool = False

    # Optional metadata from PVDB
    bpm: Optional[str] = None
    description: Optional[str] = None

    # Song credits from songinfo
    music: Optional[str] = None  # 作曲家
    arranger: Optional[str] = None # 编曲家
    lyrics: Optional[str] = None  # 作词家
    guitar_player: Optional[str] = None  # 吉他手
    illustrator: Optional[str] = None  # 画师/插画师
    manipulator: Optional[str] = None  # 调教师
    pv_editor: Optional[str] = None  # PV编辑

    # Mod information
    mod_infos: list[ModInfo] = field(default_factory=list)  # 歌曲关联的所有 Mod 信息列表
    mod_enabled: bool = True  # Mod 是否启用（影响歌曲是否可用）
    is_vanilla: bool = False  # 是否为原版歌曲（来自 data/vanilla 目录）

    # 所有原始PVDB属性
    attributes: dict = field(default_factory=dict)

    def get_display_name(self) -> str:
        """Get the display name for the song.

        Priority: 日文原名 > 英文名称 > 读音 > ID
        """
        if self.name and self.name.strip():
            return self.name
        if self.name_en and self.name_en.strip():
            return self.name_en
        if self.name_reading and self.name_reading.strip():
            return self.name_reading
        return f"PV_{self.id:03d}"

    def has_difficulty(self, difficulty: DifficultyType) -> bool:
        """Check if song has the specified difficulty."""
        return difficulty in self.difficulties

    def get_difficulty_info(self, difficulty: DifficultyType) -> Optional[ChartInfo]:
        """Get detailed info for a specific difficulty."""
        for info in self.chart_infos:
            if info.type == difficulty:
                return info
        return None

    def get_highest_available_difficulty(self, preferred: DifficultyType) -> Optional[DifficultyType]:
        """
        Get the highest available difficulty up to the preferred one.
        Returns None if no difficulties are available.
        """
        if self.has_difficulty(preferred):
            return preferred

        # Search downwards from preferred difficulty
        for diff_value in range(preferred.value - 1, -1, -1):
            diff = DifficultyType(diff_value)
            if self.has_difficulty(diff):
                return diff

        return None

    def get_difficulty_level(self, difficulty: DifficultyType) -> float:
        """Get star level for a difficulty."""
        info = self.get_difficulty_info(difficulty)
        return info.level if info else 0.0


@dataclass
class NcSong:
    """NC database song entry."""
    song_id: int
    mod_info: ModInfo
    mod_id: int = 0
    chart_infos: List[NcChartInfo] = field(default_factory=list)
    source_file: Optional[str] = None
