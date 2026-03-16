"""PVDB file parser for extracting song information."""
import re
import toml
from collections import defaultdict
from PyInstaller.log import level

import app.models.song as song_model
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple
from app.models import Song, DifficultyType, ChartInfo, ChartStyle, NcSong, NcChartInfo
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

    # ROM directory variants (31 types)
    ROM_DIRS = [
        ".", "rom_ps4", "rom_ps4_dlc", "rom_ps4_fix", "rom_ps4_patch",
        "rom_steam", "rom_steam_cn", "rom_steam_dlc", "rom_steam_en",
        "rom_steam_fr", "rom_steam_ge", "rom_steam_it", "rom_steam_kr",
        "rom_steam_region", "rom_steam_region_cn", "rom_steam_region_dlc",
        "rom_steam_region_dlc_kr", "rom_steam_region_en", "rom_steam_region_fr",
        "rom_steam_region_ge", "rom_steam_region_kr", "rom_steam_region_sp",
        "rom_steam_region_tw", "rom_steam_sp", "rom_steam_tw",
        "rom_switch", "rom_switch_cn", "rom_switch_en", "rom_switch_kr", "rom_switch_tw"
    ]

    # Database file prefixes (21 types)
    DB_PREFIXES = [
        "mod_", "", "end_", "mdata_", "patch2_", "patch_",
        "dlc13_", "dlc12_", "dlc14_", "dlc9_", "dlc8_", "dlc11_",
        "dlc10_", "dlc4_", "dlc3B_", "dlc7_", "privilege_",
        "dlc2A_", "dlc1_", "dlc3A_", "dlc2B_"
    ]

    def __init__(self, mods_directory: Optional[Path] = None):
        self.mods_directory = mods_directory
        self._songs: List[Song] = []
        self._song_map: Dict[int, Song] = {}
        self._hidden_songs: Set[int] = set()
        self._mod_id_counter: int = 1  # 从 1 开始，原版使用 0
        self._nc_songs: Dict[int, List[NcSong]] = {}  # song_id -> List[NcSong]
        self._mod_infos: Dict[int, ModInfo] = {}

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

    def get_nc_songs(self, song_id: int) -> List[NcSong]:
        """Get NC database song entries by song ID."""
        return self._nc_songs.get(song_id, [])

    @property
    def nc_songs(self) -> Dict[int, List[NcSong]]:
        """Get all parsed NC songs."""
        return self._nc_songs.copy()

    def get_mod_info(self, mod_id: int) -> Optional[ModInfo]:
        """Get NC database song info by ID."""
        return self._mod_infos.get(mod_id)

    def get_mod_infos(self) -> Dict[int, ModInfo]:
        """Get all parsed NC songs."""
        return self._mod_infos.copy()

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

        # Collect scan results: (mod_info, pvdb_files, ncdb_file, is_vanilla)
        mod_results: List[tuple[ModInfo, List[Path], Optional[Path], bool]] = []

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
            for mod_info, pvdb_files, ncdb_file in self._scan_dir_for_mods(project_vanilla_dir, is_vanilla=True):
                mod_results.append((mod_info, pvdb_files, ncdb_file, True))

        # Scan mods directory for new Mod structure
        if self.mods_directory and self.mods_directory.exists():
            logger.info(f"Scanning mods directory: {self.mods_directory}")
            for mod_info, pvdb_files, ncdb_file in self._scan_dir_for_mods(self.mods_directory):
                mod_results.append((mod_info, pvdb_files, ncdb_file, False))

        # Scan additional paths
        if additional_paths:
            for path in additional_paths:
                if path.exists():
                    logger.info(f"Scanning additional path: {path}")
                    for mod_info, pvdb_files, ncdb_file in self._scan_dir_for_mods(path):
                        mod_results.append((mod_info, pvdb_files, ncdb_file, False))

        # Sort mod_results: vanilla (True) first, then by mod name, then by mod id
        mod_results.sort(key=lambda x: (
            not x[3],  # is_vanilla: True (0) comes before False (1)
            x[0].name.lower() if x[0] else "",  # mod name (case-insensitive)
            x[0].id if x[0] else 0  # mod id
        ))

        # Parse each mod's pv_db files
        for mod_info, pvdb_files, ncdb_file, is_vanilla in mod_results:

            self._mod_infos[mod_info.id] = mod_info

            for file_path in pvdb_files:
                try:
                    self._parse_pvdb_file(file_path, mod_info, is_vanilla)
                except Exception as e:
                    logger.error(f"Error parsing {file_path}: {e}")

            # Parse nc_db file if exists
            if ncdb_file:
                try:
                    nc_songs_list = self._parse_ncdb_file(ncdb_file, mod_info)
                    for song_id, nc_song in nc_songs_list:
                        self._nc_songs.get(song_id, []).append(nc_song)
                    logger.info(f"Parsed {len(nc_songs_list)} NC entries from {ncdb_file}")
                except Exception as e:
                    logger.error(f"Error parsing {ncdb_file}: {e}")

        # Sort songs by ID
        self._songs.sort(key=lambda s: s.id)

        # 处理 NC 数据库歌曲，将 NC 难度信息合并到对应歌曲中
        # Process NC database songs, merge NC difficulty info into corresponding songs
        for song_id, nc_list in self._nc_songs.items():
            song = self._song_map.get(song_id)
            if not song:
                continue

            # 预处理：按 mod_id 分组建立查找表，避免重复遍历
            # Pre-process: build lookup table by mod_id to avoid repeated iteration
            mod_charts_map: Dict[int, List[ChartInfo]] = defaultdict(list)
            for chart in song.chart_infos:
                mod_charts_map[chart.mod_id].append(chart)

            # 遍历该歌曲的所有 NC 条目
            # Iterate through all NC entries for this song
            for nc_song in nc_list:
                mod_charts = mod_charts_map.get(nc_song.mod_id, [])

                # 建立 (difficulty_type, script_file_name) -> ChartInfo 的映射
                # Build (difficulty_type, script_file_name) -> ChartInfo lookup
                chart_lookup: Dict[Tuple[DifficultyType, Optional[str]], ChartInfo] = {
                    (chart.type, chart.script_file_name): chart
                    for chart in mod_charts
                }

                # 处理 NC 数据库中的每个难度
                # Process each difficulty from NC database
                for nc_chart in nc_song.chart_infos:
                    if not nc_chart.script_file_name:
                        continue

                    key = (nc_chart.difficulty_type, nc_chart.script_file_name)
                    if key in chart_lookup:
                        # 更新已有谱面的风格
                        # Update existing chart style
                        chart_lookup[key].style = nc_chart.style
                    else:
                        # 添加新谱面
                        # Add new chart
                        new_chart = ChartInfo(
                            style=nc_chart.style,
                            type=nc_chart.difficulty_type,
                            level=nc_chart.level,
                            script_file_name=nc_chart.script_file_name,
                            is_extra=nc_chart.difficulty_type == DifficultyType.EXTRA_EXTREME,
                            mod_id=nc_song.mod_id
                        )
                        song.chart_infos.append(new_chart)
                        # 同步更新查找表
                        # Update lookup table
                        chart_lookup[key] = new_chart

        logger.info(f"Total songs loaded: {len(self._songs)}")
        return self._songs

    def _parse_include_dirs(self, config: dict) -> List[str]:
        """
        Parse include directories from config.toml, supporting nested structures.

        Supported formats:
        - Simple string: include = ["mod1", "mod2"]
        - Nested table: include = ["mod1", { include = "mod2" }, { include = ["mod3", "mod4"] }]

        Returns:
            List of all include directories in original order
        """
        dirs = []
        stack = []

        includes = config.get('include', [])
        if not isinstance(includes, list):
            return dirs

        # Push to stack in reverse order to maintain original order
        for item in reversed(includes):
            stack.append(item)

        # Depth-first processing
        while stack:
            value = stack.pop()
            if isinstance(value, str):
                dirs.append(value)
            elif isinstance(value, dict):
                if 'include' in value:
                    sub = value['include']
                    if isinstance(sub, str):
                        dirs.append(sub)
                    elif isinstance(sub, list):
                        for item in reversed(sub):
                            stack.append(item)

        return dirs

    def _find_db_files(self, rom_path: Path) -> Tuple[List[Path], Optional[Path]]:
        """
        Search for database files in the specified ROM directory.

        Args:
            rom_path: ROM directory path (.../rom/)

        Returns:
            Tuple of (pv_db_files, nc_db_file)
            - pv_db_files: List of all found pv_db file paths (ordered by DB_PREFIXES)
            - nc_db_file: nc_db.toml file path (if exists)
        """
        pv_db_files = []
        nc_db_file = None

        # Check for nc_db.toml
        nc_path = rom_path / "nc_db.toml"
        if nc_path.exists():
            nc_db_file = nc_path
            logger.info(f"Found nc_db.toml: {nc_path}")

        # Search for pv_db files with various prefixes
        for prefix in self.DB_PREFIXES:
            for name in [f"{prefix}pv_db.txt", f"{prefix}nc_pv_db.txt"]:
                pv_path = rom_path / name
                if pv_path.exists():
                    pv_db_files.append(pv_path)
                    logger.info(f"Found PVDB file: {pv_path}")

        return pv_db_files, nc_db_file

    def _scan_dir_for_mods(self, directory: Path, is_vanilla: bool = False) -> List[tuple[ModInfo, List[Path], Optional[Path]]]:
        """
        Scan a directory for Mod subdirectories.

        Args:
            directory: Directory to scan (mods_directory or additional_paths)
            is_vanilla: If True, scan as vanilla directory (no Mod structure required)

        Returns:
            List of tuples (mod_info, pvdb_files, ncdb_file)
        """
        results: List[tuple[ModInfo, List[Path], Optional[Path]]] = []

        # For vanilla directory, directly search for PVDB files
        if is_vanilla:
            vanilla_pvdb_files = []
            vanilla_ncdb_file = None
            for pattern in ["*.txt"]:
                files = list(directory.rglob(pattern))
                for file_path in files:
                    # Only include PVDB related files
                    if "pv_db" in file_path.name or "mdata_pv_db" in file_path.name:
                        vanilla_pvdb_files.append(file_path)
                        logger.info(f"Found vanilla PVDB file: {file_path}")
            if vanilla_pvdb_files or vanilla_ncdb_file:
                # Create vanilla mod info with id=0
                vanilla_mod_info = ModInfo(
                    id=0,  # 原版 ID 为 0
                    name="Vanilla charts",
                    path=None,
                    enabled=True,  # 原版始终启用
                    author=None,
                    version=None
                )
                results.append((vanilla_mod_info, vanilla_pvdb_files, vanilla_ncdb_file))
            return results

        # Iterate through subdirectories - each is a potential Mod
        for mod_path in directory.iterdir():
            if not mod_path.is_dir():
                continue

            config_path = mod_path / "config.toml"

            if not config_path.exists():
                # Not a standard Mod structure, skip
                logger.debug(f"Directory {mod_path} has no config.toml,")
                continue

            # Load Mod configuration
            mod_config = self._load_mod_config(mod_path)
            if not mod_config:
                # Mod is failed to load
                continue

            mod_info, include_dirs = mod_config

            # Collect all pvdb_files and ncdb_file for this mod
            mod_pvdb_files: List[Path] = []
            mod_ncdb_file: Optional[Path] = None

            # Traverse include dirs and ROM_DIRS to find database files
            for include in include_dirs:
                for rom_dir in self.ROM_DIRS:
                    rom_path = mod_path / include / rom_dir / "rom"
                    if not rom_path.exists():
                        continue

                    pvdb_files, ncdb_file = self._find_db_files(rom_path)

                    # nc_db found
                    if ncdb_file:
                        mod_ncdb_file = ncdb_file
                        logger.info(f"nc_db.toml found at {ncdb_file}, parsing TODO")

                    mod_pvdb_files.extend(pvdb_files)

            if mod_pvdb_files or mod_ncdb_file:
                results.append((mod_info, mod_pvdb_files, mod_ncdb_file))

        return results

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

    def _load_mod_config(self, mod_path: Path) -> Optional[tuple[ModInfo, List[str]]]:
        """Load Mod configuration from config.toml.

        Args:
            mod_path: Path to the Mod directory

        Returns:
            Tuple of (ModInfo, include_dirs) or None if mod is disabled
        """
        config_path = mod_path / "config.toml"
        if not config_path.exists():
            logger.warning(f"Mod config not found: {config_path}")
            return None

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = toml.load(f)

            # Required: enabled field
            enabled = config.get('enabled', True)

            # Get mod info
            name = config.get('name', mod_path.name)
            author = config.get('author')
            version = config.get('version')

            # Parse include directories from root config (not mod table)
            include_dirs = self._parse_include_dirs(config)
            if not include_dirs:
                include_dirs = ["."]

            mod_info = ModInfo(
                id=self._mod_id_counter,
                name=name,
                path=str(mod_path),
                enabled=enabled,
                author=author,
                version=version
            )
            self._mod_id_counter += 1
            return mod_info, include_dirs
        except Exception as e:
            logger.error(f"Error loading Mod config from {config_path}: {e}")
            return None

    def _parse_pvdb_file(self, file_path: Path, mod_info: ModInfo, is_vanilla: bool = False) -> None:
        """Parse a single PVDB file.

        Args:
            file_path: Path to the PVDB file
            mod_info: Mod information for songs from this file
            is_vanilla: Whether this file is from vanilla directory
        """
        logger.info(f"Parsing {file_path} (vanilla={is_vanilla})")
        mod_path = mod_info.path

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
                    'mod_info': mod_info,
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
                    if d.script_file_name and d.script_file_name.strip()  # Must have script file
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
                    chart_infos=difficulty_details,
                    hidden=data.get('hidden', False),
                    mod_infos=[mod_info],
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

    def _parse_ncdb_file(self, file_path: Path, mod_info: ModInfo) -> List[Tuple[int, NcSong]]:
        """Parse a single NC database TOML file.

        Args:
            file_path: Path to the nc_db.toml file
            mod_info: Optional Mod information

        Returns:
            List of tuples (song_id, NcSong) - allowing multiple entries per song_id
        """
        logger.info(f"Parsing NC DB file: {file_path}")

        nc_songs: List[Tuple[int, NcSong]] = []

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = toml.load(f)

        # Get mod_id
        mod_id = mod_info.id

        # Parse songs array
        songs = data.get('songs', [])
        if not isinstance(songs, list):
            logger.warning(f"Invalid 'songs' format in {file_path}, expected array of tables")
            return nc_songs

        for song_data in songs:
            if not isinstance(song_data, dict):
                continue

            song_id = song_data.get('id')
            if song_id is None:
                continue

            # Parse difficulties
            difficulties: List[NcChartInfo] = []

            # Difficulty mapping from TOML keys to internal names
            for diff_key, diff_type in song_model.nc_diff_type_mapping.items():
                diff_entries = song_data.get(diff_key, [])
                if not isinstance(diff_entries, list):
                    continue

                for entry in diff_entries:
                    if not isinstance(entry, dict):
                        continue

                    style_str = entry.get('style', 'ARCADE')
                    try:
                        style = ChartStyle(style_str)
                    except ValueError:
                        style = ChartStyle.ARCADE  # Default to ARCADE if invalid

                    level_raw = entry.get('level')
                    level = self._parse_level(level_raw) if level_raw else None

                    script_file = entry.get('script_file_name')

                    difficulty = NcChartInfo(
                        difficulty_type=diff_type,
                        style=style,
                        level=level,
                        script_file_name=script_file
                    )
                    difficulties.append(difficulty)

            nc_song = NcSong(
                song_id=song_id,
                chart_infos=difficulties,
                source_file=str(file_path),
                mod_id=mod_id
            )
            nc_songs.append((song_id, nc_song))

        return nc_songs

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

        elif attr_name == 'sort_index':
            data['sort_id'] = int(attr_value) if attr_value.isdigit() else data['id']
            return

        # Parse new-style difficulty attributes with index: difficulty.{type}.{index}.{attr}
        diff_match = self.DIFF_ATTR_PATTERN.match(attr_name)
        if diff_match:
            diff_type_name = diff_match.group(1).lower()
            diff_index = int(diff_match.group(2))
            diff_attr = diff_match.group(3)

            diff_type = song_model.parse_difficulty_type(diff_type_name)
            if diff_type:
                self._update_difficulty_detail(data, diff_type, diff_attr, attr_value, diff_index)
            return

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

            data['difficulty_details'][diff_key] = ChartInfo(
                style=ChartStyle.ARCADE,
                type=actual_type,
                index=index,
                is_extra=is_extra
            )

        detail: ChartInfo = data['difficulty_details'][diff_key]

        # Record mod_id if available
        if data.get('mod_info') and data['mod_info'].id is not None:
            detail.mod_ids.add(data['mod_info'].id)
            detail.mod_id = data['mod_info'].id

        if attr == 'edition':
            detail.edition = int(value) if value.isdigit() else 0

        elif attr == 'level':
            detail.level = self._parse_level(value)
            # Don't add to difficulties list here - wait for script_file_name
            # Difficulties without script files will be filtered out later

        elif attr == 'script_file_name':
            detail.script_file_name = value.strip('"')

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
            elif attr_prop == 'original':
                detail.is_original = value.strip() == '1'
            elif attr_prop == 'slide':
                detail.is_slide = value.strip() == '1'

        # Only add to difficulties list when script file is present
        if detail.script_file_name and detail.type not in data.get('difficulties', []):
            if 'difficulties' not in data:
                data['difficulties'] = []
            data['difficulties'].append(detail.type)

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
            if not detail.script_file_name or not detail.script_file_name.strip():
                continue

            # Append the new difficulty detail
            existing.chart_infos.append(detail)

        # Re-sort difficulty details by custom order after merge
        existing.chart_infos.sort(
            key=lambda d: self.DIFFICULTY_ORDER.index(d.type.value)
            if d.type.value in self.DIFFICULTY_ORDER else d.type.value
        )
        # Rebuild difficulties list based on sorted details (all should have script_path)
        existing.difficulties = [d.type for d in existing.chart_infos]

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

