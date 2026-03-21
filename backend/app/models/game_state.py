from enum import IntEnum


class GameState(IntEnum):
    """Current state or menu of the game"""
    UNKNOWN = -1
    NOT_READY = 0
    LOADING = 1
    INTRO = 2
    TITLE = 3
    RHYTHM_GAME = 5
    CUSTOM_PLAYLIST = 6
    INGAME = 7
    CUSTOMIZATION = 36
    GALLERY = 38
    MAIN_MENU = 42
    OPTIONS = 44
