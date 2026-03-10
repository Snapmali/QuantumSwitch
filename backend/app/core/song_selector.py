"""Song selector implementation for switching songs in-game."""
import time
from enum import Enum
from typing import Optional, Tuple
from app.models.song import Song, DifficultyType
from app.utils.logger import logger
from app.config import settings


class SwitchMode(Enum):
    """Song switch modes."""
    STANDARD = "standard"  # Normal switch when in song selection (state 6)
    DELAYED = "delayed"    # Delayed switch when in PV selection (state 5)


class SongSelector:
    """Handles song selection and switching in the game."""

    # Game states
    STATE_PV_SELECTION = 5
    STATE_SONG_SELECTION = 6

    def __init__(self, memory_operator):
        self._mem = memory_operator

    def get_game_state(self) -> Optional[int]:
        """Get the current game state."""
        return self._mem.get_game_state()

    def determine_switch_mode(self) -> Optional[SwitchMode]:
        """
        Determine which switch mode to use based on game state.

        According to technical specification (Section 5.2, step 3):
        - Read CHANGE_SONG_SELECT (0xCC61098)
        - If value == 6: use STANDARD mode (song selection, ready state)
        - If value != 6: use DELAYED mode (PV selection or other states)

        Valid values per spec 3.1.1:
        - 6: Ready state, can accept new commands
        - 5: Switching in progress
        - other: Game handling other operations

        Returns:
            SwitchMode.STANDARD if CHANGE_SONG_SELECT == 6
            SwitchMode.DELAYED if CHANGE_SONG_SELECT != 6 (including state 5)
            None if game not running or cannot read memory
        """
        from app.config import settings

        # Read CHANGE_SONG_SELECT value (0xCC61098)
        # Per spec: Control addresses are NOT affected by Eden offset
        change_song_select = self._mem.read_int32(settings.CHANGE_SONG_SELECT_ADDR, skip_eden=True)
        if change_song_select is None:
            logger.warning("Failed to read CHANGE_SONG_SELECT, game may not be running")
            return None

        logger.info(f"Read CHANGE_SONG_SELECT = {change_song_select} (0x{change_song_select:08X})")

        # According to technical specification Section 5.2:
        # - Step 3: Read CHANGE_SONG_SELECT
        # - If value == 6: Standard mode (song selection state)
        # - If value != 6: Delayed mode (PV selection or other states)
        if change_song_select == self.STATE_SONG_SELECTION:
            return SwitchMode.STANDARD
        else:
            # Any value other than 6 (including 5 or other states) uses DELAYED mode
            return SwitchMode.DELAYED

    def switch_song(
        self,
        song: Song,
        difficulty: DifficultyType = DifficultyType.HARD
    ) -> Tuple[bool, str, Optional[DifficultyType], Optional[SwitchMode]]:
        """
        Switch to the specified song and difficulty.

        Args:
            song: The song to switch to
            difficulty: The desired difficulty

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
            success = self._execute_standard_switch(song, actual_difficulty)
        else:
            success = self._execute_delayed_switch(song, actual_difficulty)

        if success:
            message = f"Successfully switched to '{song.name}' ({actual_difficulty.display_name})"
            if mode == SwitchMode.DELAYED:
                message += " (delayed update - press SPACE to apply)"
        else:
            message = "Failed to switch song"

        return success, message, actual_difficulty, mode

    def _execute_standard_switch(self, song: Song, difficulty: DifficultyType) -> bool:
        """
        Execute standard song switch (when in song selection state).

        According to technical specification (Section 5.2):
        - Step 4: Initialize switch (CHANGE_SONG_SELECT = 6, START_CHANGE = 2)
        - Step 5: Wait 100ms
        - Step 6: Prepare data (write DIFF_TYPE, PVID)
        - Step 7: Set sort (write SORT, DIFF_LEVEL = 19)
        - Step 8: Trigger switch (CHANGE_SONG_SELECT = 5, START_CHANGE = 2)
        """
        try:
            # Step 4: Initialize switch
            logger.debug("Step 4: Initialize switch")
            # Write CHANGE_SONG_SELECT = 6 (prepare state)
            if not self._mem.write_int8(settings.CHANGE_SONG_SELECT_ADDR, 6, skip_eden=True):
                logger.error("Failed to set CHANGE_SONG_SELECT = 6")
                return False

            # Write START_CHANGE = 2 (trigger value per spec)
            if not self._mem.write_int8(settings.START_CHANGE_ADDR, 2, skip_eden=True):
                logger.error("Failed to set START_CHANGE = 2")
                return False

            # Step 5: Wait 100ms for stabilization
            logger.debug("Step 5: Wait 100ms")
            time.sleep(0.1)  # 100ms per specification

            # Step 6: Prepare data (selectPV)
            logger.debug("Step 6: Prepare song data")
            # Write difficulty type first (per spec order)
            if not self._mem.write_int32(settings.LAST_SELECT_DIFF_TYPE_ADDR, difficulty.value):
                logger.error("Failed to write DIFF_TYPE")
                return False

            # Write PVID (song ID)
            if not self._mem.write_int32(settings.LAST_SELECT_PVID_ADDR, song.id):
                logger.error("Failed to write PVID")
                return False

            # Step 7: Set sort (selectSort)
            logger.debug("Step 7: Set sort")
            # Write sort index (default 1 per spec)
            sort_index = 19
            if not self._mem.write_int32(settings.LAST_SELECT_SORT_ADDR, 1):
                logger.error("Failed to write SORT")
                return False

            # Write difficulty level (same as sort_index per spec)
            if not self._mem.write_int32(settings.LAST_SELECT_DIFF_LEVEL_ADDR, sort_index):
                logger.error("Failed to write DIFF_LEVEL")
                return False

            # Step 8: Trigger switch
            logger.debug("Step 8: Trigger switch")
            # Write CHANGE_SONG_SELECT = 5 (execute state)
            if not self._mem.write_int8(settings.CHANGE_SONG_SELECT_ADDR, 5, skip_eden=True):
                logger.error("Failed to set CHANGE_SONG_SELECT = 5")
                return False

            # Write START_CHANGE = 2 (trigger value per spec)
            if not self._mem.write_int8(settings.START_CHANGE_ADDR, 2, skip_eden=True):
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

    def _execute_delayed_switch(self, song: Song, difficulty: DifficultyType) -> bool:
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
            if not self._mem.write_int32(settings.LAST_SELECT_DIFF_TYPE_ADDR, difficulty.value):
                logger.error("Delayed mode: Failed to write DIFF_TYPE")
                return False

            if not self._mem.write_int32(settings.LAST_SELECT_PVID_ADDR, song.id):
                logger.error("Delayed mode: Failed to write PVID")
                return False

            sort_index = 19  # Default sort index per technical specification
            # selectSort: Write sort index and diff level (default 1 per spec)
            if not self._mem.write_int32(settings.LAST_SELECT_SORT_ADDR, 1):
                logger.error("Delayed mode: Failed to write SORT")
                return False

            # Note: DIFF_LEVEL is set to the same value as sort_index per spec
            if not self._mem.write_int32(settings.LAST_SELECT_DIFF_LEVEL_ADDR, sort_index):
                logger.error("Delayed mode: Failed to write DIFF_LEVEL")
                return False

            # Note: We don't trigger CHANGE_SONG_SELECT or START_CHANGE here
            # The change will be applied when user presses SPACE to enter song selection

            logger.info(
                f"Delayed switch prepared for song {song.id} ({song.name}) "
                f"with difficulty {difficulty.display_name}"
            )
            return True

        except Exception as e:
            logger.exception(f"Error during delayed switch: {e}")
            return False

    def get_current_song(self) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Get the currently selected song information."""
        return self._mem.get_current_selection()
