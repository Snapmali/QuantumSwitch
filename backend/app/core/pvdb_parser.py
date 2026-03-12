"""PVDB file parser for extracting song information."""
import re
import toml
from pathlib import Path
from typing import List, Optional, Dict, Set
from app.models.song import Song, DifficultyType, DifficultyInfo
from app.models.mod_info import ModInfo
from app.utils.logger import logger
from app.config import DATA_DIR, IS_FROZEN


class PvdbParser:
    """Parses PVDB files to extract song information."""

    # Regex patterns for parsing
    PV_ID_PATTERN = re.compile(r'pv_(\d+)')
    ATTR_PATTERN = re.compile(r'pv_(\d+)\.(?!.*lyric)([^=]+)=(.+)?')
    # Match difficulty attributes with index: difficulty.{type}.{index}.{attr}
    DIFF_ATTR_PATTERN = re.compile(r'difficulty\.(\w+)\.(\d+)\.(\w+)')
    # Match old-style difficulty without index: difficulty.{type}.{attr}
    DIFF_ATTR_NO_INDEX_PATTERN = re.compile(r'difficulty\.(\w+)\.(\w+)')
    # Match old-style difficulty: song_{type}_difficulty
    OLD_DIFF_PATTERN = re.compile(r'song_(\w+)_difficulty')

    # Standard difficulty order: EASY (0), NORMAL (1), HARD (2), EXTREME (3), EXTRA_EXTREME (4)
    DIFFICULTY_ORDER = [0, 1, 2, 3, 4]

    def __init__(self, mods_directory: Optional[Path] = None):
        self.mods_directory = mods_directory
        self._songs: List[Song] = []
        self._song_map: Dict[int, Song] = {}
        self._hidden_songs: Set[int] = set()
        self._mod_id_counter: int = 1  # 从 1 开始，原版使用 0

    @property
    def songs(self) -> List[Song]:
        """Get all parsed songs."""
        return self._songs.copy()

    @property
    def hidden_count(self) -> int:
        """Get count of hidden songs."""
        return len(self._hidden_songs)

    def get_song_by_id(self, song_id: int) -> Optional[Song]:
        """Get a song by its ID."""
        # Auto-load songs if not already loaded
        if not self._song_map:
            self.scan_and_parse()
        return self._song_map.get(song_id)

    def scan_and_parse(self, additional_paths: Optional[List[Path]] = None) -> List[Song]:
        """
        Scan for PVDB files and parse them.

        Supports new Mod directory structure:
        - mods_directory or additional_paths contain Mod subdirectories
        - Each Mod has config.toml and rom/ directory
        - config.toml has 'enabled' field for Mod status

        Args:
            additional_paths: Additional directories to scan

        Returns:
            List of parsed songs
        """
        self._songs = []
        self._song_map = {}
        self._hidden_songs = set()

        pvdb_files: List[tuple[Path, Optional[ModInfo], bool]] = []

        # Scan project data/vanilla directory (not in mods folder)
        # This is the vanilla folder in the project: backend/data/vanilla
        # In frozen mode, use DATA_DIR from config; in dev mode, use relative path
        if IS_FROZEN:
            project_vanilla_dir = DATA_DIR / "vanilla"
        else:
            # __file__ is backend/app/core/pvdb_parser.py
            # parent.parent.parent = backend
            project_vanilla_dir = Path(__file__).parent.parent.parent / "data" / "vanilla"
        if project_vanilla_dir.exists():
            logger.info(f"Scanning project vanilla directory: {project_vanilla_dir}")
            for file_path, mod_info in self._scan_for_mods(project_vanilla_dir, is_vanilla=True):
                pvdb_files.append((file_path, mod_info, True))

        # Scan mods directory for new Mod structure
        if self.mods_directory and self.mods_directory.exists():
            logger.info(f"Scanning mods directory: {self.mods_directory}")
            for file_path, mod_info in self._scan_for_mods(self.mods_directory):
                pvdb_files.append((file_path, mod_info, False))

        # Scan additional paths
        if additional_paths:
            for path in additional_paths:
                if path.exists():
                    logger.info(f"Scanning additional path: {path}")
                    for file_path, mod_info in self._scan_for_mods(path):
                        pvdb_files.append((file_path, mod_info, False))

        # Sort pvdb_files: vanilla (True) first, then by mod name, then by mod id
        pvdb_files.sort(key=lambda x: (
            not x[2],  # is_vanilla: True (0) comes before False (1)
            x[1].name.lower() if x[1] else "",  # mod name (case-insensitive)
            x[1].id if x[1] else 0  # mod id
        ))

        # Parse each file with its associated Mod info and vanilla flag
        for file_path, mod_info, is_vanilla_file in pvdb_files:
            try:
                self._parse_file(file_path, mod_info, is_vanilla_file)
            except Exception as e:
                logger.error(f"Error parsing {file_path}: {e}")

        # Sort songs by ID
        self._songs.sort(key=lambda s: s.id)

        logger.info(f"Total songs loaded: {len(self._songs)} (hidden: {self.hidden_count})")
        return self._songs

    def _scan_for_mods(self, directory: Path, is_vanilla: bool = False) -> List[tuple[Path, Optional[ModInfo]]]:
        """
        Scan a directory for Mod subdirectories.

        Args:
            directory: Directory to scan (mods_directory or additional_paths)
            is_vanilla: If True, scan as vanilla directory (no Mod structure required)

        Returns:
            List of tuples (pvdb_file_path, mod_info)
        """
        pvdb_files: List[tuple[Path, Optional[ModInfo]]] = []

        # For vanilla directory, directly search for PVDB files
        if is_vanilla:
            for pattern in ["*.txt"]:
                files = list(directory.rglob(pattern))
                for file_path in files:
                    # Only include PVDB related files
                    if "pv_db" in file_path.name or "mdata_pv" in file_path.name:
                        # Create vanilla mod info with id=0
                        vanilla_mod_info = ModInfo(
                            id=0,  # 原版 ID 为 0
                            name="Vanilla",
                            path=None,
                            enabled=True,  # 原版始终启用
                            author=None,
                            version=None
                        )
                        pvdb_files.append((file_path, vanilla_mod_info))
                        logger.info(f"Found vanilla PVDB file: {file_path}")
            return pvdb_files

        # Iterate through subdirectories - each is a potential Mod
        for mod_path in directory.iterdir():
            if not mod_path.is_dir():
                continue

            # Check for Mod structure: config.toml + rom/ directory
            config_path = mod_path / "config.toml"
            rom_path = mod_path / "rom"

            if not config_path.exists() or not rom_path.exists():
                # Not a standard Mod structure, but check for PVDB files directly
                logger.debug(f"Directory {mod_path} is not a standard Mod, scanning for PVDB files directly")
                for pattern in ["mod_pv_db.txt", "mdata_pv_db.txt"]:
                    files = list(mod_path.rglob(pattern))
                    for file_path in files:
                        pvdb_files.append((file_path, None))
                continue

            # Load Mod configuration
            mod_info = self._load_mod_config(mod_path)
            if not mod_info:
                logger.warning(f"Failed to load Mod config from {mod_path}")
                continue

            # Scan rom/ directory for PVDB files
            for pattern in ["mod_pv_db.txt", "mdata_pv_db.txt"]:
                files = list(rom_path.glob(pattern))
                for file_path in files:
                    pvdb_files.append((file_path, mod_info))
                    logger.info(f"Found PVDB file: {file_path} (Mod: {mod_info.name}, enabled: {mod_info.enabled})")

        return pvdb_files

    def _get_mod_path_from_file(self, file_path: Path) -> Optional[str]:
        """Extract mod directory path from PVDB file path.

        Args:
            file_path: Path to the PVDB file

        Returns:
            Path to the mod directory, or None if not found
        """
        # file_path: .../mods/SomeMod/rom/mod_pv_db.txt
        # mod_path: .../mods/SomeMod
        try:
            parts = file_path.parts
            for i, part in enumerate(parts):
                if part == "rom" and i > 0:
                    return str(Path(*parts[:i]))
            # Fallback: parent of parent
            return str(file_path.parent.parent)
        except Exception:
            return None

    def _load_mod_config(self, mod_path: Path) -> Optional[ModInfo]:
        """Load Mod configuration from config.toml.

        Args:
            mod_path: Path to the Mod directory

        Returns:
            ModInfo object or None if config is invalid
        """
        config_path = mod_path / "config.toml"
        if not config_path.exists():
            logger.warning(f"Mod config not found: {config_path}")
            # Return default ModInfo with directory name
            mod_info = ModInfo(
                id=self._mod_id_counter,
                name=mod_path.name,
                path=str(mod_path),
                enabled=True
            )
            self._mod_id_counter += 1
            return mod_info

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = toml.load(f)

            # Required: enabled field
            enabled = config.get('enabled', True)

            # Get mod info from config
            mod_config = config.get('mod', {})
            name = mod_config.get('name', mod_path.name)
            author = mod_config.get('author')
            version = mod_config.get('version')

            mod_info = ModInfo(
                id=self._mod_id_counter,
                name=name,
                path=str(mod_path),
                enabled=enabled,
                author=author,
                version=version
            )
            self._mod_id_counter += 1
            return mod_info
        except Exception as e:
            logger.error(f"Error loading Mod config from {config_path}: {e}")
            # Return default ModInfo with directory name
            mod_info = ModInfo(
                id=self._mod_id_counter,
                name=mod_path.name,
                path=str(mod_path),
                enabled=True
            )
            self._mod_id_counter += 1
            return mod_info

    def _parse_file(self, file_path: Path, mod_info: Optional[ModInfo] = None, is_vanilla: bool = False) -> None:
        """Parse a single PVDB file.

        Args:
            file_path: Path to the PVDB file
            mod_info: Optional Mod information for songs from this file
            is_vanilla: Whether this file is from vanilla directory
        """
        logger.info(f"Parsing {file_path} (vanilla={is_vanilla})")

        # Determine mod_path from file_path or mod_info
        if mod_info:
            mod_path = mod_info.path
        else:
            mod_path = self._get_mod_path_from_file(file_path)

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Parse entries
        lines = content.split('\n')
        current_songs: Dict[int, Dict] = {}

        for line in lines:
            original_line = line  # Keep original for #hide# check
            line = line.strip()
            if not line:
                continue

            # Check for hidden song marker (#hide#pv_XXX...)
            is_hidden = line.startswith('#hide#')
            if is_hidden:
                line = line[6:]  # Remove #hide# prefix

            # Skip pure comment lines (but not #hide# lines)
            if line.startswith('#') and not line.startswith('pv_'):
                continue

            match = self.ATTR_PATTERN.match(line)
            if not match:
                continue

            pv_num = int(match.group(1))
            attr_name = match.group(2)
            attr_value = match.group(3) or ""

            if pv_num not in current_songs:
                current_songs[pv_num] = {
                    'id': pv_num,
                    'difficulties': [],
                    'difficulty_details': {},  # Map<DifficultyType, DifficultyInfo>
                    'hidden': False,
                    'source_file': str(file_path),
                    'mod_path': mod_path,
                    'mod_info': mod_info,
                    'mod_infos': [mod_info] if mod_info else [],  # List of all associated mods
                    'mod_enabled': mod_info.enabled if mod_info else True,
                    'is_vanilla': is_vanilla,  # Mark as vanilla song
                    'attributes': {},  # All raw PVDB attributes
                }

            # Store original attribute
            current_songs[pv_num]['attributes'][attr_name] = attr_value

            # Check hidden status from line prefix
            if is_hidden:
                current_songs[pv_num]['hidden'] = True

            self._parse_attribute(current_songs[pv_num], attr_name, attr_value)

        # Convert to Song objects
        for pv_num, data in current_songs.items():
            if pv_num in self._song_map:
                # Merge with existing song, passing is_vanilla from the current file
                self._merge_song_data(self._song_map[pv_num], data, is_vanilla)
            else:
                # Build difficulty details list - only include difficulties with script files
                difficulty_details = [
                    d for d in data.get('difficulty_details', {}).values()
                    if d.script_path and d.script_path.strip()  # Must have script file
                ]
                # Sort by difficulty order
                difficulty_details.sort(key=lambda d: self.DIFFICULTY_ORDER.index(d.type.value) if d.type.value in self.DIFFICULTY_ORDER else d.type.value)

                # Build difficulties list based on filtered and sorted order
                difficulties = [d.type for d in difficulty_details]

                # Get name with priority: Japanese > English > Reading > ID
                name = data.get('name')
                if not name:
                    name = data.get('name_en') or data.get('name_reading') or f"PV_{data['id']:03d}"

                song = Song(
                    id=data['id'],
                    name=name,
                    name_en=data.get('name_en'),
                    name_reading=data.get('name_reading'),
                    difficulties=difficulties,
                    difficulty_details=difficulty_details,
                    hidden=data.get('hidden', False),
                    source_file=data.get('source_file'),
                    mod_path=data.get('mod_path'),
                    mod_info=data.get('mod_info'),
                    mod_infos=data.get('mod_infos', []),
                    mod_enabled=data.get('mod_enabled', True),
                    is_vanilla=data.get('is_vanilla', False),
                    bpm=data.get('bpm'),
                    description=data.get('description'),
                    attributes=data.get('attributes', {}),
                    # Song credits from songinfo
                    music=data.get('music'),
                    arranger=data.get('arranger'),
                    lyrics=data.get('lyrics'),
                    guitar_player=data.get('guitar_player'),
                    illustrator=data.get('illustrator'),
                    manipulator=data.get('manipulator'),
                    pv_editor=data.get('pv_editor'),
                )

                self._songs.append(song)
                self._song_map[pv_num] = song

                if song.hidden:
                    self._hidden_songs.add(pv_num)

    def _parse_attribute(self, data: Dict, attr_name: str, attr_value: str) -> None:
        """Parse a single attribute."""
        # Song names - priority: song_name (Japanese) > song_name_en > song_name_reading
        if attr_name == 'song_name':
            data['name'] = attr_value.strip('"')

        elif attr_name == 'song_name_en':
            data['name_en'] = attr_value.strip('"')

        elif attr_name == 'song_name_reading':
            data['name_reading'] = attr_value.strip('"')

        elif attr_name == 'song_file_name':
            data['song_file'] = attr_value.strip('"')

        elif attr_name == 'sabi_start_time':
            data['sabi_start'] = attr_value

        elif attr_name == 'sabi_play_time':
            data['sabi_duration'] = attr_value

        elif attr_name == 'performer_num':
            data['performer_count'] = int(attr_value) if attr_value.isdigit() else 1

        elif attr_name == 'date':
            data['date'] = attr_value

        elif attr_name == 'song_video_re':
            data['has_video'] = attr_value == '1'

        elif attr_name == 'song_video_omake':
            data['has_omake'] = attr_value == '1'

        elif attr_name == 'hidden':
            data['hidden'] = attr_value == '1'

        elif attr_name == 'bpm':
            data['bpm'] = attr_value

        elif attr_name.startswith('songinfo.'):
            # Parse songinfo attributes
            info_attr = attr_name.split('.')[1] if '.' in attr_name else ''
            if info_attr == 'music':
                data['music'] = attr_value.strip('"')
            elif info_attr == 'lyrics':
                data['lyrics'] = attr_value.strip('"')
            elif info_attr == 'arranger':
                data['arranger'] = attr_value.strip('"')
            elif info_attr == 'guitar_player':
                data['guitar_player'] = attr_value.strip('"')
            elif info_attr == 'illustrator':
                data['illustrator'] = attr_value.strip('"')
            elif info_attr == 'manipulator':
                data['manipulator'] = attr_value.strip('"')
            elif info_attr == 'pv_editor':
                data['pv_editor'] = attr_value.strip('"')

        elif attr_name.startswith('songinfo_en.'):
            # Parse English songinfo attributes (store as backup or for display)
            info_attr = attr_name.split('.')[1] if '.' in attr_name else ''
            if info_attr == 'music':
                data.setdefault('music_en', attr_value.strip('"'))
            elif info_attr == 'lyrics':
                data.setdefault('lyrics_en', attr_value.strip('"'))
            elif info_attr == 'illustrator':
                data.setdefault('illustrator_en', attr_value.strip('"'))
            elif info_attr == 'manipulator':
                data.setdefault('manipulator_en', attr_value.strip('"'))

        elif attr_name.startswith('songinfo.'):
            # Parse songinfo attributes
            info_attr = attr_name.split('.')[1] if '.' in attr_name else ''
            if info_attr == 'music':
                data['music'] = attr_value.strip('"')
            elif info_attr == 'lyrics':
                data['lyrics'] = attr_value.strip('"')
            elif info_attr == 'arranger':
                data['arranger'] = attr_value.strip('"')
            elif info_attr == 'guitar_player':
                data['guitar_player'] = attr_value.strip('"')
            elif info_attr == 'illustrator':
                data['illustrator'] = attr_value.strip('"')
            elif info_attr == 'manipulator':
                data['manipulator'] = attr_value.strip('"')
            elif info_attr == 'pv_editor':
                data['pv_editor'] = attr_value.strip('"')

        elif attr_name.startswith('songinfo_en.'):
            # Parse English songinfo attributes (store as backup or for display)
            info_attr = attr_name.split('.')[1] if '.' in attr_name else ''
            if info_attr == 'music':
                data.setdefault('music_en', attr_value.strip('"'))
            elif info_attr == 'lyrics':
                data.setdefault('lyrics_en', attr_value.strip('"'))
            elif info_attr == 'illustrator':
                data.setdefault('illustrator_en', attr_value.strip('"'))
            elif info_attr == 'manipulator':
                data.setdefault('manipulator_en', attr_value.strip('"'))

        elif attr_name == 'sort_index':
            data['sort_id'] = int(attr_value) if attr_value.isdigit() else data['id']
            return

        # Parse new-style difficulty attributes with index: difficulty.{type}.{index}.{attr}
        diff_match = self.DIFF_ATTR_PATTERN.match(attr_name)
        if diff_match:
            diff_type_name = diff_match.group(1).lower()
            diff_index = int(diff_match.group(2))
            diff_attr = diff_match.group(3)

            diff_type = self._parse_difficulty_type(diff_type_name)
            if diff_type:
                self._update_difficulty_detail(data, diff_type, diff_attr, attr_value, diff_index)
            return

        # Parse new-style difficulty attributes without index: difficulty.{type}.{attr}
        diff_no_index_match = self.DIFF_ATTR_NO_INDEX_PATTERN.match(attr_name)
        if diff_no_index_match:
            diff_type_name = diff_no_index_match.group(1).lower()
            diff_attr = diff_no_index_match.group(2)

            diff_type = self._parse_difficulty_type(diff_type_name)
            if diff_type:
                self._update_difficulty_detail(data, diff_type, diff_attr, attr_value, 0)
            return

        # Parse old-style difficulty: song_{type}_difficulty
        old_diff_match = self.OLD_DIFF_PATTERN.match(attr_name)
        if old_diff_match:
            diff_name = old_diff_match.group(1).upper()
            diff_type = self._parse_difficulty_type(diff_name)
            if diff_type and attr_value and attr_value != '-1':
                if diff_type not in data['difficulties']:
                    data['difficulties'].append(diff_type)
                # Initialize difficulty detail if not exists
                if diff_type not in data['difficulty_details']:
                    data['difficulty_details'][diff_type] = DifficultyInfo(type=diff_type)

    def _parse_difficulty_type(self, name: str) -> Optional[DifficultyType]:
        """Parse difficulty type name to enum."""
        mapping = {
            'easy': DifficultyType.EASY,
            'normal': DifficultyType.NORMAL,
            'hard': DifficultyType.HARD,
            'extreme': DifficultyType.EXTREME,
            'extra_extreme': DifficultyType.EXTRA_EXTREME,
            'extraextreme': DifficultyType.EXTRA_EXTREME,
            'exextreme': DifficultyType.EXTRA_EXTREME,
        }
        return mapping.get(name.lower())

    def _update_difficulty_detail(self, data: Dict, diff_type: DifficultyType,
                                   attr: str, value: str, index: int = 0) -> None:
        """Update difficulty detail information."""
        if 'difficulty_details' not in data:
            data['difficulty_details'] = {}

        # Create a unique key for each difficulty instance (type + index)
        diff_key = (diff_type, index)

        if diff_key not in data['difficulty_details']:
            # Determine actual difficulty type
            # If index > 0 and type is EXTREME, it could be EXTRA EXTREME
            actual_type = diff_type
            is_extra = False

            # Check if this is an indexed EXTREME difficulty (potential EXTRA EXTREME)
            if diff_type == DifficultyType.EXTREME and index > 0:
                is_extra = True
                actual_type = DifficultyType.EXTRA_EXTREME

            data['difficulty_details'][diff_key] = DifficultyInfo(
                type=actual_type,
                index=index,
                is_extra=is_extra
            )

        detail = data['difficulty_details'][diff_key]

        # Record mod_id if available
        if data.get('mod_info') and data['mod_info'].id is not None:
            detail.mod_ids.add(data['mod_info'].id)

        if attr == 'level':
            detail.level = self._parse_level(value)
            # Don't add to difficulties list here - wait for script_file_name
            # Difficulties without script files will be filtered out later

        elif attr == 'edition':
            detail.edition = int(value) if value.isdigit() else 0

        elif attr == 'script_file_name':
            detail.script_path = value.strip('"')
            # Only add to difficulties list when script file is present
            if detail.script_path and detail.type not in data.get('difficulties', []):
                if 'difficulties' not in data:
                    data['difficulties'] = []
                data['difficulties'].append(detail.type)

        elif attr == 'attribute':
            # Attribute alone doesn't add difficulty - need script file
            pass

        elif attr.startswith('attribute.'):
            # Handle nested attribute properties like attribute.extra
            attr_prop = attr.split('.')[1] if '.' in attr else attr.split('_')[-1]
            if attr_prop == 'extra' and value.strip() == '1':
                detail.is_extra = True
                # Promote EXTREME with extra=1 to EXTRA_EXTREME
                if detail.type == DifficultyType.EXTREME:
                    detail.type = DifficultyType.EXTRA_EXTREME
                # Add to difficulties if script file exists or will exist
                if detail.type not in data.get('difficulties', []):
                    if 'difficulties' not in data:
                        data['difficulties'] = []
                    data['difficulties'].append(detail.type)
            elif attr_prop == 'original':
                detail.is_original = value.strip() == '1'
            elif attr_prop == 'slide':
                detail.is_slide = value.strip() == '1'

    def _merge_song_data(self, existing: Song, new_data: Dict, is_vanilla: bool = False) -> None:
        """Merge new data into an existing song.

        Args:
            existing: The existing song object to merge into
            new_data: New song data from parsing
            is_vanilla: Whether this data comes from a vanilla file
        """
        # Merge difficulty details (keys are now tuples: (diff_type, index))
        # Only include difficulties with script files
        for diff_key, detail in new_data.get('difficulty_details', {}).items():
            # Skip difficulties without script files (also filter empty/whitespace-only paths)
            if not detail.script_path or not detail.script_path.strip():
                continue

            # diff_key is a tuple: (diff_type, index) or just diff_type for legacy data
            if isinstance(diff_key, tuple):
                diff_type, index = diff_key
            else:
                diff_type = diff_key
                index = detail.index if hasattr(detail, 'index') else 0

            # Find matching existing detail by type and index
            existing_detail = next(
                (d for d in existing.difficulty_details
                 if d.type == detail.type and d.index == detail.index),
                None
            )
            if existing_detail:
                # Update existing detail with new info if available
                if detail.level > 0:
                    existing_detail.level = detail.level
                if detail.edition > 0:
                    existing_detail.edition = detail.edition
                if detail.script_path:
                    existing_detail.script_path = detail.script_path
                # Update boolean flags
                if detail.is_extra:
                    existing_detail.is_extra = True
                if detail.is_original:
                    existing_detail.is_original = True
                if detail.is_slide:
                    existing_detail.is_slide = True
                # Merge mod_ids sets
                existing_detail.mod_ids.update(detail.mod_ids)
            else:
                existing.difficulty_details.append(detail)

        # Re-sort difficulty details by custom order after merge
        existing.difficulty_details.sort(
            key=lambda d: self.DIFFICULTY_ORDER.index(d.type.value)
            if d.type.value in self.DIFFICULTY_ORDER else d.type.value
        )
        # Rebuild difficulties list based on sorted details (all should have script_path)
        existing.difficulties = [d.type for d in existing.difficulty_details]

        # Update hidden status
        if new_data.get('hidden'):
            existing.hidden = True
            self._hidden_songs.add(existing.id)

        # Merge Mod information - add new mod to list if not already present
        new_mod_info = new_data.get('mod_info')
        if new_mod_info:
            # Add to mod_infos list if not already present
            if new_mod_info not in existing.mod_infos:
                existing.mod_infos.append(new_mod_info)
            # Also update single mod_info for backward compatibility (use first enabled or first available)
            if not existing.mod_info or (not existing.mod_info.enabled and new_mod_info.enabled):
                existing.mod_info = new_mod_info

        # Update vanilla status - if any source is vanilla, mark as vanilla
        if new_data.get('is_vanilla'):
            existing.is_vanilla = True

        # Update mod_enabled: OR logic - if any mod is enabled, song is enabled
        new_mod_enabled = new_data.get('mod_enabled', True)
        existing.mod_enabled = existing.mod_enabled or new_mod_enabled

        # Merge attributes
        existing.attributes.update(new_data.get('attributes', {}))

        # Update other fields if not already set
        if not existing.name_en and new_data.get('name_en'):
            existing.name_en = new_data['name_en']

        if not existing.name_reading and new_data.get('name_reading'):
            existing.name_reading = new_data['name_reading']

        if not existing.arranger and new_data.get('arranger'):
            existing.arranger = new_data['arranger']

    def search_songs(self, query: str, difficulty: Optional[int] = None) -> List[Song]:
        """Search songs by name or PV ID."""
        results = []
        query_lower = query.lower()

        for song in self._songs:
            # Search by ID
            if query.isdigit() and song.id == int(query):
                results.append(song)
                continue

            # Search by name (Japanese, English, or reading)
            match = (
                query_lower in song.name.lower() or
                (song.name_en and query_lower in song.name_en.lower()) or
                (song.name_reading and query_lower in song.name_reading.lower())
            )
            if match:
                if difficulty is not None:
                    if difficulty in [d.value for d in song.difficulties]:
                        results.append(song)
                else:
                    results.append(song)

        return results

    def get_song(self, song_id: int) -> Optional[Song]:
        """Get a song by ID (alias for get_song_by_id)."""
        return self.get_song_by_id(song_id)

    def _parse_level(self, value: str) -> float:
        """Parse level from PV_LV_WW_D format (e.g., PV_LV_06_5 -> 6.5)."""
        if not value:
            return 0.0
        # Match PV_LV_WW_D format
        match = re.match(r'PV_LV_(\d{2})_(\d)', value)
        if match:
            whole = int(match.group(1))
            decimal = int(match.group(2))
            return whole + decimal / 10.0
        # Fallback: try to parse as integer
        try:
            return float(value) if value.replace('.', '').isdigit() else 0.0
        except (ValueError, AttributeError):
            return 0.0

