"""Process management for finding and accessing the game process."""
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Optional, List, Dict
import psutil

from app.models.process_module import ProcessModule
from app.utils.logger import logger
from app.config import settings, DllEnum, DllPattern


class ProcessManager:
    """Manages finding and accessing the DivaMegaMix.exe process."""

    # Windows API constants
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_OPERATION = 0x0008
    PROCESS_VM_READ = 0x0010
    PROCESS_VM_WRITE = 0x0020
    PROCESS_ALL_ACCESS = (
        PROCESS_QUERY_INFORMATION |
        PROCESS_VM_OPERATION |
        PROCESS_VM_READ |
        PROCESS_VM_WRITE
    )

    def __init__(self, process_name: str = "DivaMegaMix.exe"):
        self.process_name = process_name
        self._process_handle: Optional[wintypes.HANDLE] = None
        self._process_id: Optional[int] = None
        self._base_address: Optional[int] = None
        self._eden_checked = False
        self._dll_cache: Optional[Dict[str, ProcessModule]] = None

    def __enter__(self):
        """Context manager entry."""
        self.attach()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.detach()
        return False

    @property
    def process_id(self) -> Optional[int]:
        """Get the current process ID."""
        return self._process_id

    @property
    def base_address(self) -> Optional[int]:
        """Get the process base address."""
        return self._base_address

    @property
    def eden_checked(self) -> bool:
        """Get is eden version checked."""
        return self._eden_checked

    def set_eden_checked(self):
        """Get whether eden version is checked."""
        self._eden_checked = True
        logger.debug(f"Eden version checked: {self._eden_checked}")

    @property
    def is_attached(self) -> bool:
        """Check if currently attached to a process."""
        if self._process_handle is None:
            return False
        # Handle both HANDLE objects (with .value) and raw integers
        if isinstance(self._process_handle, int):
            return self._process_handle != 0
        return self._process_handle.value != 0

    def get_handle(self) -> Optional[wintypes.HANDLE]:
        """Get the process handle."""
        if not self.is_attached:
            if not self.attach():
                return None
        return self._process_handle

    def find_process(self) -> Optional[int]:
        """
        Find the game process by name.

        Returns:
            Process ID if found, None otherwise
        """
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == self.process_name:
                    pid = proc.info['pid']

                    # Check whether the current process is a brand-new process
                    if self.is_attached and self._process_id != pid:
                        self.detach()

                    return pid
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if self.is_attached:
            self.detach()
        return None

    def attach(self) -> bool:
        """
        Attach to the game process.

        Returns:
            True if successfully attached, False otherwise
        """
        pid = self.find_process()
        if pid is None:
            logger.info(f"Process {self.process_name} not found")
            return False

        if self.is_attached:
            return True

        self._process_id = pid

        # Open process with required access rights
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.restype = wintypes.HANDLE
        self._process_handle = kernel32.OpenProcess(
            self.PROCESS_ALL_ACCESS,
            False,
            pid
        )

        # Handle both HANDLE objects (with .value) and raw integers
        handle_value = self._process_handle.value if hasattr(self._process_handle, 'value') else self._process_handle
        if not self._process_handle or handle_value == 0:
            error_code = ctypes.windll.kernel32.GetLastError()
            logger.error(f"Failed to open process {pid}. Error code: {error_code}")
            logger.error("Try running as administrator.")
            self._process_handle = None
            self._process_id = None
            self._base_address = None
            self._eden_checked = False
            self._dll_cache = None
            return False

        # Get base address from the opened handle and cache DLL list
        modules = self._enum_modules(self._process_handle)
        if modules:
            self._base_address = modules[0]
            logger.info(f"Found process {self.process_name} (PID: {pid}) at base address 0x{self._base_address:08X}")
            # Build DLL cache from already enumerated modules
            self._dll_cache = self._build_dll_cache(modules)
            # Scan patterns for cached DLLs
            self.scan_dll_patterns()
        else:
            logger.error(f"Could not enumerate modules of process {pid}, not attached.")
            self._process_handle = None
            self._process_id = None
            self._base_address = None
            self._eden_checked = False
            self._dll_cache = None
            return False

        logger.info(f"Successfully attached to process {pid}")
        return True

    def detach(self) -> None:
        """Detach from the game process."""
        if self._process_handle:
            # Handle both HANDLE objects (with .value) and raw integers
            handle_value = self._process_handle.value if hasattr(self._process_handle, 'value') else self._process_handle
            if handle_value != 0:
                ctypes.windll.kernel32.CloseHandle(self._process_handle)
                logger.info(f"Detached from process {self._process_id}")

        self._process_handle = None
        self._process_id = None
        self._base_address = None
        self._eden_checked = False
        self._dll_cache = None

    def get_process_info(self) -> Optional[dict]:
        """Get process information dictionary"""
        if not self.is_attached:
            if not self.attach():
                return None
        return {
            "pid": self._process_id,
            "base_address": self._base_address,
        }

    def get_modules(self) -> List[int]:
        """
        Enumerate all modules (DLLs) loaded in the attached process.

        Returns:
            List of HMODULE values (module base addresses)
        """
        if not self.is_attached:
            logger.error("Cannot get modules: not attached to process")
            return []

        return self._enum_modules(self._process_handle)

    def _enum_modules(self, h_process) -> List[int]:
        """
        Core method to enumerate all modules in a process.
        Shared by _get_module_base_address and get_modules.

        Args:
            h_process: Windows process handle (can be int or c_void_p)

        Returns:
            List of HMODULE values (module base addresses)
        """
        psapi = ctypes.windll.psapi
        cb_needed = wintypes.DWORD()

        # First call to get required buffer size
        if not psapi.EnumProcessModules(
            h_process,
            None,
            0,
            ctypes.byref(cb_needed)
        ):
            return []

        # Allocate buffer for module handles
        module_count = cb_needed.value // ctypes.sizeof(wintypes.HMODULE)
        h_mods = (wintypes.HMODULE * module_count)()

        # Second call to get actual module handles
        if not psapi.EnumProcessModules(
            h_process,
            ctypes.byref(h_mods),
            ctypes.sizeof(h_mods),
            ctypes.byref(cb_needed)
        ):
            return []

        # Filter out None/null handles
        return [h for h in h_mods if h]

    def get_cached_dll(self, dll: DllEnum) -> Optional[ProcessModule]:
        """
        Retrieve a cached DLL module from the internal cache.

        This method looks up the specified DLL from the internal DLL cache.
        The cache is populated after successfully attaching to the process
        (built by the _build_dll_cache method).

        Args:
            dll: DLL settings enum value (e.g., DllSettings.NEW_CLASSICS)

        Returns:
            ProcessModule object containing DLL name, path, and handle,
            or None if not found or cache is empty
        """
        if self._dll_cache is not None:
            return self._dll_cache.get(dll)
        return None

    def get_dll_list(self, filter_name: Optional[str] = None) -> Dict[str, int]:
        """
        Get a mapping of module file paths to their handles.
        Uses cached list if available (populated during attach).

        Args:
            filter_name: Optional string to filter module names (case-insensitive)

        Returns:
            Dictionary mapping module file paths to HMODULE values
        """
        # Build from scratch using already enumerated modules
        modules = self.get_modules()
        dll_list = self._build_dll_dict_from_modules(modules)

        if filter_name is not None:
            filter_lower = filter_name.lower()
            dll_list = {
                name: hmodule for name, hmodule in dll_list.items()
                if filter_lower in name.lower()
            }

        return dll_list

    def get_dll(self, name: str, exact_match: bool = False) -> Optional[int]:
        """
        Find a specific DLL by name.

        Args:
            name: The DLL name to search for (e.g., "NewClassics.dll")
            exact_match: If True, requires exact filename match; if False, uses substring match

        Returns:
            HMODULE value (base address) of the found DLL, or None if not found
        """
        name_lower = name.lower()
        dll_list = self.get_dll_list()

        for module_path, hmodule in dll_list.items():
            if exact_match:
                filename = Path(module_path).name.lower()
                if filename == name_lower:
                    return hmodule
            else:
                if name_lower in module_path.lower():
                    return hmodule

        return None

    def _build_dll_cache(self, modules: List[int]) -> Dict[str, ProcessModule]:
        """
        Build DLL dictionary for caching from already enumerated module handles.
        Only caches DLLs that are in the CACHED_DLLS whitelist and located in the game directory.

        Args:
            modules: List of HMODULE values from _enum_modules

        Returns:
            Dictionary mapping names in CACHED_DLLS to dll module infos
        """
        output: Dict[str, ProcessModule] = {}
        # 获取白名单
        whitelist = [name for name in settings.CACHED_DLLS]

        # 获取游戏路径
        game_directory = settings.GAME_DIRECTORY

        dll_list = self._build_dll_dict_from_modules(modules)
        # 仅缓存白名单中的 DLL，且位于游戏路径下
        for white in whitelist:
            for path, hmodule in dll_list.items():
                dll_path = Path(path)
                dll_name = dll_path.name

                # 检查是否在游戏路径下（如果游戏路径已知）
                if game_directory is not None:
                    try:
                        # 检查 dll_path 是否在游戏目录下
                        dll_path.resolve().relative_to(game_directory.resolve())
                    except ValueError:
                        # 不在游戏目录下，跳过
                        continue
                if white == dll_name:
                    module = ProcessModule(
                        name=dll_name,
                        path=dll_path,
                        hmodule=hmodule,
                        pattern_cache={}
                    )
                    output[white] = module
                    logger.info(f"Cached DLL: {path} at 0x{hmodule:08X}")
                    break

        return output

    def _build_dll_dict_from_modules(self, modules: List[int]) -> Dict[str, int]:
        """
        Build DLL dictionary from already enumerated module handles.

        Args:
            modules: List of HMODULE values from _enum_modules

        Returns:
            Dictionary mapping module file paths to HMODULE values
        """
        output: Dict[str, int] = {}
        psapi = ctypes.windll.psapi

        for hmodule in modules:
            path_buffer = ctypes.create_unicode_buffer(32767)  # Maximum extended path length
            size = psapi.GetModuleFileNameExW(
                self._process_handle,
                wintypes.HMODULE(hmodule),
                path_buffer,
                wintypes.DWORD(32767)
            )
            if size > 0:
                path = path_buffer.value
                output[path] = hmodule

        return output

    def scan_dll_patterns(self) -> None:
        """
        Scan all configured patterns in cached DLLs.
        Results are stored in each ProcessModule's pattern_cache.
        """
        if self._dll_cache is None:
            logger.warning("Cannot scan patterns: DLL cache not initialized")
            return

        for pattern_config in settings.CACHED_PATTERN:
            dll_name = pattern_config.dll
            pattern_bytes = pattern_config.pattern

            # Find the DLL in cache
            dll_module = self._dll_cache.get(dll_name)
            if dll_module is None:
                logger.debug(f"Pattern scan skipped: {dll_name} not in cache")
                continue

            # Scan for pattern
            address = self._scan_pattern_in_dll(dll_module, pattern_bytes)
            if address is not None:
                dll_module.pattern_cache[pattern_config.name] = address
                logger.info(f"Pattern '{pattern_config.name}' found in {dll_name} at 0x{address:08X}")
            else:
                logger.warning(f"Pattern '{pattern_config.name}' not found in {dll_name}")

    def get_pattern_address(self, dll: DllEnum, pattern: DllPattern) -> Optional[int]:
        """
        Get cached pattern address from a specific DLL.

        Args:
            dll: The DLL enum to look in
            pattern: The DllPattern to find

        Returns:
            The cached address if found, None otherwise
        """
        if self._dll_cache is None:
            return None

        dll_module = self._dll_cache.get(dll)
        if dll_module is None:
            return None

        return dll_module.pattern_cache.get(pattern.name)

    def _scan_pattern_in_dll(self, dll_module: ProcessModule, pattern: bytes) -> Optional[int]:
        """
        Scan for a byte pattern within a DLL's memory.

        Args:
            dll_module: The ProcessModule to scan
            pattern: The byte pattern to search for (may contain wildcards as None bytes)

        Returns:
            The address where pattern was found, or None if not found
        """
        if not self.is_attached or self._process_handle is None:
            logger.error("Cannot scan pattern: not attached to process")
            return None

        # Get module information to determine size
        module_info = self._get_module_info(dll_module.hmodule)
        if module_info is None:
            logger.error(f"Failed to get module info for {dll_module.name}")
            return None

        base_addr, module_size = module_info

        # Read entire module memory
        handle = self.get_handle()
        if handle is None:
            return None

        try:
            buffer = self._read_memory_range(handle, base_addr, module_size)
            if buffer is None:
                logger.error(f"Failed to read memory from {dll_module.name}")
                return None

            # Search for pattern with wildcard support
            offset = self._find_pattern_with_wildcards(buffer, pattern)
            if offset == -1:
                return None

            return base_addr + offset

        except Exception as e:
            logger.error(f"Error scanning pattern in {dll_module.name}: {e}")
            return None

    def _get_module_info(self, hmodule: int) -> Optional[tuple]:
        """
        Get module base address and size.

        Args:
            hmodule: The module handle

        Returns:
            Tuple of (base_address, size) or None if failed
        """
        psapi = ctypes.windll.psapi

        class MODULEINFO(ctypes.Structure):
            _fields_ = [
                ("lpBaseOfDll", ctypes.c_void_p),
                ("SizeOfImage", wintypes.DWORD),
                ("EntryPoint", ctypes.c_void_p),
            ]

        module_info = MODULEINFO()
        result = psapi.GetModuleInformation(
            self._process_handle,
            wintypes.HMODULE(hmodule),
            ctypes.byref(module_info),
            ctypes.sizeof(module_info)
        )

        if not result:
            error = ctypes.windll.kernel32.GetLastError()
            logger.error(f"GetModuleInformation failed, error: {error}")
            return None

        return int(module_info.lpBaseOfDll), module_info.SizeOfImage

    def _read_memory_range(self, handle, base_addr: int, size: int) -> Optional[bytes]:
        """
        Read a range of memory from the process.

        Args:
            handle: Process handle
            base_addr: Starting address
            size: Number of bytes to read

        Returns:
            Bytes read, or None if failed
        """
        kernel32 = ctypes.windll.kernel32
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)

        success = kernel32.ReadProcessMemory(
            handle,
            ctypes.c_void_p(base_addr),
            buffer,
            size,
            ctypes.byref(bytes_read)
        )

        if not success:
            error = kernel32.GetLastError()
            logger.error(f"ReadProcessMemory failed at 0x{base_addr:08X}, error: {error}")
            return None

        return buffer.raw[:bytes_read.value]

    def _find_pattern_with_wildcards(self, data: bytes, pattern: bytes) -> int:
        """
        Find pattern in data, supporting wildcards (0x2E '.').

        Args:
            data: The data to search in
            pattern: The pattern to search for ('.' acts as wildcard)

        Returns:
            Offset where pattern found, or -1 if not found
        """
        if not pattern:
            return -1

        pattern_len = len(pattern)
        data_len = len(data)

        if pattern_len > data_len:
            return -1

        # Convert pattern to bytearray for mutable comparison
        pattern_bytes = bytearray(pattern)

        for i in range(data_len - pattern_len + 1):
            match = True
            for j in range(pattern_len):
                # 0x2E is '.' which acts as wildcard
                if pattern_bytes[j] != 0x2E and data[i + j] != pattern_bytes[j]:
                    match = False
                    break
            if match:
                return i

        return -1
