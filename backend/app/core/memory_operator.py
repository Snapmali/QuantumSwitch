"""Memory operations for reading and writing process memory."""
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

from app.models.process_module import ProcessModule
from app.utils.logger import logger
from app.config import settings, DllSettings


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
        value = self.read_int(check_addr, use_offset=True)

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

    def _get_data_address(
        self,
        base_addr: int,
        apply_eden: bool = False,
        dll: Optional[DllSettings] = None
    ) -> int:
        """
        计算实际内存地址

        Args:
            base_addr: 基础地址或偏移量
            apply_eden: 是否使用 Eden 偏移
            dll: 若指定，则 base_addr 视为该 DLL 的偏移量

        当指定 dll 时:
            最终地址 = DLL 基址 + base_addr (作为偏移)
            忽略进程基址和 Eden 偏移

        未指定 dll 时:
            最终地址 = base_addr + 进程基址 + Eden 偏移
        """
        # DLL 模式：忽略其他偏移，只计算 DLL 偏移
        if dll is not None:
            dll_base: Optional[ProcessModule] = self._pm.get_cached_dll(dll)
            if dll_base is None:
                raise RuntimeError(f"DLL '{dll}' not found in process")

            result = dll_base.hmodule + base_addr
            logger.debug(
                f"DLL address calculation: {dll} "
                f"base=0x{dll_base.hmodule:08X}, offset=0x{base_addr:X}, "
                f"result=0x{result:08X}"
            )
            return result

        # 标准模式：原有的计算逻辑
        eden_offset = 0
        if apply_eden and base_addr:
            eden_offset += self.eden_offset or 0

        base = self._pm.base_address or 0
        result = base_addr + base + eden_offset

        logger.debug(f"Standard address: 0x{base_addr:08X} -> 0x{result:08X} (+{base} +{eden_offset})")
        return result

    def read_memory(
        self,
        address: int,
        size: int,
        use_offset: bool = True,
        apply_eden: bool = False,
        dll: Optional[DllSettings] = None
    ) -> Optional[bytes]:
        """
        Read raw bytes from process memory.

        Args:
            address: Memory address to read from (or DLL offset if dll is specified)
            size: Number of bytes to read
            use_offset: If True, apply address calculations (base/eden/dll). Set to False when entering an absolute address
            apply_eden: If True, apply Eden offset calculation
            dll: If specified, address is treated as an offset from this DLL's base

        Returns:
            Bytes read, or None if failed
        """
        handle = self._get_handle()
        if not handle:
            return None

        # Calculate actual address if needed
        actual_address = address
        if use_offset:
            try:
                actual_address = self._get_data_address(address, apply_eden=apply_eden, dll=dll)
            except RuntimeError as e:
                logger.error(f"Failed to calculate address: {e}")
                return None

        kernel32 = ctypes.windll.kernel32
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)

        success = kernel32.ReadProcessMemory(
            handle,
            ctypes.c_void_p(actual_address),
            buffer,
            size,
            ctypes.byref(bytes_read)
        )

        if not success:
            error = kernel32.GetLastError()
            logger.error(f"ReadProcessMemory failed at 0x{actual_address:08X}, error: {error}")
            if error == 5:
                logger.error("错误代码5: 访问被拒绝 - 请以管理员身份运行后端")
            elif error == 6:
                logger.error("错误代码6: 无效句柄")
            elif error == 299:
                logger.error("错误代码299: 部分复制 - 地址可能无效")
            return None

        return buffer.raw[:bytes_read.value]

    def write_memory(
        self,
        address: int,
        data: bytes,
        use_offset: bool = True,
        apply_eden: bool = False,
        dll: Optional[DllSettings] = None
    ) -> bool:
        """
        Write raw bytes to process memory.

        Args:
            address: Memory address to write to (or DLL offset if dll is specified)
            data: Bytes to write
            use_offset: If True, apply address calculations (base/eden/dll). Set to False when entering an absolute address
            apply_eden: If True, apply Eden offset calculation
            dll: If specified, address is treated as an offset from this DLL's base

        Returns:
            True if successful, False otherwise
        """
        handle = self._get_handle()
        if not handle:
            return False

        # Calculate actual address if needed
        actual_address = address
        if use_offset:
            try:
                actual_address = self._get_data_address(address, apply_eden=apply_eden, dll=dll)
            except RuntimeError as e:
                logger.error(f"Failed to calculate address: {e}")
                return False

        kernel32 = ctypes.windll.kernel32
        buffer = ctypes.create_string_buffer(data)
        bytes_written = wintypes.SIZE(0)

        # Change memory protection to allow writing
        old_protect = wintypes.DWORD(0)
        size = len(data)

        success = kernel32.VirtualProtectEx(
            handle,
            ctypes.c_void_p(actual_address),
            size,
            0x40,  # PAGE_EXECUTE_READWRITE
            ctypes.byref(old_protect)
        )

        if not success:
            error = kernel32.GetLastError()
            logger.warning(f"VirtualProtectEx failed at 0x{actual_address:08X}, error: {error}")
            return False

        try:
            success = kernel32.WriteProcessMemory(
                handle,
                ctypes.c_void_p(actual_address),
                buffer,
                size,
                ctypes.byref(bytes_written)
            )

            if not success:
                error = kernel32.GetLastError()
                logger.error(f"WriteProcessMemory failed at 0x{actual_address:08X}, error: {error}")
                return False

            return True

        finally:
            # Restore original protection
            kernel32.VirtualProtectEx(
                handle,
                ctypes.c_void_p(actual_address),
                size,
                old_protect.value,
                ctypes.byref(old_protect)
            )

    def read_int(
            self,
            address: int,
            size: int = 4,
            signed: bool = False,
            use_offset: bool = True,
            apply_eden: bool = False,
            dll: Optional[DllSettings] = None
    ) -> Optional[int]:
        """
        Read an arbitrary integer from memory.

        Args:
            address: Memory address (or DLL offset if dll is specified)
            size: Number of bytes to read
            signed: Whether the integer is signed
            use_offset: If True, apply address calculations (base/eden/dll). Set to False when entering an absolute address
            apply_eden: If True, apply Eden offset
            dll: If specified, address is treated as an offset from this DLL's base
        """
        logger.debug(f"Reading int from address: 0x{address:08X}, size={size}, dll={dll}")

        data = self.read_memory(address, size, use_offset=use_offset, apply_eden=apply_eden, dll=dll)
        if data is None:
            return None
        return int.from_bytes(data, byteorder='little', signed=signed)

    def write_int(
            self,
            address: int,
            value: int,
            size: int = 4,
            signed: bool = False,
            use_offset: bool = True,
            apply_eden: bool = False,
            dll: Optional[DllSettings] = None
    ) -> bool:
        """
        Write a 32-bit integer to memory.

        Args:
            address: Memory address (or DLL offset if dll is specified)
            value: The integer value to write
            size: Number of bytes to write
            signed: Whether the integer is signed
            use_offset: If True, apply address calculations (base/eden/dll). Set to False when entering an absolute address
            apply_eden: If True, apply Eden offset
            dll: If specified, address is treated as an offset from this DLL's base
        """
        logger.debug(f"Writing int to address: 0x{address:08X}, value={value}, size={size}, dll={dll}")

        data = value.to_bytes(size, byteorder='little', signed=signed)
        return self.write_memory(address, data, use_offset=use_offset, apply_eden=apply_eden, dll=dll)

    def get_game_state(self) -> Optional[int]:
        """
        Read the current game state.
        Returns the value from the START_CHANGE address.
        """
        return self.read_int(settings.START_CHANGE_ADDR)

    def get_last_selection(self) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Get current song selection data.

        Returns:
            Tuple of (pvid, sort_id, difficulty) or (None, None, None) if failed
        """
        pvid = self.read_int(settings.LAST_SELECT_PVID_ADDR, apply_eden=True)
        sort_id = self.read_int(settings.LAST_SELECT_SORT_ADDR, apply_eden=True)
        diff_type = self.read_int(settings.LAST_SELECT_DIFF_TYPE_ADDR, apply_eden=True)
        diff_level = self.read_int(settings.LAST_SELECT_DIFF_LEVEL_ADDR, apply_eden=True)

        logger.debug(f"pvid: {pvid}, sort_id: {sort_id}, diff_type: {diff_type}, diff_level: {diff_level}")

        return pvid, sort_id, diff_type
