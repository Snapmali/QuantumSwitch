"""PVDB file parser for extracting song information."""
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple

import toml

from app.config import DATA_DIR, IS_FROZEN
from app.models import Song, DifficultyType, ChartInfo, ChartStyle, ModInfo, NcSong, NcChartInfo
from app.models.difficulty_type import nc_diff_type_mapping, parse_difficulty_type
from app.utils.logger import logger


@dataclass
class SongBuilder:
    """Type-safe builder for song data during parsing."""
    song_id: int
    mod_info: ModInfo
    mod_enabled: bool = True
    difficulties: List[DifficultyType] = field(default_factory=list)
    difficulty_details: Dict[Tuple[DifficultyType, int], ChartInfo] = field(default_factory=dict)
    hidden: bool = False
    source_file: str = ""
    is_vanilla: bool = False
    attributes: Dict[str, str] = field(default_factory=dict)
    # Song metadata
    name: Optional[str] = None
    name_en: Optional[str] = None
    name_reading: Optional[str] = None
    bpm: Optional[str] = None
    description: Optional[str] = None
    # Credits
    music: Optional[str] = None
    arranger: Optional[str] = None
    lyrics: Optional[str] = None
    guitar_player: Optional[str] = None
    illustrator: Optional[str] = None
    manipulator: Optional[str] = None
    pv_editor: Optional[str] = None

    def get_display_name(self) -> str:
        """Get display name with priority: Japanese > English > Reading > ID."""
        return self.name or self.name_en or self.name_reading or f"PV_{self.song_id:03d}"

    def get_filtered_and_sorted_charts(self) -> List[ChartInfo]:
        """Get charts filtered by script file existence and sorted by difficulty order."""
        charts = []
        for chart in self.difficulty_details.values():
            if not chart.script_file_name or not chart.script_file_name.strip():
                continue
            # Check if script file exists
            if self.mod_info.path and not (self.mod_info.path / chart.script_file_name).exists():
                continue
            charts.append(chart)
        charts.sort(key=lambda c: _get_difficulty_sort_key(c.type))
        return charts


def _get_difficulty_sort_key(diff_type: DifficultyType) -> int:
    """Get sort key for difficulty type."""
    order = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}
    return order.get(diff_type.value, diff_type.value)


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
        # Autoload songs if not already loaded
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
        self._mod_id_counter = 1  # 从 1 开始，原版使用 0
        self._nc_songs = {}  # song_id -> List[NcSong]
        self._mod_infos = {}

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
                        self._nc_songs.setdefault(song_id, []).append(nc_song)
                    logger.info(f"Parsed {len(nc_songs_list)} NC entries from {ncdb_file}")
                except Exception as e:
                    logger.error(f"Error parsing {ncdb_file}: {e}")

        # Sort songs by ID
        self._songs.sort(key=lambda s: s.id)

        # 处理 NC 数据库歌曲，将 NC 难度信息合并到对应歌曲中
        # 如果 nc_db 中某个歌曲 id 的谱面与相同 mod id 的 pv_db 中该歌曲某个谱面的 难度类别、script_file_name 一致，
        # 则 pv_db 中该谱面的 chart style 被 nc_db 的谱面覆盖
        # 否则将该 nc_db 谱面视为新谱面加入到歌曲
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
                # 向歌曲补充 nc_db 中额外的 mod info
                # Merge mod info
                if nc_song.mod_info and nc_song.mod_info not in song.mod_infos:
                    song.mod_infos.append(nc_song.mod_info)

                mod_charts = mod_charts_map.get(nc_song.mod_id, [])

                # 建立 (difficulty_type, script_file_name) -> ChartInfo 的映射
                # Build (difficulty_type, script_file_name) -> ChartInfo lookup
                chart_lookup: Dict[Tuple[DifficultyType, Optional[str]], ChartInfo] = {
                    (mod_chart.type, mod_chart.script_file_name): mod_chart
                    for mod_chart in mod_charts
                }

                nc_styles: Set[ChartStyle] = set()

                # 处理 NC 数据库中的每个难度
                # Process each difficulty from NC database
                for nc_chart in nc_song.chart_infos:
                    nc_styles.add(nc_chart.style)
                    # 如果 nc_db 谱面的 script_file_name 为空，则跳过该谱面
                    if not nc_chart.script_file_name:
                        continue

                    key = (nc_chart.difficulty_type, nc_chart.script_file_name)
                    if key in chart_lookup:
                        # 更新相同 mod_id、难度信息、script_file_name 谱面的风格
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

                # 删除 chart style 在 nc_db 中未定义的谱面
                for mod_chart in mod_charts:
                    if mod_chart.style not in nc_styles:
                        song.chart_infos.remove(mod_chart)

            song.difficulties = [c.type for c in song.chart_infos]

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

                    pvdb_files, mod_ncdb_file = self._find_db_files(rom_path)

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
                path=mod_path,
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

        # Get rom directory (parent of the pv_db file)
        rom_dir = file_path.parent

        # Parse file content into song builders
        builders = self._parse_pvdb_content(file_path, mod_info, is_vanilla, rom_dir)

        # Convert builders to Song objects
        for builder in builders.values():
            self._convert_builder_to_song(builder, file_path)

    def _parse_pvdb_content(self, file_path: Path, mod_info: ModInfo, is_vanilla: bool, rom_dir: Path) -> Dict[int, SongBuilder]:
        """Parse PVDB file content into song builders."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        builders: Dict[int, SongBuilder] = {}

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Handle hidden marker (#hide#pv_XXX...)
            is_hidden = line.startswith('#hide#')
            if is_hidden:
                line = line[6:]

            # Skip pure comment lines
            if line.startswith('#') and not line.startswith('pv_'):
                continue

            match = self.ATTR_PATTERN.match(line)
            if not match:
                continue

            pv_num = int(match.group(1))
            attr_name = match.group(2)
            attr_value = match.group(3) or ""

            if pv_num not in builders:
                builders[pv_num] = SongBuilder(
                    song_id=pv_num,
                    source_file=str(file_path),
                    mod_info=mod_info,
                    mod_enabled=mod_info.enabled,
                    is_vanilla=is_vanilla
                )

            builders[pv_num].attributes[attr_name] = attr_value

            if is_hidden:
                builders[pv_num].hidden = True

            self._parse_attribute_to_builder(builders[pv_num], attr_name, attr_value)

        return builders

    def _convert_builder_to_song(self, builder: SongBuilder, file_path: Path) -> None:
        """Convert SongBuilder to Song and add to collection."""
        if builder.song_id in self._song_map:
            self._merge_song_builder(self._song_map[builder.song_id], builder)
        else:
            song = self._create_song_from_builder(builder)
            self._songs.append(song)
            self._song_map[builder.song_id] = song

            if song.hidden:
                self._hidden_songs.add(builder.song_id)

    def _create_song_from_builder(self, builder: SongBuilder) -> Song:
        """Create a Song object from SongBuilder."""
        charts = builder.get_filtered_and_sorted_charts()

        return Song(
            id=builder.song_id,
            name=builder.get_display_name(),
            name_en=builder.name_en,
            name_reading=builder.name_reading,
            difficulties=[c.type for c in charts],
            chart_infos=charts,
            hidden=builder.hidden,
            mod_infos=[builder.mod_info] if builder.mod_info else [],
            mod_enabled=builder.mod_enabled,
            is_vanilla=builder.is_vanilla,
            bpm=builder.bpm,
            description=builder.description,
            attributes=builder.attributes,
            music=builder.music,
            arranger=builder.arranger,
            lyrics=builder.lyrics,
            guitar_player=builder.guitar_player,
            illustrator=builder.illustrator,
            manipulator=builder.manipulator,
            pv_editor=builder.pv_editor,
        )

    def _merge_song_builder(self, existing: Song, builder: SongBuilder) -> None:
        """Merge SongBuilder data into existing Song."""
        # Build lookup set of existing charts by (mod_id, script_file_name)
        existing_chart_keys: Set[Tuple[Optional[int], Optional[str]]] = {
            (chart.mod_id, chart.script_file_name) for chart in existing.chart_infos
        }

        # Add new charts (with file existence check and deduplication)
        for chart in builder.get_filtered_and_sorted_charts():
            chart_key = (chart.mod_id, chart.script_file_name)
            if chart_key not in existing_chart_keys:
                existing.chart_infos.append(chart)
                existing_chart_keys.add(chart_key)

        # Re-sort and rebuild difficulties list
        existing.chart_infos.sort(key=lambda c: _get_difficulty_sort_key(c.type))
        existing.difficulties = [c.type for c in existing.chart_infos]

        # Update hidden status
        if builder.hidden:
            existing.hidden = True
            self._hidden_songs.add(existing.id)

        # Merge mod info
        if builder.mod_info and builder.mod_info not in existing.mod_infos:
            existing.mod_infos.append(builder.mod_info)

        # Update vanilla status
        if builder.is_vanilla:
            existing.is_vanilla = True

        # Update mod_enabled (OR logic)
        existing.mod_enabled = existing.mod_enabled or builder.mod_enabled

        # Merge attributes
        existing.attributes.update(builder.attributes)

        # Update fields if not already set
        if not existing.name_en and builder.name_en:
            existing.name_en = builder.name_en
        if not existing.name_reading and builder.name_reading:
            existing.name_reading = builder.name_reading
        if not existing.arranger and builder.arranger:
            existing.arranger = builder.arranger

    def _parse_attribute_to_builder(self, builder: SongBuilder, attr_name: str, attr_value: str) -> None:
        """Parse a single attribute into SongBuilder."""
        # Song names
        if attr_name == 'song_name':
            builder.name = attr_value.strip('"')
        elif attr_name == 'song_name_en':
            builder.name_en = attr_value.strip('"')
        elif attr_name == 'song_name_reading':
            builder.name_reading = attr_value.strip('"')
        elif attr_name == 'song_file_name':
            builder.attributes['song_file'] = attr_value.strip('"')
        elif attr_name == 'performer_num':
            builder.attributes['performer_count'] = attr_value if attr_value.isdigit() else '1'
        elif attr_name == 'date':
            builder.attributes['date'] = attr_value
        elif attr_name == 'hidden':
            builder.hidden = attr_value == '1'
        elif attr_name == 'bpm':
            builder.bpm = attr_value
        elif attr_name.startswith('songinfo.'):
            self._parse_songinfo_attribute(builder, attr_name, attr_value, '')
        elif attr_name.startswith('songinfo_en.'):
            self._parse_songinfo_attribute(builder, attr_name, attr_value, '_en')
        elif attr_name == 'sort_index':
            builder.attributes['sort_id'] = attr_value if attr_value.isdigit() else str(builder.song_id)
        else:
            # Parse difficulty attributes
            self._parse_difficulty_attribute(builder, attr_name, attr_value)

    def _parse_songinfo_attribute(self, builder: SongBuilder, attr_name: str, attr_value: str, suffix: str) -> None:
        """Parse songinfo attribute into builder."""
        info_attr = attr_name.split('.')[1] if '.' in attr_name else ''
        field_name = info_attr + suffix
        if hasattr(builder, field_name):
            setattr(builder, field_name, attr_value.strip('"'))

    def _parse_difficulty_attribute(self, builder: SongBuilder, attr_name: str, attr_value: str) -> None:
        """Parse difficulty-related attribute into builder."""
        diff_match = self.DIFF_ATTR_PATTERN.match(attr_name)
        if not diff_match:
            return

        diff_type_name = diff_match.group(1).lower()
        diff_index = int(diff_match.group(2))
        diff_attr = diff_match.group(3)

        diff_type = parse_difficulty_type(diff_type_name)
        if diff_type:
            self._update_builder_difficulty(builder, diff_type, diff_attr, attr_value, diff_index)

    def _update_builder_difficulty(self, builder: SongBuilder, diff_type: DifficultyType,
                                    attr: str, value: str, index: int = 0) -> None:
        """Update difficulty information in SongBuilder."""
        diff_key = (diff_type, index)

        if diff_key not in builder.difficulty_details:
            # Determine actual type (EXTREME with index > 0 could be EXTRA EXTREME)
            actual_type = diff_type
            is_extra = diff_type == DifficultyType.EXTREME and index > 0
            if is_extra:
                actual_type = DifficultyType.EXTRA_EXTREME

            builder.difficulty_details[diff_key] = ChartInfo(
                style=ChartStyle.ARCADE,
                type=actual_type,
                index=index,
                is_extra=is_extra
            )

        chart = builder.difficulty_details[diff_key]

        # Record mod_id
        if builder.mod_info and builder.mod_info.id is not None:
            chart.mod_id = builder.mod_info.id

        # Update chart attributes
        if attr == 'edition':
            chart.edition = int(value) if value.isdigit() else 0
        elif attr == 'level':
            chart.level = self._parse_level(value)
        elif attr == 'script_file_name':
            chart.script_file_name = value.strip('"')
        elif attr == 'attribute.extra' and value.strip() == '1':
            chart.is_extra = True
            if chart.type == DifficultyType.EXTREME:
                chart.type = DifficultyType.EXTRA_EXTREME
        elif attr == 'attribute.original':
            chart.is_original = value.strip() == '1'
        elif attr == 'attribute.slide':
            chart.is_slide = value.strip() == '1'

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
            for diff_key, diff_type in nc_diff_type_mapping.items():
                diff_entries = song_data.get(diff_key, [])
                if not isinstance(diff_entries, list):
                    continue

                for entry in diff_entries:
                    if not isinstance(entry, dict):
                        continue

                    style_str = entry.get('style', 'ARCADE')

                    # 尝试大小写不敏感匹配
                    style = ChartStyle.from_string(style_str)
                    if style is None:
                        style = ChartStyle.ARCADE  # Default to ARCADE if invalid

                    level_raw = entry.get('level')
                    level = self._parse_level(level_raw) if level_raw else 0.0

                    script_file = entry.get('script_file_name')

                    if script_file and mod_info.path and not (mod_info.path / script_file).exists():
                        continue

                    difficulty = NcChartInfo(
                        difficulty_type=diff_type,
                        style=style,
                        level=level,
                        script_file_name=script_file
                    )
                    difficulties.append(difficulty)

            nc_song = NcSong(
                song_id=song_id,
                mod_info=mod_info,
                mod_id=mod_id,
                chart_infos=difficulties,
                source_file=str(file_path)
            )
            nc_songs.append((song_id, nc_song))

        return nc_songs

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

