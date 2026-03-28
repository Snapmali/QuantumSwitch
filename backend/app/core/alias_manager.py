"""Alias manager for handling song aliases persistence and fuzzy matching."""
import json
import uuid
from typing import Dict, List, Optional

from ..config import DATA_DIR
from ..models import SongAlias
from ..utils.logger import logger


class AliasManager:
    """Manages song aliases persistence and fuzzy matching."""

    def __init__(self):
        """Initialize alias manager"""
        self.data_dir = DATA_DIR
        self.alias_file = self.data_dir / "aliases.json"
        self._aliases: Dict[str, SongAlias] = {}  # key: id
        self._ensure_data_dir()
        self.load_aliases()

    def _ensure_data_dir(self) -> None:
        """Ensure data directory exists."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create data directory: {e}")

    def load_aliases(self) -> Dict[str, SongAlias]:
        """Load aliases from file.

        Returns:
            Dict mapping id to SongAlias
        """
        if not self.alias_file.exists():
            logger.info("Aliases file does not exist, starting with empty set")
            self._aliases = {}
            return self._aliases

        try:
            with open(self.alias_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._aliases = {}

            for item in data:
                alias_obj = SongAlias(
                    id=item.get('id', str(uuid.uuid4())),
                    alias=item.get('alias', ''),
                    songName=item.get('songName', '')
                )
                self._aliases[alias_obj.id] = alias_obj

            logger.info(f"Loaded {len(self._aliases)} aliases")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse aliases file: {e}")
            self._aliases = {}
        except Exception as e:
            logger.error(f"Failed to load aliases: {e}")
            self._aliases = {}

        return self._aliases

    def save_aliases(self) -> bool:
        """Save aliases to file.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_data_dir()
            data = [alias.model_dump() for alias in self._aliases.values()]
            with open(self.alias_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save aliases: {e}")
            return False

    def create_alias(self, alias: str, song_name: str) -> Optional[SongAlias]:
        """Create a new alias.

        Args:
            alias: The alias text
            song_name: The actual song name

        Returns:
            Created SongAlias
        """
        alias_obj = SongAlias(
            id=str(uuid.uuid4()),
            alias=alias,
            songName=song_name
        )

        self._aliases[alias_obj.id] = alias_obj

        if self.save_aliases():
            logger.info(f"Created alias: {alias} -> {song_name}")
            return alias_obj
        return None

    def update_alias(self, alias_id: str, alias: Optional[str] = None,
                     song_name: Optional[str] = None) -> Optional[SongAlias]:
        """Update an existing alias.

        Args:
            alias_id: The alias ID to update
            alias: New alias text (optional)
            song_name: New song name (optional)

        Returns:
            Updated SongAlias or None if not found
        """
        if alias_id not in self._aliases:
            logger.warning(f"Alias with ID {alias_id} not found")
            return None

        alias_obj = self._aliases[alias_id]

        # Update fields
        if alias is not None:
            alias_obj.alias = alias
        if song_name is not None:
            alias_obj.songName = song_name

        if self.save_aliases():
            logger.info(f"Updated alias: {alias_obj.alias} -> {alias_obj.songName}")
            return alias_obj
        return None

    def delete_alias(self, alias_id: str) -> bool:
        """Delete an alias.

        Args:
            alias_id: The alias ID to delete

        Returns:
            True if deleted, False if not found
        """
        if alias_id not in self._aliases:
            logger.warning(f"Alias with ID {alias_id} not found")
            return False

        alias = self._aliases[alias_id]

        del self._aliases[alias_id]

        if self.save_aliases():
            logger.info(f"Deleted alias: {alias.alias}")
            return True
        return False

    def get_all_aliases(self) -> List[SongAlias]:
        """Get all aliases.

        Returns:
            List of all SongAlias entries
        """
        return list(self._aliases.values())

    def get_alias_by_id(self, alias_id: str) -> Optional[SongAlias]:
        """Get an alias by ID.

        Args:
            alias_id: The alias ID

        Returns:
            SongAlias or None if not found
        """
        return self._aliases.get(alias_id)

    def find_by_alias(self, alias: str) -> Optional[SongAlias]:
        """Find the first alias by exact match (case insensitive).

        Args:
            alias: The alias to search for

        Returns:
            First matching SongAlias or None if not found
        """
        alias_lower = alias.lower()
        for alias_obj in self._aliases.values():
            if alias_obj.alias.lower() == alias_lower:
                return alias_obj
        return None

    def find_all_by_alias(self, alias: str) -> List[SongAlias]:
        """Find all aliases with the same text (case insensitive).

        Args:
            alias: The alias to search for

        Returns:
            List of matching SongAlias entries
        """
        alias_lower = alias.lower()
        return [
            alias_obj for alias_obj in self._aliases.values()
            if alias_obj.alias.lower() == alias_lower
        ]

    def search_aliases(self, query: str, limit: int = 10) -> List[SongAlias]:
        """Search aliases using fuzzy matching.

        Matching rules (in priority order):
        1. Exact match (alias == query)
        2. Starts with (alias.startswith(query))
        3. Contains (query in alias)

        Args:
            query: Search query
            limit: Maximum number of results (default 10)

        Returns:
            List of matching SongAlias entries sorted by relevance
        """
        query_lower = query.lower()
        matches = []

        # Collect all matches with their priority
        for alias_obj in self._aliases.values():
            alias_lower = alias_obj.alias.lower()

            if alias_lower == query_lower:
                # Exact match - highest priority (0)
                matches.append((0, alias_obj))
            elif alias_lower.startswith(query_lower):
                # Starts with - medium priority (1)
                matches.append((1, alias_obj))
            elif query_lower in alias_lower:
                # Contains - lowest priority (2)
                matches.append((2, alias_obj))

        # Sort by priority, then by alias text for consistent ordering
        matches.sort(key=lambda x: (x[0], x[1].alias.lower()))

        # Return limited results
        return [match[1] for match in matches[:limit]]

    def alias_exists(self, alias: str) -> bool:
        """Check if an alias exists (case insensitive).

        Args:
            alias: The alias to check

        Returns:
            True if exists, False otherwise
        """
        alias_lower = alias.lower()
        return any(
            alias_obj.alias.lower() == alias_lower
            for alias_obj in self._aliases.values()
        )
