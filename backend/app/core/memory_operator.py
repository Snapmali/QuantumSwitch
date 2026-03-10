"""Memory operations for reading and writing process memory."""
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple
from app.utils.logger import logger
from app.config import settings


class MemoryOperator:
    """Handles reading from and writing to process memory."""

    def __init__(self, process_manager):
        self._pm = process_manager
        self._eden_offset: Optional[int] = None
        self._is_eden_version: bool = False

    @property
    def eden_offset(self) -> int:
        """Get the Eden offset (cached)."""
        if self._eden_offset is None or not self._pm.eden_checked:
            self._detect_eden_version()
        return self._eden_offset

    @property
    def is_eden_version(self) -> bool:
        """Check if running Eden version."""
        if self._eden_offset is None or not self._pm.eden_checked:
            self._detect_eden_version()
        return self._is_eden_version

    def _get_handle(self) -> Optional[wintypes.HANDLE]:
        """Get process handle from manager."""
        return self._pm.get_handle()

    def _detect_eden_version(self) -> None:
        """
        Detect if running Eden version by checking LAST_SELECT_PVID_ADDR.
        According to the documentation:
        - Check address: 0x12B6350 (LAST_SELECT_PVID_ADDR)
        - If value is 0, apply offset 0x105F460
        """
        # Ensure we have a valid handle first
        handle = self._pm.get_handle()
        if not handle:
            logger.warning("Eden detection: No process handle available, defaulting to no offset")
            self._eden_offset = 0
            self._is_eden_version = False
            return

        # Read the value at LAST_SELECT_PVID_ADDR (0x12B6350) and avoid triggering eden_offset property again
        check_addr = settings.LAST_SELECT_PVID_ADDR
        value = self.read_int32(check_addr, use_offset=True, skip_eden=True)

        if value is None:
            logger.warning(f"Eden detection: check_addr=0x{check_addr:08X}, FAILED to read value (None)")
        else:
            logger.info(f"Eden detection: check_addr=0x{check_addr:08X}, read_value={value}, condition=value==0, match={value == 0}")

        # According to documentation: if value is 0, apply Eden offset 0x105F460
        if value is not None and value == 0:
            self._eden_offset = settings.EDEN_OFFSET
            self._is_eden_version = True
            logger.info(f"Detected Eden version (offset: +0x{self._eden_offset:X})")
        else:
            self._eden_offset = 0
            self._is_eden_version = False
            logger.info("Detected standard version (no offset)")

        self._pm.set_eden_checked()

    def _get_data_address(self, base_addr: int, skip_eden: bool = False) -> int:
        """
        Get the actual data address, accounting for base address and Eden offset.
        Control addresses are not affected by base address or Eden offset.

        Args:
            base_addr: The base address from configuration
            skip_eden: If True, skip adding Eden offset (used during Eden detection)
        """
        eden_offset = 0
        if not skip_eden and base_addr:
            # Use _eden_offset directly to avoid triggering detection
            eden_offset += self.eden_offset or 0

        # Control addresses (CHANGE_SONG_SELECT, START_CHANGE) are absolute addresses
        if base_addr in [settings.CHANGE_SONG_SELECT_ADDR, settings.START_CHANGE_ADDR]:
            eden_offset = 0

        base = self._pm.base_address or 0

        # Data addresses: base + offset + eden_offset
        result = base_addr + base + eden_offset
        logger.debug(f"Applying offset: 0x{base_addr:08X} -> 0x{result:08X} (+{base} +{eden_offset})")
        return result

    def read_memory(self, address: int, size: int) -> Optional[bytes]:
        """
        Read raw bytes from process memory.

        Args:
            address: Memory address to read from
            size: Number of bytes to read

        Returns:
            Bytes read, or None if failed
        """
        handle = self._get_handle()
        if not handle:
            return None

        kernel32 = ctypes.windll.kernel32
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)

        success = kernel32.ReadProcessMemory(
            handle,
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(bytes_read)
        )

        if not success:
            error = kernel32.GetLastError()
            logger.error(f"ReadProcessMemory failed at 0x{address:08X}, error: {error}")
            if error == 5:
                logger.error("错误代码5: 访问被拒绝 - 请以管理员身份运行后端")
            elif error == 6:
                logger.error("错误代码6: 无效句柄")
            elif error == 299:
                logger.error("错误代码299: 部分复制 - 地址可能无效")
            return None

        return buffer.raw[:bytes_read.value]

    def write_memory(self, address: int, data: bytes) -> bool:
        """
        Write raw bytes to process memory.

        Args:
            address: Memory address to write to
            data: Bytes to write

        Returns:
            True if successful, False otherwise
        """
        handle = self._get_handle()
        if not handle:
            return False

        kernel32 = ctypes.windll.kernel32
        buffer = ctypes.create_string_buffer(data)
        bytes_written = wintypes.SIZE(0)

        # Change memory protection to allow writing
        old_protect = wintypes.DWORD(0)
        size = len(data)

        success = kernel32.VirtualProtectEx(
            handle,
            ctypes.c_void_p(address),
            size,
            0x40,  # PAGE_EXECUTE_READWRITE
            ctypes.byref(old_protect)
        )

        if not success:
            error = kernel32.GetLastError()
            logger.warning(f"VirtualProtectEx failed at 0x{address:08X}, error: {error}")
            return False

        try:
            success = kernel32.WriteProcessMemory(
                handle,
                ctypes.c_void_p(address),
                buffer,
                size,
                ctypes.byref(bytes_written)
            )

            if not success:
                error = kernel32.GetLastError()
                logger.error(f"WriteProcessMemory failed at 0x{address:08X}, error: {error}")
                return False

            return True

        finally:
            # Restore original protection
            kernel32.VirtualProtectEx(
                handle,
                ctypes.c_void_p(address),
                size,
                old_protect.value,
                ctypes.byref(old_protect)
            )

    def read_int32(self, address: int, use_offset: bool = True, skip_eden: bool = False) -> Optional[int]:
        """Read a 32-bit integer from memory."""
        original_address = address
        if use_offset:
            address = self._get_data_address(address, skip_eden=skip_eden)

        data = self.read_memory(address, 4)
        if data is None:
            return None
        return int.from_bytes(data, byteorder='little', signed=True)

    def read_int8(self, address: int, use_offset: bool = True, skip_eden: bool = False) -> Optional[int]:
        """Read an 8-bit integer from memory."""
        original_address = address
        if use_offset:
            address = self._get_data_address(address, skip_eden=skip_eden)

        data = self.read_memory(address, 1)
        if data is None:
            return None
        return int.from_bytes(data, byteorder='little', signed=True)

    def write_int32(self, address: int, value: int, use_offset: bool = True, skip_eden: bool = False) -> bool:
        """Write a 32-bit integer to memory."""
        if use_offset:
            address = self._get_data_address(address, skip_eden=skip_eden)

        data = value.to_bytes(4, byteorder='little', signed=True)
        return self.write_memory(address, data)

    def write_int8(self, address: int, value: int, use_offset: bool = True, skip_eden: bool = False) -> bool:
        """Write an 8-bit integer to memory."""
        if use_offset:
            address = self._get_data_address(address, skip_eden=skip_eden)

        data = value.to_bytes(1, byteorder='little', signed=True)
        return self.write_memory(address, data)

    def get_game_state(self) -> Optional[int]:
        """
        Read the current game state.
        Returns the value from the START_CHANGE address.
        """
        return self.read_int32(settings.START_CHANGE_ADDR, skip_eden=True)

    def get_current_selection(self) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Get current song selection data.

        Returns:
            Tuple of (pvid, sort_id, difficulty) or (None, None, None) if failed
        """
        pvid = self.read_int32(settings.LAST_SELECT_PVID_ADDR)
        sort_id = self.read_int32(settings.LAST_SELECT_SORT_ADDR)
        diff_type = self.read_int32(settings.LAST_SELECT_DIFF_TYPE_ADDR)
        diff_level = self.read_int32(settings.LAST_SELECT_DIFF_LEVEL_ADDR)

        logger.debug(f"pvid: {pvid}, sort_id: {sort_id}, diff_type: {diff_type}, diff_level: {diff_level}")

        return pvid, sort_id, diff_type
