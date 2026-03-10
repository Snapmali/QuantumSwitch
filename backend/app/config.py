"""Configuration management for the song selector."""
import sys
import os
import platform
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

# Windows-specific imports
if platform.system() == "Windows":
    import winreg

IS_WINDOWS = platform.system() == "Windows"


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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 延迟初始化 GAME_MODS_DIRECTORY，以便在实例化后调用方法
        game_path = self.get_game_path(self.GAME_ID)
        if game_path:
            self.GAME_MODS_DIRECTORY = Path(game_path) / "mods"

    def get_game_path(self, app_id: str) -> str | None:
        """Get game installation path from Steam registry (Windows only)."""
        # 非 Windows 系统返回 None
        if not IS_WINDOWS:
            return None
        try:
            # 1. 从注册表获取 Steam 安装路径
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            steam_path = winreg.QueryValueEx(key, "SteamPath")[0]

            # 2. 读取库配置文件
            vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")

            # 3. 简单的路径搜索逻辑 (实际建议使用 vdf 解析库)
            libraries = [steam_path]
            with open(vdf_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if '"path"' in line:
                        libraries.append(line.split('"')[3].replace("\\\\", "\\"))

            # 4. 在各个库中寻找目标 AppID
            for lib in libraries:
                manifest_path = os.path.join(lib, "steamapps", f"appmanifest_{app_id}.acf")
                if os.path.exists(manifest_path):
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if '"installdir"' in line:
                                install_dir = line.split('"')[3]
                                return os.path.join(lib, "steamapps", "common", install_dir)
        except Exception:
            pass
        return None

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
    GAME_MODS_DIRECTORY: Optional[Path] = None

    # Memory addresses (base addresses, may need Eden offset)
    # Control addresses (not affected by Eden offset)
    CHANGE_SONG_SELECT_ADDR: int = 0xCC61098
    START_CHANGE_ADDR: int = 0xCC610A0

    # Data addresses (maybe affected by Eden offset)
    LAST_SELECT_PVID_ADDR: int = 0x12B6350
    LAST_SELECT_SORT_ADDR: int = 0x12B6354
    LAST_SELECT_DIFF_LEVEL_ADDR: int = 0x12B635C
    LAST_SELECT_DIFF_TYPE_ADDR: int = 0x12B634C

    # Eden offset configuration
    # Detection: Read LAST_SELECT_PVID_ADDR (0x12B6350), if value is 0, apply offset 0x105F460
    EDEN_OFFSET: int = 0x105F460

    # PVDB file names
    PVDB_FILES: list[str] = ["mod_pv_db.txt", "mdata_pv_db.txt"]

    class Config:
        env_file = CONFIG_DIR / ".env" if IS_FROZEN else ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
