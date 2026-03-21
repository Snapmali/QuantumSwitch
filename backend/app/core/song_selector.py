"""Song selector implementation for switching songs in-game.

Core Logic Acknowledgment:
    The song switching implementation in this module is based on the core logic
    from hiki8man's Select Song with PVID and sasnchis's DivaSongViewer, along with
    memory addresses and logic open-sourced by 萌新安定:
    https://gamebanana.com/tools/21051
    https://gamebanana.com/tools/18296
    https://github.com/sasnchis/DivaSongViewer/tree/master

    Huge thanks to 萌新安定, hiki8man and sasnchis for reverse engineering and documenting these techniques.
"""
import time
from enum import Enum
from typing import Optional, Tuple

from app.models import ChartStyle, DifficultyType, Song, ChartStyleValue, GameState
from app.utils.logger import logger
from app.config import settings, DllEnum, DllPatternOffset


class SwitchMode(Enum):
    """Song switch modes."""
    STANDARD = "standard"  # Normal switch when in song selection (state 6)
    DELAYED = "delayed"    # Delayed switch when in PV selection (state 5)

class SongSelector:
    """Handles song selection and switching in the game."""

    # Game states
    STATE_INGAME = 0

    def __init__(self, memory_operator):
        self._mem = memory_operator

    def determine_switch_mode(self) -> Optional[SwitchMode]:
        """
        Determine which switch mode to use based on game state.

        According to technical specification (Section 5.2, step 3):
        - Read GAME_STATE_NEXT (0xCC61098)
        - If value == 6: use STANDARD mode (song selection, ready state)
        - If value != 6: use DELAYED mode (PV selection or other states)

        Valid values per spec 3.1.1:
        - 6: Ready state, can accept new commands
        - 5: Switching in progress
        - other: Game handling other operations

        Returns:
            SwitchMode.STANDARD if GAME_STATE_NEXT == 6
            SwitchMode.DELAYED if GAME_STATE_NEXT != 6 (including state 5)
            None if game not running or cannot read memory
        """
        from app.config import settings

        # Read GAME_STATE_NEXT value (0xCC61098)
        # Per spec: Control addresses are NOT affected by Eden offset
        game_state_next = self._mem.read_int(settings.GAME_STATE_NEXT_ADDR)
        if game_state_next is None:
            logger.warning("Failed to read GAME_STATE_NEXT, game may not be running")
            return None

        logger.info(f"Read GAME_STATE_NEXT = {game_state_next} (0x{game_state_next:08X})")

        # According to technical specification Section 5.2:
        # - Step 3: Read GAME_STATE_NEXT
        # - If value == 6: Standard mode (song selection state)
        # - If value != 6: Delayed mode (PV selection or other states)
        if game_state_next == GameState.CUSTOM_PLAYLIST:
            return SwitchMode.STANDARD
        else:
            # Any value other than 6 (including 5 or other states) uses DELAYED mode
            return SwitchMode.DELAYED

    def switch_song(
        self,
        song: Song,
        difficulty: DifficultyType = DifficultyType.HARD,
        style: ChartStyle = ChartStyle.ARCADE
    ) -> Tuple[bool, str, Optional[DifficultyType], Optional[SwitchMode]]:
        """
        Switch to the specified song and difficulty.

        Args:
            song: The song to switch to
            difficulty: The desired difficulty
            style: The target chart style

        Returns:
            Tuple of (success, message, actual_difficulty, mode)
        """
        mode = self.determine_switch_mode()
        if mode is None:
            return False, "Game not running or cannot access memory", None, None

        # Check if the requested difficulty is available
        actual_difficulty = song.get_highest_available_difficulty(difficulty)
        if actual_difficulty is None:
            return False, f"Song '{song.name}' has no available difficulties", None, mode

        if actual_difficulty != difficulty:
            logger.info(f"Difficulty '{difficulty.display_name}' not available, using '{actual_difficulty.display_name}' instead")

        # Execute the appropriate switch method
        if mode == SwitchMode.STANDARD:
            success = self._execute_standard_switch(song, actual_difficulty, style)
        else:
            success = self._execute_delayed_switch(song, actual_difficulty, style)

        if success:
            message = f"Successfully switched to '{song.name}' ({actual_difficulty.display_name})"
            if mode == SwitchMode.DELAYED:
                message += " (delayed update)"
        else:
            message = "Failed to switch song"

        return success, message, actual_difficulty, mode

    def _execute_standard_switch(self, song: Song, difficulty: DifficultyType, style: ChartStyle = ChartStyle.ARCADE) -> bool:
        """
        Execute standard song switch (when in song selection state).

        According to technical specification (Section 5.2):
        - Step 4: Initialize switch (GAME_STATE_NEXT = 6, START_CHANGE = 2)
        - Step 5: Wait 100ms
        - Step 6: Prepare data (write DIFF_TYPE, PVID)
        - Step 7: Set sort (write SORT = 1, DIFF_LEVEL = 19)
        - Step 8: Trigger switch (GAME_STATE_NEXT = 5, START_CHANGE = 2)
        """
        try:
            # Step 4: Initialize switch
            logger.debug("Step 4: Initialize switch")
            # Write GAME_STATE_NEXT = 6 (switch to Custom playlists)
            if not self._mem.write_int(settings.GAME_STATE_NEXT_ADDR, 6):
                logger.error("Failed to set GAME_STATE_NEXT = 6")
                return False

            # Write START_CHANGE = 2 (triggering menu switch)
            if not self._mem.write_int(settings.START_CHANGE_ADDR, 2):
                logger.error("Failed to set START_CHANGE = 2")
                return False

            # Step 5: Wait 100ms for stabilization
            logger.debug("Step 5: Wait 100ms")
            time.sleep(0.1)  # 100ms per specification

            # Step 6: Prepare data (selectPV)
            logger.debug("Step 6: Prepare song data")
            # Write difficulty type first (per spec order)
            if not self._mem.write_int(settings.LAST_SELECT_DIFF_TYPE_ADDR, difficulty.value, apply_eden=True):
                logger.error("Failed to write DIFF_TYPE")
                return False

            # Write PVID (song ID)
            if not self._mem.write_int(settings.LAST_SELECT_PVID_ADDR, song.id, apply_eden=True):
                logger.error("Failed to write PVID")
                return False

            if self._mem.get_cached_dll_base(DllEnum.NEW_CLASSICS):
                # Set chart style (Arcade / Console / Mixed)
                style_offset = self._mem.read_int(0, dll_pattern_offset=DllPatternOffset.CHART_STYLE_OFFSET)
                if not self._mem.write_int(
                        style_offset + 4,
                        ChartStyleValue.to_value(style),
                        dll_pattern_offset=DllPatternOffset.CHART_STYLE_OFFSET
                ):
                    logger.error("Failed to write CHART_STYLE")
                    return False

            # Step 7: Set sort (selectSort)
            logger.debug("Step 7: Set sort")
            # Write LAST_SELECT_SORT_ADDR = 1 (sort by difficulty level)
            if not self._mem.write_int(settings.LAST_SELECT_SORT_ADDR, 1, apply_eden=True):
                logger.error("Failed to write SORT")
                return False

            # Write LAST_SELECT_DIFF_LEVEL_ADDR = 19 (difficulty level = ALL)
            if not self._mem.write_int(settings.LAST_SELECT_DIFF_LEVEL_ADDR, 19, apply_eden=True):
                logger.error("Failed to write DIFF_LEVEL")
                return False

            # Step 8: Trigger switch
            logger.debug("Step 8: Trigger switch")
            # Write GAME_STATE_NEXT = 5 (switch to Rhythm Game)
            if not self._mem.write_int(settings.GAME_STATE_NEXT_ADDR, 5):
                logger.error("Failed to set GAME_STATE_NEXT = 5")
                return False

            # Write START_CHANGE = 2 (triggering menu switch)
            if not self._mem.write_int(settings.START_CHANGE_ADDR, 2):
                logger.error("Failed to set START_CHANGE = 2")
                return False

            logger.info(
                f"Standard switch executed for song {song.id} ({song.name}) "
                f"with difficulty {difficulty.display_name}"
            )
            return True

        except Exception as e:
            logger.exception(f"Error during standard switch: {e}")
            return False

    def _execute_delayed_switch(self, song: Song, difficulty: DifficultyType, style: ChartStyle = ChartStyle.ARCADE) -> bool:
        """
        Execute delayed song switch (when in PV selection state).
        Changes are buffered and applied when user enters song selection.

        According to technical specification (Section 5.3):
        - Only update data (no trigger flags)
        - Execute selectPV(songId, diffLevel)
        - Execute selectSort(19)
        """
        try:
            # Step 1-2: Establish connection and detect version (done by caller)

            # Step 3: Update data only (selectPV + selectSort)
            logger.debug("Delayed mode: Updating data only")

            # selectPV: Write difficulty type first, then PVID (per spec section 5.2 step 6)
            if not self._mem.write_int(settings.LAST_SELECT_DIFF_TYPE_ADDR, difficulty.value, apply_eden=True):
                logger.error("Delayed mode: Failed to write DIFF_TYPE")
                return False

            if not self._mem.write_int(settings.LAST_SELECT_PVID_ADDR, song.id, apply_eden=True):
                logger.error("Delayed mode: Failed to write PVID")
                return False

            if self._mem.get_cached_dll_base(DllEnum.NEW_CLASSICS):
                # Set chart style (Arcade / Console / Mixed)
                style_offset = self._mem.read_int(0, dll_pattern_offset=DllPatternOffset.CHART_STYLE_OFFSET)
                if not self._mem.write_int(
                        style_offset + 4,
                        ChartStyleValue.to_value(style),
                        dll_pattern_offset=DllPatternOffset.CHART_STYLE_OFFSET
                ):
                    logger.error("Failed to write CHART_STYLE")
                    return False

            # Write LAST_SELECT_SORT_ADDR = 1 (sort by difficulty level)
            if not self._mem.write_int(settings.LAST_SELECT_SORT_ADDR, 1, apply_eden=True):
                logger.error("Delayed mode: Failed to write SORT")
                return False

            # Write LAST_SELECT_DIFF_LEVEL_ADDR = 19 (difficulty level = ALL)
            if not self._mem.write_int(settings.LAST_SELECT_DIFF_LEVEL_ADDR, 19, apply_eden=True):
                logger.error("Delayed mode: Failed to write DIFF_LEVEL")
                return False

            # Note: We don't trigger GAME_STATE_NEXT or START_CHANGE here
            # The change will be applied when user presses ENTER to enter song selection

            logger.info(
                f"Delayed switch prepared for song {song.id} ({song.name}) "
                f"with difficulty {difficulty.display_name}"
            )
            return True

        except Exception as e:
            logger.exception(f"Error during delayed switch: {e}")
            return False
