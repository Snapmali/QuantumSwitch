from enum import Enum


class DifficultyType(Enum):
    """Difficulty types for songs."""
    EASY = 0
    NORMAL = 1
    HARD = 2
    EXTREME = 3
    EXTRA_EXTREME = 4
    RESERVED = 5

    @property
    def display_name(self) -> str:
        """Get the display name for the difficulty."""
        names = {
            DifficultyType.EASY: "EASY",
            DifficultyType.NORMAL: "NORMAL",
            DifficultyType.HARD: "HARD",
            DifficultyType.EXTREME: "EXTREME",
            DifficultyType.EXTRA_EXTREME: "EXTRA EXTREME",
            DifficultyType.RESERVED: "RESERVED",
        }
        return names.get(self, self.name)

    @property
    def short_name(self) -> str:
        """Get the short name for the difficulty."""
        names = {
            DifficultyType.EASY: "E",
            DifficultyType.NORMAL: "N",
            DifficultyType.HARD: "H",
            DifficultyType.EXTREME: "Ex",
            DifficultyType.EXTRA_EXTREME: "EX",
            DifficultyType.RESERVED: "R",
        }
        return names.get(self, self.name[0])


diff_type_mapping = {
        'easy': DifficultyType.EASY,
        'normal': DifficultyType.NORMAL,
        'hard': DifficultyType.HARD,
        'extreme': DifficultyType.EXTREME,
        'extra_extreme': DifficultyType.EXTRA_EXTREME,
        'ex_extreme': DifficultyType.EXTRA_EXTREME,
        'extraextreme': DifficultyType.EXTRA_EXTREME,
        'exextreme': DifficultyType.EXTRA_EXTREME,
    }

nc_diff_type_mapping = {
                'easy': DifficultyType.EASY,
                'normal': DifficultyType.NORMAL,
                'hard': DifficultyType.HARD,
                'extreme': DifficultyType.EXTREME,
                'ex_extreme': DifficultyType.EXTRA_EXTREME,
            }

def parse_difficulty_type(name: str):
    """Parse difficulty type name to enum."""
    return diff_type_mapping.get(name.lower())