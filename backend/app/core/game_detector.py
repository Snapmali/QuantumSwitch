"""Game installation directory detection."""
import os
import platform
from pathlib import Path
from typing import Optional

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import winreg


def _get_steam_libraries() -> list[str]:
    """Get list of Steam library paths from registry."""
    if not IS_WINDOWS:
        return []

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path = winreg.QueryValueEx(key, "SteamPath")[0]

        libraries = [steam_path]
        vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")

        if os.path.exists(vdf_path):
            with open(vdf_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if '"path"' in line:
                        library_path = line.split('"')[3].replace("\\\\", "\\")
                        libraries.append(library_path)

        return libraries
    except Exception:
        return []


def _find_game_in_library(app_id: str, library_path: str) -> Optional[Path]:
    """Find game installation directory in a specific Steam library."""
    manifest_path = os.path.join(library_path, "steamapps", f"appmanifest_{app_id}.acf")

    if not os.path.exists(manifest_path):
        return None

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '"installdir"' in line:
                    install_dir = line.split('"')[3]
                    game_path = os.path.join(library_path, "steamapps", "common", install_dir)
                    return Path(game_path)
    except Exception:
        pass

    return None


def detect_game_path_from_steam(app_id: str) -> Optional[Path]:
    """Get game installation path from Steam registry (Windows only)."""
    if not IS_WINDOWS:
        return None

    libraries = _get_steam_libraries()

    for lib in libraries:
        game_path = _find_game_in_library(app_id, lib)
        if game_path:
            return game_path

    return None


def detect_game_directories(
    game_id: str,
    configured_mods_dir: Optional[Path],
    configured_game_dir: Optional[Path]
) -> tuple[Optional[Path], Optional[Path]]:
    """
    Detect game directories from config or registry.

    Priority:
    1. Use configured GAME_MODS_DIRECTORY if available
    2. Use configured GAME_DIRECTORY if available
    3. Auto-detect from Steam registry

    Returns:
        tuple of (game_directory, mods_directory)
    """
    game_dir: Optional[Path] = None
    mods_dir: Optional[Path] = None

    # Case 1: User configured GAME_MODS_DIRECTORY in .env
    if configured_mods_dir is not None:
        mods_dir = configured_mods_dir

        # Derive game_dir from mods_dir if not configured
        if configured_game_dir is None:
            game_dir = mods_dir.parent
        else:
            game_dir = configured_game_dir

        return game_dir, mods_dir

    # Case 2: User configured GAME_DIRECTORY in .env
    if configured_game_dir is not None:
        game_dir = configured_game_dir
        mods_dir = game_dir / "mods"
        return game_dir, mods_dir

    # Case 3: Auto-detect from Steam registry
    game_dir = detect_game_path_from_steam(game_id)
    if game_dir is not None:
        mods_dir = game_dir / "mods"

    return game_dir, mods_dir
