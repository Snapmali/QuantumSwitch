from typing import Optional, Tuple

from app.config import settings, DllEnum, DllPatternOffset
from app.models import ChartStyle, GameState, ChartStyleValue
from app.utils.logger import logger


class GameStatusProcessor:
    # Game states
    STATE_INGAME = 0

    PVID_EMPTY_INGAME = 0xFFFFFFFF
    PVID_EMPTY_SONG_SELECTION = 0xFFFFFFFE

    def __init__(self, process_manager, memory_operator):
        self._pm = process_manager
        self._mem = memory_operator

    def attach_for_pid(self) -> Optional[int]:
        if self._pm.attach():
            return self._pm.process_id
        else:
            return None

    def get_game_state(self) -> Optional[GameState]:
        """
        Read the current game state.
        Returns the value from the GAME_STATE_CURR_ADDR address.
        """
        state_value = self._mem.read_int(settings.GAME_STATE_CURR_ADDR)
        try:
            game_state = GameState(state_value)
        except ValueError:
            logger.warning(f"Unknown game state: {state_value}")
            game_state = None
        return game_state

    def get_current_selection(self) -> Tuple[Optional[int], Optional[bool], Optional[ChartStyle]]:
        """
        Get the currently playing or selected song PVID.

        Reads the game state to determine if player is in-game or in song selection,
        then reads the appropriate memory address to get the current PVID.

        Returns:
            Tuple of (current_pvid, is_ingame):
                - current_pvid: The current song PVID, or None if no song selected
                - is_ingame: True if player is in-game (playing), False if in menu,
                           None if cannot read memory
                - style: The current chart style
        """
        # Read game state to determine if player is in-game
        curr_pvid_base_addr = self._mem.read_int(settings.CURR_PVID_BASE_PTR_ADDR, size=8)
        if curr_pvid_base_addr is None:
            logger.warning("Failed to read CURR_PVID_BASE_PTR_ADDR, game may not be running")
            return None, None, None
        logger.debug(f"Read CURR_PVID_BASE_PTR_ADDR 0x{settings.CURR_PVID_BASE_PTR_ADDR:08X} = "
                    f"0x{curr_pvid_base_addr:08X} ({curr_pvid_base_addr})")

        # Determine which memory address to read based on game state
        # STATE_INGAME (0): Player is currently playing a song
        # Other values: Player is in menu/song selection
        if curr_pvid_base_addr == self.STATE_INGAME:
            current_pvid_addr = settings.CURR_PVID_INGAME_ADDR
            is_ingame = True
            use_offset = True
        else:
            curr_pvid_song_selection_offset = (self._mem.read_int(settings.CURR_PVID_SONG_SELECTION_OFFSET_PTR_ADDR)
                                               - settings.CURR_PVID_SONG_SELECTION_OFFSET_PTR_OFFSET)
            if curr_pvid_song_selection_offset is None:
                logger.warning("Failed to read CURR_PVID_SONG_SELECTION_OFFSET, game may not be running")
                return None, None, None

            current_pvid_addr = curr_pvid_base_addr + curr_pvid_song_selection_offset
            is_ingame = False
            use_offset = False
            logger.debug(f"CURR_PVID_ADDR: 0x{current_pvid_addr:08X} = 0x{curr_pvid_base_addr:08X} + 0x{curr_pvid_song_selection_offset:08X}")

        # Read the current PVID from the determined address
        current_pvid = self._mem.read_int(current_pvid_addr, use_offset=use_offset)
        if current_pvid is None:
            logger.warning(f"Failed to read CURR_PVID_BASE_ADDR 0x{curr_pvid_base_addr:08X}, "
                           f"game may not be running or not in the right state")
            return None, None, None

        # Check if no song is selected (empty PVID values)
        elif current_pvid == self.PVID_EMPTY_INGAME or current_pvid == self.PVID_EMPTY_SONG_SELECTION:
            logger.info(f"CURR_PVID_ADDR checked: 0x{current_pvid_addr:08X}, PVID: {current_pvid}, no song selected")
            return None, None, None
        else:
            logger.info(f"CURR_PVID_ADDR checked: 0x{current_pvid_addr:08X}, PVID: {current_pvid}, Ingame state: {is_ingame}")

        style = self.get_current_style()

        return current_pvid, is_ingame, style

    def get_current_style(self) -> ChartStyle:
        """
        Get the current chart style.

        Returns:
            Current chart style as ChartStyle
        """
        if self._mem.get_cached_dll_base(DllEnum.NEW_CLASSICS):
            style_offset = self._mem.read_int(0, dll_pattern_offset=DllPatternOffset.CHART_STYLE_OFFSET)
            style_value = self._mem.read_int(style_offset + 4, dll_pattern_offset=DllPatternOffset.CHART_STYLE_OFFSET)
            return ChartStyleValue.from_value(style_value)
        else:
            return ChartStyle.ARCADE

    def get_last_selection(self) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Get current song selection data.

        Returns:
            Tuple of (pvid, sort_id, difficulty) or (None, None, None) if failed
        """
        pvid = self._mem.read_int(settings.LAST_SELECT_PVID_ADDR, apply_eden=True)
        sort_id = self._mem.read_int(settings.LAST_SELECT_SORT_ADDR, apply_eden=True)
        diff_type = self._mem.read_int(settings.LAST_SELECT_DIFF_TYPE_ADDR, apply_eden=True)
        diff_level = self._mem.read_int(settings.LAST_SELECT_DIFF_LEVEL_ADDR, apply_eden=True)

        logger.debug(f"pvid: {pvid}, sort_id: {sort_id}, diff_type: {diff_type}, diff_level: {diff_level}")

        return pvid, sort_id, diff_type