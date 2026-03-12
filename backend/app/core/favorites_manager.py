"""Favorites manager for handling song favorites persistence."""
import json
import os
from pathlib import Path
from typing import Set

from ..utils.logger import logger


class FavoritesManager:
    """Manages favorite songs persistence."""

    def __init__(self, data_dir: str = "data"):
        """Initialize favorites manager.

        Args:
            data_dir: Directory to store favorites data file
        """
        self.data_dir = Path(data_dir)
        self.favorites_file = self.data_dir / "favorites.json"
        self._favorites: Set[int] = set()
        self._ensure_data_dir()
        self.load_favorites()

    def _ensure_data_dir(self) -> None:
        """Ensure data directory exists."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create data directory: {e}")

    def load_favorites(self) -> Set[int]:
        """Load favorites from file.

        Returns:
            Set of favorite song IDs
        """
        if not self.favorites_file.exists():
            logger.info("Favorites file does not exist, starting with empty set")
            self._favorites = set()
            return self._favorites

        try:
            with open(self.favorites_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._favorites = set(data)
                else:
                    logger.warning("Invalid favorites file format, expected list")
                    self._favorites = set()
            logger.info(f"Loaded {len(self._favorites)} favorites")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse favorites file: {e}")
            self._favorites = set()
        except Exception as e:
            logger.error(f"Failed to load favorites: {e}")
            self._favorites = set()

        return self._favorites

    def save_favorites(self) -> bool:
        """Save favorites to file.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_data_dir()
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(list(self._favorites)), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save favorites: {e}")
            return False

    def add_favorite(self, song_id: int) -> bool:
        """Add a song to favorites.

        Args:
            song_id: The song ID to add

        Returns:
            True if added (or already exists), False on error
        """
        try:
            self._favorites.add(song_id)
            return self.save_favorites()
        except Exception as e:
            logger.error(f"Failed to add favorite {song_id}: {e}")
            return False

    def remove_favorite(self, song_id: int) -> bool:
        """Remove a song from favorites.

        Args:
            song_id: The song ID to remove

        Returns:
            True if removed (or didn't exist), False on error
        """
        try:
            self._favorites.discard(song_id)
            return self.save_favorites()
        except Exception as e:
            logger.error(f"Failed to remove favorite {song_id}: {e}")
            return False

    def toggle_favorite(self, song_id: int) -> bool:
        """Toggle a song's favorite status.

        Args:
            song_id: The song ID to toggle

        Returns:
            True if song is now favorited, False otherwise
        """
        if song_id in self._favorites:
            self.remove_favorite(song_id)
            return False
        else:
            self.add_favorite(song_id)
            return True

    def is_favorite(self, song_id: int) -> bool:
        """Check if a song is favorited.

        Args:
            song_id: The song ID to check

        Returns:
            True if favorited, False otherwise
        """
        return song_id in self._favorites

    def get_all_favorites(self) -> Set[int]:
        """Get all favorite song IDs.

        Returns:
            Set of all favorite song IDs
        """
        return self._favorites.copy()


# Global favorites manager instance
_favorites_manager: FavoritesManager | None = None


def get_favorites_manager() -> FavoritesManager:
    """Get or create the global favorites manager instance."""
    global _favorites_manager
    if _favorites_manager is None:
        _favorites_manager = FavoritesManager()
    return _favorites_manager
