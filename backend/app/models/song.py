"""Song data models."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Set, List

from app.models.mod_info import ModInfo

class ChartStyle(Enum):
    """NC difficulty style types."""
    ARCADE = "ARCADE"
    CONSOLE = "CONSOLE"
    MIXED = "MIXED"

    @classmethod
    def from_string(cls, value: str) -> Optional["ChartStyle"]:
        """Parse ChartStyle from string (case-insensitive)."""
        if not value:
            return None
        try:
            return cls(value.upper())
        except ValueError:
            return None


class DifficultyType(Enum):
    """Difficulty types for songs."""
    EASY = 0
    NORMAL = 1
    HARD = 2
    EXTREME = 3
    EXTRA_EXTREME = 4
    RESERVED = 5

    @property
    def display_name(self) -> str:
        """Get the display name for the difficulty."""
        names = {
            DifficultyType.EASY: "EASY",
            DifficultyType.NORMAL: "NORMAL",
            DifficultyType.HARD: "HARD",
            DifficultyType.EXTREME: "EXTREME",
            DifficultyType.EXTRA_EXTREME: "EXTRA EXTREME",
            DifficultyType.RESERVED: "RESERVED",
        }
        return names.get(self, self.name)

    @property
    def short_name(self) -> str:
        """Get the short name for the difficulty."""
        names = {
            DifficultyType.EASY: "E",
            DifficultyType.NORMAL: "N",
            DifficultyType.HARD: "H",
            DifficultyType.EXTREME: "Ex",
            DifficultyType.EXTRA_EXTREME: "EX",
            DifficultyType.RESERVED: "R",
        }
        return names.get(self, self.name[0])


@dataclass
class ChartInfo:
    """Chart information with level and script path."""
    style: Optional[ChartStyle]
    type: DifficultyType
    level: float = 0.0  # 星级 1-20，支持小数如 6.5
    edition: int = 0
    script_file_name: Optional[str] = None
    is_extra: bool = False  # 是否为 EXTRA EXTREME
    is_original: bool = False  # 是否为原谱
    is_slide: bool = False  # 是否为滑动谱
    index: int = 0  # 同类型难度的索引，用于区分多个 EXTREME
    mod_id: int = 0 # 来源 Mod ID


@dataclass
class NcChartInfo:
    """NC database difficulty entry."""
    difficulty_type: DifficultyType  # "easy", "normal", "hard", "extreme", "ex_extreme"
    style: ChartStyle
    level: Optional[float] = None  # Parsed from PV_LV_WW_D
    script_file_name: Optional[str] = None


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

    def to_dict(self) -> dict:
        """Convert song to dictionary."""
        return {
            "id": self.id,
            "name": self.name,  # 日文原名
            "nameEn": self.name_en,
            "nameReading": self.name_reading,
            "difficulties": [d.value for d in self.difficulties],
            "difficultyNames": [d.display_name for d in self.difficulties],
            "difficultyDetails": [
                {
                    "type": d.type.value,
                    "name": d.type.display_name,
                    "level": d.level,
                    "edition": d.edition,
                    "scriptPath": d.script_file_name,
                    "isExtra": d.is_extra,
                    "isOriginal": d.is_original,
                    "isSlide": d.is_slide,
                    "index": d.index,
                }
                for d in self.chart_infos
            ],
            "hidden": self.hidden,
            "modInfos": [
                {
                    "id": m.id,
                    "name": m.name,
                    "path": m.path,
                    "enabled": m.enabled,
                    "author": m.author,
                    "version": m.version,
                } for m in self.mod_infos
            ],
            "modEnabled": self.mod_enabled,
            "isVanilla": self.is_vanilla,
            "bpm": self.bpm,
            "description": self.description,
            "attributes": self.attributes,
            # Song credits from songinfo
            "music": self.music,
            "arranger": self.arranger,
            "lyrics": self.lyrics,
            "guitarPlayer": self.guitar_player,
            "illustrator": self.illustrator,
            "manipulator": self.manipulator,
            "pvEditor": self.pv_editor,
        }

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


diff_type_mapping = {
        'easy': DifficultyType.EASY,
        'normal': DifficultyType.NORMAL,
        'hard': DifficultyType.HARD,
        'extreme': DifficultyType.EXTREME,
        'extra_extreme': DifficultyType.EXTRA_EXTREME,
        'ex_extreme': DifficultyType.EXTRA_EXTREME,
        'extraextreme': DifficultyType.EXTRA_EXTREME,
        'exextreme': DifficultyType.EXTRA_EXTREME,
    }

nc_diff_type_mapping = {
                'easy': DifficultyType.EASY,
                'normal': DifficultyType.NORMAL,
                'hard': DifficultyType.HARD,
                'extreme': DifficultyType.EXTREME,
                'ex_extreme': DifficultyType.EXTRA_EXTREME,
            }

def parse_difficulty_type(name: str):
    """Parse difficulty type name to enum."""
    return diff_type_mapping.get(name.lower())