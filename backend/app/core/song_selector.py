"""Song selector implementation for switching songs in-game.

Core Logic Acknowledgment:
    The song switching implementation in this module is based on the core logic
    from hiki8man's Select Song with PVID and sasnchis's DivaSongViewer:
    https://gamebanana.com/tools/21051
    https://gamebanana.com/tools/18296
    https://github.com/sasnchis/DivaSongViewer/tree/master

    Specifically, the following aspects are derived from these projects:
    - Memory address layout and offsets for song selection
    - The game state detection mechanism using CHANGE_SONG_SELECT
    - The standard switch procedure and delayed switch procedure
    - The sequence of writing PVID, difficulty type, sort, and difficulty level

    Huge thanks to hiki8man and sasnchis for reverse engineering and documenting these techniques.
"""
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

    STATE_INGAME = 0
    PVID_EMPTY_INGAME = 0xFFFFFFFF
    PVID_EMPTY_SONG_SELECTION = 0xFFFFFFFE

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
        difficulty: DifficultyType = DifficultyType.HARD,
        console: bool = False
    ) -> Tuple[bool, str, Optional[DifficultyType], Optional[SwitchMode]]:
        """
        Switch to the specified song and difficulty.

        Args:
            song: The song to switch to
            difficulty: The desired difficulty
            console: Switch to the console mode

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
            success = self._execute_standard_switch(song, actual_difficulty, console)
        else:
            success = self._execute_delayed_switch(song, actual_difficulty, console)

        if success:
            message = f"Successfully switched to '{song.name}' ({actual_difficulty.display_name})"
            if mode == SwitchMode.DELAYED:
                message += " (delayed update - enter song selection ment to apply)"
        else:
            message = "Failed to switch song"

        return success, message, actual_difficulty, mode

    def _execute_standard_switch(self, song: Song, difficulty: DifficultyType, console: bool = False) -> bool:
        """
        Execute standard song switch (when in song selection state).

        According to technical specification (Section 5.2):
        - Step 4: Initialize switch (CHANGE_SONG_SELECT = 6, START_CHANGE = 2)
        - Step 5: Wait 100ms
        - Step 6: Prepare data (write DIFF_TYPE, PVID)
        - Step 7: Set sort (write SORT = 1, DIFF_LEVEL = 19)
        - Step 8: Trigger switch (CHANGE_SONG_SELECT = 5, START_CHANGE = 2)
        """
        try:
            # Step 4: Initialize switch
            logger.debug("Step 4: Initialize switch")
            # Write CHANGE_SONG_SELECT = 6 (switch to Custom playlists)
            if not self._mem.write_int8(settings.CHANGE_SONG_SELECT_ADDR, 6, skip_eden=True):
                logger.error("Failed to set CHANGE_SONG_SELECT = 6")
                return False

            # Write START_CHANGE = 2 (triggering menu switch)
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
            # Write LAST_SELECT_SORT_ADDR = 1 (sort by difficulty level)
            if not self._mem.write_int32(settings.LAST_SELECT_SORT_ADDR, 1):
                logger.error("Failed to write SORT")
                return False

            # Write LAST_SELECT_DIFF_LEVEL_ADDR = 19 (difficulty level = ALL)
            if not self._mem.write_int32(settings.LAST_SELECT_DIFF_LEVEL_ADDR, 19):
                logger.error("Failed to write DIFF_LEVEL")
                return False

            # Step 8: Trigger switch
            logger.debug("Step 8: Trigger switch")
            # Write CHANGE_SONG_SELECT = 5 (switch to Rhythm Game)
            if not self._mem.write_int8(settings.CHANGE_SONG_SELECT_ADDR, 5, skip_eden=True):
                logger.error("Failed to set CHANGE_SONG_SELECT = 5")
                return False

            # Write START_CHANGE = 2 (triggering menu switch)
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

    def _execute_delayed_switch(self, song: Song, difficulty: DifficultyType, console: bool = False) -> bool:
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

            # Write LAST_SELECT_SORT_ADDR = 1 (sort by difficulty level)
            if not self._mem.write_int32(settings.LAST_SELECT_SORT_ADDR, 1):
                logger.error("Delayed mode: Failed to write SORT")
                return False

            # Write LAST_SELECT_DIFF_LEVEL_ADDR = 19 (difficulty level = ALL)
            if not self._mem.write_int32(settings.LAST_SELECT_DIFF_LEVEL_ADDR, 19):
                logger.error("Delayed mode: Failed to write DIFF_LEVEL")
                return False

            # Note: We don't trigger CHANGE_SONG_SELECT or START_CHANGE here
            # The change will be applied when user presses ENTER to enter song selection

            logger.info(
                f"Delayed switch prepared for song {song.id} ({song.name}) "
                f"with difficulty {difficulty.display_name}"
            )
            return True

        except Exception as e:
            logger.exception(f"Error during delayed switch: {e}")
            return False

    def get_current_selection(self) -> Tuple[Optional[int], Optional[bool]]:
        """
        Get the currently playing or selected song PVID.

        Reads the game state to determine if player is in-game or in song selection,
        then reads the appropriate memory address to get the current PVID.

        Returns:
            Tuple of (current_pvid, is_ingame):
                - current_pvid: The current song PVID, or None if no song selected
                - is_ingame: True if player is in-game (playing), False if in menu,
                           None if cannot read memory
        """
        # Read game state to determine if player is in-game
        curr_pvid_base_addr = self._mem.read_int(settings.CURR_PVID_BASE_PTR_ADDR, 8, signed=False, skip_eden=True)
        if curr_pvid_base_addr is None:
            logger.warning("Failed to read CURR_PVID_BASE_PTR_ADDR, game may not be running")
            return None, None
        logger.debug(f"Read CURR_PVID_BASE_PTR_ADDR 0x{settings.CURR_PVID_BASE_PTR_ADDR:08X} = "
                    f"0x{curr_pvid_base_addr:08X} ({curr_pvid_base_addr})")

        # Determine which memory address to read based on game state
        # STATE_INGAME (0): Player is currently playing a song
        # Other values: Player is in menu/song selection
        if curr_pvid_base_addr == self.STATE_INGAME:
            current_pvid_addr = settings.CURR_PVID_INGAME_ADDR
            is_ingame = True
        else:
            curr_pvid_song_selection_offset = self._mem.read_int32(
                settings.CURR_PVID_SONG_SELECTION_OFFSET_PTR_ADDR,
                signed=False,
                skip_eden=True
            ) - settings.CURR_PVID_SONG_SELECTION_OFFSET_PTR_OFFSET
            if curr_pvid_song_selection_offset is None:
                logger.warning("Failed to read CURR_PVID_SONG_SELECTION_OFFSET, game may not be running")
                return None, None

            current_pvid_addr = curr_pvid_base_addr + curr_pvid_song_selection_offset
            is_ingame = False
            logger.debug(f"CURR_PVID_ADDR: 0x{current_pvid_addr:08X} = 0x{curr_pvid_base_addr:08X} + 0x{curr_pvid_song_selection_offset:08X}")

        # Read the current PVID from the determined address
        current_pvid = self._mem.read_int32(current_pvid_addr, signed=False, skip_eden=True, use_offset=is_ingame)
        if current_pvid is None:
            logger.warning(f"Failed to read CURR_PVID_BASE_ADDR 0x{curr_pvid_base_addr:08X}, "
                           f"game may not be running or not in the right state")
            return None, None

        # Check if no song is selected (empty PVID values)
        elif current_pvid == self.PVID_EMPTY_INGAME or current_pvid == self.PVID_EMPTY_SONG_SELECTION:
            logger.info(f"CURR_PVID_ADDR checked: 0x{current_pvid_addr:08X}, PVID: {current_pvid}, no song selected")
            return None, None
        else:
            logger.info(f"CURR_PVID_ADDR checked: 0x{current_pvid_addr:08X}, PVID: {current_pvid}, Ingame state: {is_ingame}")

        return current_pvid, is_ingame

    def get_last_selection(self) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Get the currently selected song information."""
        return self._mem.get_last_selection()
