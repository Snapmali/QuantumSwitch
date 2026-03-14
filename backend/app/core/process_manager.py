"""Process management for finding and accessing the game process."""
import ctypes
from ctypes import wintypes
from typing import Optional, List, Dict
import psutil
from app.utils.logger import logger
from app.config import settings


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
        self._nc_address: Optional[int] = None
        self._eden_checked = False
        self._dll_list_cache: Optional[Dict[str, int]] = None

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
            self._nc_address = None
            self._eden_checked = False
            return False

        # Get base address from the opened handle and cache DLL list
        modules = self._enum_modules(self._process_handle)
        if modules:
            self._base_address = modules[0]
            logger.info(f"Found process {self.process_name} (PID: {pid}) at base address 0x{self._base_address:08X}")
            # Build DLL cache from already enumerated modules
            self._dll_list_cache = self._build_dll_list_from_modules(modules)
        else:
            self._base_address = 0x140000000
            self._dll_list_cache = {}
            logger.warning(f"Could not enumerate modules, using default base address 0x{self._base_address:08X}")

        nc_dll = self.get_dll(settings.NEW_CLASSICS_DLL)
        if nc_dll:
            self._nc_address = nc_dll
            logger.info(f"Found New Classics DLL at address 0x{self._nc_address:08X}")
        else:
            logger.debug("New Classics DLL not found")

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
        self._nc_address = None
        self._eden_checked = False
        self._dll_list_cache = None

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

    def _build_dll_list_from_modules(self, modules: List[int]) -> Dict[str, int]:
        """
        Build DLL list dictionary from already enumerated module handles.

        Args:
            modules: List of HMODULE values from _enum_modules

        Returns:
            Dictionary mapping module file paths to HMODULE values
        """
        output: Dict[str, int] = {}
        psapi = ctypes.windll.psapi

        for hmodule in modules:
            path_buffer = ctypes.create_unicode_buffer(1024)
            size = psapi.GetModuleFileNameExW(
                self._process_handle,
                hmodule,
                path_buffer,
                1024
            )
            if size > 0:
                output[path_buffer.value] = hmodule

        return output

    def get_process_info(self) -> Optional[dict]:
        """Get process information dictionary."""
        if not self.is_attached:
            if not self.attach():
                return None
        return {
            "pid": self._process_id,
            "base_address": self._base_address,
        }

    def get_dll_list(self, filter_name: Optional[str] = None) -> Dict[str, int]:
        """
        Get a mapping of module file paths to their handles.
        Uses cached list if available (populated during attach).

        Args:
            filter_name: Optional string to filter module names (case-insensitive)

        Returns:
            Dictionary mapping module file paths to HMODULE values
        """
        # Use cached list if available
        if self._dll_list_cache is None:
            # Build from scratch using already enumerated modules
            modules = self.get_modules()
            dll_list = self._build_dll_list_from_modules(modules)
        else:
            dll_list = self._dll_list_cache

        if filter_name is not None:
            filter_lower = filter_name.lower()
            dll_list = {
                name: hmodule for name, hmodule in dll_list.items()
                if filter_lower in name.lower()
            }

        return dll_list

    def get_dll(self, name: str) -> Optional[int]:
        """
        Find a specific DLL by name (case-insensitive substring match).

        Args:
            name: The DLL name to search for (e.g., "divamodloader")

        Returns:
            HMODULE value (base address) of the found DLL

        Raises:
            DllNotFoundException: If the DLL is not found in the process
        """
        name_lower = name.lower()
        dll_list = self.get_dll_list()

        for module_path, hmodule in dll_list.items():
            if name_lower in module_path.lower():
                return hmodule

        return None

    def get_dll_info(self) -> List[dict]:
        """
        Get detailed information about all loaded modules.

        Returns:
            List of dictionaries containing module information
        """
        modules = []
        psapi = ctypes.windll.psapi

        for hmodule in self.get_modules():
            # Get module file name
            path_buffer = ctypes.create_unicode_buffer(1024)
            size = psapi.GetModuleFileNameExW(
                self._process_handle,
                hmodule,
                path_buffer,
                1024
            )

            if size > 0:
                modules.append({
                    "path": path_buffer.value,
                    "base_address": hmodule,
                    "base_address_hex": f"0x{hmodule:08X}"
                })

        return modules
