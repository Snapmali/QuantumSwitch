"""服务注册和引导模块。"""
from ..config import settings
from ..utils.logger import logger
from .container import get_container
from .process_manager import ProcessManager
from .memory_operator import MemoryOperator
from .song_selector import SongSelector
from .pvdb_parser import PvdbParser


def bootstrap_services() -> None:
    """
    引导所有服务，注册到依赖注入容器。

    调用时机: 应用启动时（main.py 的 lifespan 中）
    """
    container = get_container()

    logger.info("Bootstrapping services...")

    # 注册 ProcessManager
    container.register_singleton(
        ProcessManager,
        lambda: ProcessManager(settings.GAME_PROCESS_NAME)
    )

    # 注册 MemoryOperator（依赖 ProcessManager）
    def create_memory_operator() -> MemoryOperator:
        pm = container.resolve(ProcessManager)
        return MemoryOperator(pm)

    container.register_singleton(MemoryOperator, create_memory_operator)

    # 注册 SongSelector（依赖 MemoryOperator）
    def create_song_selector() -> SongSelector:
        mem = container.resolve(MemoryOperator)
        return SongSelector(mem)

    container.register_singleton(SongSelector, create_song_selector)

    # 注册 PvdbParser
    container.register_singleton(
        PvdbParser,
        lambda: PvdbParser(mods_directory=settings.GAME_MODS_DIRECTORY)
    )

    logger.info("Services bootstrapped successfully")


def get_process_manager() -> ProcessManager:
    """便捷函数: 获取 ProcessManager 实例。"""
    return get_container().resolve(ProcessManager)


def get_memory_operator() -> MemoryOperator:
    """便捷函数: 获取 MemoryOperator 实例。"""
    return get_container().resolve(MemoryOperator)


def get_song_selector() -> SongSelector:
    """便捷函数: 获取 SongSelector 实例。"""
    return get_container().resolve(SongSelector)


def get_pvdb_parser() -> PvdbParser:
    """便捷函数: 获取 PvdbParser 实例。"""
    return get_container().resolve(PvdbParser)
