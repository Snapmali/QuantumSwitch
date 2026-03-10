"""Song data models."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.models.mod_info import ModInfo


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
class DifficultyInfo:
    """Difficulty information with level and script path."""
    type: DifficultyType
    level: float = 0.0  # 星级 1-20，支持小数如 6.5
    edition: int = 0
    script_path: Optional[str] = None
    is_extra: bool = False  # 是否为 EXTRA EXTREME
    is_original: bool = False  # 是否为原谱
    is_slide: bool = False  # 是否为滑动谱
    index: int = 0  # 同类型难度的索引，用于区分多个 EXTREME


@dataclass
class Song:
    """Represents a Project DIVA song."""

    id: int
    sort_id: int
    name: str  # 日文原名 (优先)
    name_en: Optional[str] = None  # 英文名称
    name_reading: Optional[str] = None  # 读音/假名
    difficulties: list[DifficultyType] = field(default_factory=list)
    difficulty_details: list[DifficultyInfo] = field(default_factory=list)
    hidden: bool = False
    source_file: Optional[str] = None
    mod_path: Optional[str] = None  # 所属Mod路径

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
    mod_info: Optional[ModInfo] = None  # 歌曲来源 Mod 信息（单个，用于向后兼容）
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

    def get_difficulty_info(self, difficulty: DifficultyType) -> Optional[DifficultyInfo]:
        """Get detailed info for a specific difficulty."""
        for info in self.difficulty_details:
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
            "sortId": self.sort_id,
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
                    "scriptPath": d.script_path,
                    "isExtra": d.is_extra,
                    "isOriginal": d.is_original,
                    "isSlide": d.is_slide,
                    "index": d.index,
                }
                for d in self.difficulty_details
            ],
            "hidden": self.hidden,
            "modPath": self.mod_path,
            "modInfo": {
                "name": self.mod_info.name,
                "path": self.mod_info.path,
                "enabled": self.mod_info.enabled,
                "author": self.mod_info.author,
                "version": self.mod_info.version,
            } if self.mod_info else None,
            "modInfos": [
                {
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
