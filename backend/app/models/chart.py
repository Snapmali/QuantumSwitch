from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.models.difficulty_type import DifficultyType


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


class ChartStyleValue:
    """双向 ChartStyle 映射，支持 style -> 内存值 和 内存值 -> style 的转换"""

    _STYLE_TO_VALUE = {
        ChartStyle.ARCADE: 0,
        ChartStyle.CONSOLE: 1,
        ChartStyle.MIXED: 2,
    }

    _VALUE_TO_STYLE = {v: k for k, v in _STYLE_TO_VALUE.items()}

    @classmethod
    def to_value(cls, style: ChartStyle) -> int:
        """ChartStyle -> 内存值 (默认返回 0)"""
        return cls._STYLE_TO_VALUE.get(style, 0)

    @classmethod
    def from_value(cls, value: int) -> ChartStyle:
        """内存值 -> ChartStyle (默认返回 ARCADE)"""
        return cls._VALUE_TO_STYLE.get(value, ChartStyle.ARCADE)