"""Process management for finding and accessing the game process."""
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple
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
        self._eden_checked = False

    @property
    def is_attached(self) -> bool:
        """Check if currently attached to a process."""
        if self._process_handle is None:
            return False
        # Handle both HANDLE objects (with .value) and raw integers
        if isinstance(self._process_handle, int):
            return self._process_handle != 0
        return self._process_handle.value != 0

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

    def find_process(self) -> Optional[Tuple[int, int]]:
        """
        Find the game process by name.

        Returns:
            Tuple of (process_id, base_address) if found, None otherwise
        """
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if proc.info['name'] == self.process_name:
                    pid = proc.info['pid']

                    # Check whether the current process is a brand-new process
                    if self.is_attached and self._process_id != pid:
                        self.detach()

                    # Get base address using psutil
                    p = psutil.Process(pid)
                    # For 64-bit Windows, the base address is typically 0x140000000
                    # We need to enumerate modules to find the actual base
                    base_addr = self._get_module_base_address(pid)
                    logger.info(f"Found process {self.process_name} (PID: {pid}) at base address 0x{base_addr:08X}")
                    return pid, base_addr
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if self.is_attached:
            self.detach()
        return None

    def _get_module_base_address(self, pid: int) -> int:
        """
        Get the base address of the main module for a process.
        Uses Windows API to enumerate modules.
        """
        kernel32 = ctypes.windll.kernel32

        # Open process with query access
        h_process = kernel32.OpenProcess(
            self.PROCESS_QUERY_INFORMATION | self.PROCESS_VM_READ,
            False,
            pid
        )

        if not h_process:
            # Default base address for 64-bit PE executables
            return 0x140000000

        try:
            # Use EnumProcessModules to get module handles
            h_mods = (wintypes.HMODULE * 1024)()
            cb_needed = wintypes.DWORD()

            psapi = ctypes.windll.psapi
            if psapi.EnumProcessModules(h_process, ctypes.byref(h_mods), ctypes.sizeof(h_mods), ctypes.byref(cb_needed)):
                # First module is the executable itself
                return h_mods[0]

        finally:
            kernel32.CloseHandle(h_process)

        return 0x140000000

    def attach(self) -> bool:
        """
        Attach to the game process.

        Returns:
            True if successfully attached, False otherwise
        """
        result = self.find_process()
        if result is None:
            logger.warning(f"Process {self.process_name} not found")
            return False

        if self.is_attached:
            return True

        pid, base_addr = result
        self._process_id = pid
        self._base_address = base_addr

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

    def __enter__(self):
        """Context manager entry."""
        self.attach()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.detach()
        return False

    def get_handle(self) -> Optional[wintypes.HANDLE]:
        """Get the process handle."""
        if not self.is_attached:
            if not self.attach():
                return None
        return self._process_handle

    def get_process_info(self) -> Optional[dict]:
        """Get process information dictionary."""
        if not self.is_attached:
            if not self.attach():
                return None
        return {
            "pid": self._process_id,
            "base_address": self._base_address,
        }

    def set_eden_checked(self):
        """Get whether eden version is checked."""
        self._eden_checked = True
        logger.debug(f"Eden version checked: {self._eden_checked}")
