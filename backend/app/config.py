"""Configuration management for the song selector."""
import sys
import os
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional
from enum import Enum


class DllEnum(str, Enum):
    """预定义的 DLL 名称配置"""
    NEW_CLASSICS = "NewClassics.dll"
    DIVA_MOD_LOADER = "dinput8.dll"


class DllPattern(Enum):
    CHART_STYLE_PATTERN = (
        DllEnum.NEW_CLASSICS,
        b"\x74\x0B\x8B\x88....\x83\xF9\x03\x75\x02\x33\xC9\x89\x0D....\x40\x0F\xB6\xC7\x48\x8B"
    )

    def __init__(self, dll: str, pattern: bytes):
        self.dll: str = dll
        self.pattern: bytes = pattern


class DllPatternOffset(Enum):
    CHART_STYLE_OFFSET = (DllPattern.CHART_STYLE_PATTERN, 17)

    def __init__(self, dll_pattern: DllPattern, offset: int):
        self.dll_pattern: DllPattern = dll_pattern
        self.offset: int = offset


# Detect runtime mode
IS_FROZEN = getattr(sys, 'frozen', False)

if IS_FROZEN:
    # PyInstaller mode: exe directory is the working directory
    WORK_DIR = Path(os.environ.get('DIVA_SELECTOR_WORK_DIR', Path(sys.executable).parent))
    DATA_DIR = WORK_DIR / "data"
    CONFIG_DIR = WORK_DIR / "config"
else:
    # Development mode
    WORK_DIR = Path(__file__).parent.parent
    DATA_DIR = WORK_DIR / "data"
    CONFIG_DIR = WORK_DIR


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Quantum Switch"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Game settings
    GAME_ID: str = "1761390"
    GAME_PROCESS_NAME: str = "DivaMegaMix.exe"
    GAME_DIRECTORY: Optional[Path] = None
    GAME_MODS_DIRECTORY: Optional[Path] = None

    # Memory addresses (base addresses, may need Eden offset)
    CURR_PVID_BASE_PTR_ADDR: int = 0xCC5EF18
    CURR_PVID_SONG_SELECTION_OFFSET_PTR_ADDR: int = 0x6EFE8C
    CURR_PVID_SONG_SELECTION_OFFSET_PTR_OFFSET: int = 0x9C8

    # Control addresses (not affected by Eden offset)
    CHANGE_SONG_SELECT_ADDR: int = 0xCC61098
    START_CHANGE_ADDR: int = 0xCC610A0

    CONSOLE_MODE_CHANGE_ADDR: int = 0x114F80
    """The offset of NewClassics.dll ver 1.2.0, used to set console mode"""

    # Data addresses (maybe affected by Eden offset)
    LAST_SELECT_PVID_ADDR: int = 0x12B6350
    LAST_SELECT_SORT_ADDR: int = 0x12B6354
    LAST_SELECT_DIFF_LEVEL_ADDR: int = 0x12B635C
    LAST_SELECT_DIFF_TYPE_ADDR: int = 0x12B634C

    CURR_PVID_INGAME_ADDR: int = 0x16E2BB0

    # Eden offset configuration
    # Detection: Read LAST_SELECT_PVID_ADDR (0x12B6350), if value is 0, apply offset 0x105F460
    EDEN_OFFSET: int = 0x105F460

    # PVDB file names
    PVDB_FILES: list[str] = ["mod_pv_db.txt", "mdata_pv_db.txt"]

    # DLL 白名单 - 仅缓存这些 DLL
    CACHED_DLLS: list[str] = [
        DllEnum.NEW_CLASSICS,
        DllEnum.DIVA_MOD_LOADER,
    ]

    CACHED_PATTERN: list[DllPattern] = [
        DllPattern.CHART_STYLE_PATTERN
    ]

    class Config:
        env_file = CONFIG_DIR / ".env" if IS_FROZEN else ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
