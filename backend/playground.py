"""Playground test file for memory operations and song switching.

This file provides:
1. Periodic memory status printing via print_status
2. Interactive song switching via user input
"""
import threading
import time
from pathlib import Path
from typing import Optional

from app.config import settings, DllEnum
from app.core import SongSelector, MemoryOperator, ProcessManager
from app.core.bootstrap import _init_game_directories
from app.models import ChartStyle
from app.models.song import Song, DifficultyType
from app.utils.logger import logger

# Global instances
_pm: Optional[ProcessManager] = None
_mem: Optional[MemoryOperator] = None
_song_selector: Optional[SongSelector] = None

# Status log file for external monitoring
STATUS_LOG_FILE: Optional[Path] = None


DIFFICULTY_MAP = {
    "0": DifficultyType.EASY,
    "1": DifficultyType.NORMAL,
    "2": DifficultyType.HARD,
    "3": DifficultyType.EXTREME,
    "4": DifficultyType.EXTRA_EXTREME,
    "5": DifficultyType.RESERVED,
    "e": DifficultyType.EASY,
    "n": DifficultyType.NORMAL,
    "h": DifficultyType.HARD,
    "ex": DifficultyType.EXTREME,
    "exex": DifficultyType.EXTRA_EXTREME,
    "easy": DifficultyType.EASY,
    "normal": DifficultyType.NORMAL,
    "hard": DifficultyType.HARD,
    "extreme": DifficultyType.EXTREME,
    "extra_extreme": DifficultyType.EXTRA_EXTREME,
    "ex extreme": DifficultyType.EXTRA_EXTREME,
}

STYLE_MAP = {
    "0": ChartStyle.ARCADE,
    "1": ChartStyle.CONSOLE,
    "2": ChartStyle.MIXED,
    "a": ChartStyle.ARCADE,
    "c": ChartStyle.CONSOLE,
    "m": ChartStyle.MIXED,
    "arcade": ChartStyle.ARCADE,
    "console": ChartStyle.CONSOLE,
    "mixed": ChartStyle.MIXED,
}


def init():
    """Initialize global instances and attach to game process."""
    global _pm, _mem, _song_selector, STATUS_LOG_FILE

    logger.info("Initializing playground...")

    # Initialize status log file
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    STATUS_LOG_FILE = log_dir / "status.log"
    logger.info(f"Status log file: {STATUS_LOG_FILE}")

    _pm = ProcessManager()
    _mem = MemoryOperator(_pm)
    _song_selector = SongSelector(_mem)
    _init_game_directories()

    # Attach to game process
    if not _pm.attach():
        logger.error("Failed to attach to game process. Make sure DivaMegaMix.exe is running.")
        return False

    logger.info("Successfully attached to game process")
    return True


def print_status():
    """Print current memory status information to status log file only."""
    if _mem is None:
        return

    try:
        # Read key memory addresses
        menu = _mem.read_int(settings.CHANGE_SONG_SELECT_ADDR)
        game_mode = _mem.read_int(settings.CONSOLE_MODE_CHANGE_ADDR, dll=DllEnum.NEW_CLASSICS)
        pvid = _mem.read_int(settings.LAST_SELECT_PVID_ADDR, apply_eden=True)
        sort_id = _mem.read_int(settings.LAST_SELECT_SORT_ADDR, apply_eden=True)
        diff_type = _mem.read_int(settings.LAST_SELECT_DIFF_TYPE_ADDR, apply_eden=True)
        diff_level = _mem.read_int(settings.LAST_SELECT_DIFF_LEVEL_ADDR, apply_eden=True)

        status_msg = (
            f"[Memory Status] menu={menu}, game_mode={game_mode}, "
            f"pvid={pvid}, sort_id={sort_id}, diff_type={diff_type}, diff_level={diff_level}"
        )

        # Write to status log file for external monitoring (no console output)
        if STATUS_LOG_FILE:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(STATUS_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{timestamp} | {status_msg}\n")
            except Exception:
                pass  # Silently fail if file cannot be written
    except Exception:
        pass  # Silently fail if memory read fails


def status_printer_loop(interval: float = 2.0):
    """Background thread that periodically prints memory status.

    Args:
        interval: Seconds between status prints (default: 2.0)
    """
    logger.info(f"Status printer started (interval: {interval}s)")
    while True:
        print_status()
        time.sleep(interval)


def parse_difficulty(diff_input: str) -> Optional[DifficultyType]:
    """Parse difficulty from user input string.

    Args:
        diff_input: User input string (e.g., "0", "e", "hard", "EX")

    Returns:
        DifficultyType or None if invalid
    """
    diff_lower = diff_input.strip().lower()
    return DIFFICULTY_MAP.get(diff_lower)

def parse_style(style_input: str) -> Optional[ChartStyle]:
    """Parse chart style from user input string."""
    style_lower = style_input.strip().lower()
    return STYLE_MAP.get(style_lower)


def create_test_song(song_id: int) -> Song:
    """Create a minimal Song object for testing.

    Args:
        song_id: The PVID of the song

    Returns:
        Song object with all difficulties enabled
    """
    return Song(
        id=song_id,
        name=f"Test Song {song_id}",
        difficulties=list(DifficultyType),
    )


def switch_song_interactive():
    """Interactive song switching via user input."""
    if _song_selector is None:
        logger.error("Song selector not initialized")
        return

    print("\n" + "=" * 50)
    print("Song Switch Mode")
    print("=" * 50)
    print("Enter song details (or 'q' to cancel):")

    # Get song ID
    song_id_input = input("Song ID (PVID): ").strip()
    if song_id_input.lower() == 'q':
        print("Cancelled.")
        return

    try:
        song_id = int(song_id_input)
    except ValueError:
        logger.error(f"Invalid song ID: {song_id_input}")
        return

    # Get difficulty
    print(f"\nDifficulty options: 0/E/easy, 1/N/normal, 2/H/hard, 3/Ex/extreme, 4/EX/exex/extra_extreme, 5/R/reserved")
    diff_input = input("Difficulty [2/hard]: ").strip()
    if diff_input == '':
        diff_input = "2"

    difficulty = parse_difficulty(diff_input)
    if difficulty is None:
        logger.error(f"Invalid difficulty: {diff_input}")
        return

    # Get chart style
    print(f"\nStyle options: 0/A/arcade, 1/C/console, 2/M/mixed ")
    style_input = input("Style [0/arcade]: ").strip()
    if style_input == '':
        style_input = "0"
    style = parse_style(style_input)

    # Create song and switch
    song = create_test_song(song_id)

    logger.info(f"Switching to song {song_id} with difficulty {difficulty.display_name}, style={style}")

    success, message, actual_diff, mode = _song_selector.switch_song(song, difficulty, style)

    if success:
        logger.info(f"Success: {message}")
        if mode:
            logger.info(f"Switch mode: {mode.value}")
    else:
        logger.error(f"Failed: {message}")


def print_help():
    """Print help information."""
    print("\n" + "=" * 50)
    print("Playground Commands:")
    print("=" * 50)
    print("  s, switch   - Switch to a song (interactive)")
    print("  p, print    - Print current memory status")
    print("  h, help     - Show this help message")
    print("  q, quit     - Exit playground")
    print("\nDifficulty shortcuts:")
    print("  0/e/easy         = EASY")
    print("  1/n/normal       = NORMAL")
    print("  2/h/hard         = HARD (default)")
    print("  3/ex/extreme     = EXTREME")
    print("  4/exex/ex extreme = EXTRA EXTREME")
    print("  5/r/reserved     = RESERVED")
    print("=" * 50)


def main():
    """Main entry point for playground."""
    print("\n" + "=" * 50)
    print("QuantumSwitch Playground")
    print("=" * 50)

    # Initialize
    if not init():
        print("Failed to initialize. Exiting.")
        return

    # Start status printer thread
    printer_thread = threading.Thread(target=status_printer_loop, args=(2.0,), daemon=True)
    printer_thread.start()

    print_help()

    # Main interactive loop
    while True:
        try:
            user_input = input("\n> ").strip().lower()

            if user_input in ('q', 'quit', 'exit'):
                print("Exiting playground...")
                break
            elif user_input in ('h', 'help', '?'):
                print_help()
            elif user_input in ('p', 'print', 'status'):
                print_status()
            elif user_input in ('s', 'switch', 'song'):
                switch_song_interactive()
            elif user_input == '':
                continue
            else:
                print(f"Unknown command: '{user_input}'. Type 'help' for available commands.")

        except KeyboardInterrupt:
            print("\nExiting playground...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")

    # Cleanup
    if _pm:
        _pm.detach()
    print("Goodbye!")


if __name__ == "__main__":
    main()
