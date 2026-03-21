"""服务注册和引导模块。"""
from .game_status_processor import GameStatusProcessor
from ..config import settings
from ..utils.logger import logger
from .container import get_container
from .game_dir_processor import detect_game_directories
from .process_manager import ProcessManager
from .memory_operator import MemoryOperator
from .song_selector import SongSelector
from .pvdb_parser import PvdbParser
from .alias_manager import AliasManager
from .favorites_manager import FavoritesManager


def _init_game_directories() -> None:
    """初始化游戏目录，优先使用 .env 中配置的 GAME_MODS_DIRECTORY"""
    game_dir, mods_dir = detect_game_directories(
        game_id=settings.GAME_ID,
        configured_mods_dir=settings.GAME_MODS_DIRECTORY,
        configured_game_dir=settings.GAME_DIRECTORY
    )

    if game_dir is not None:
        settings.GAME_DIRECTORY = game_dir
        logger.info(f"Game directory: {game_dir}")
    else:
        logger.warning("Could not determine game directory from .env or registry")

    if mods_dir is not None:
        settings.GAME_MODS_DIRECTORY = mods_dir
        logger.info(f"Mods directory: {mods_dir}")

    # Validate directories exist
    if game_dir is not None and not game_dir.exists():
        logger.warning(f"Game directory does not exist: {game_dir}")

    if mods_dir is not None and not mods_dir.exists():
        logger.warning(f"Mods directory does not exist: {mods_dir}")


def bootstrap_services() -> None:
    """
    引导所有服务，注册到依赖注入容器。

    调用时机: 应用启动时（main.py 的 lifespan 中）
    """
    container = get_container()

    logger.info("Bootstrapping services...")

    # 初始化游戏目录
    _init_game_directories()

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

    # 注册 GameStatusProcessor（依赖 MemoryOperator）
    def create_game_status_processor() -> GameStatusProcessor:
        pm = container.resolve(ProcessManager)
        mem = container.resolve(MemoryOperator)
        return GameStatusProcessor(pm, mem)

    container.register_singleton(GameStatusProcessor, create_game_status_processor)

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

    # 注册 AliasManager
    container.register_singleton(
        AliasManager,
        lambda: AliasManager(data_dir="data")
    )

    # 注册 FavoritesManager
    container.register_singleton(
        FavoritesManager,
        lambda: FavoritesManager(data_dir="data")
    )

    logger.info("Services bootstrapped successfully")


def get_process_manager() -> ProcessManager:
    """获取 ProcessManager 实例"""
    return get_container().resolve(ProcessManager)


def get_memory_operator() -> MemoryOperator:
    """获取 MemoryOperator 实例"""
    return get_container().resolve(MemoryOperator)


def get_game_status_processor() -> GameStatusProcessor:
    """获取 GameStatusProcessor 实例"""
    return get_container().resolve(GameStatusProcessor)


def get_song_selector() -> SongSelector:
    """获取 SongSelector 实例"""
    return get_container().resolve(SongSelector)


def get_pvdb_parser() -> PvdbParser:
    """获取 PvdbParser 实例"""
    return get_container().resolve(PvdbParser)


def get_alias_manager() -> AliasManager:
    """获取 AliasManager 实例"""
    return get_container().resolve(AliasManager)


def get_favorites_manager() -> FavoritesManager:
    """获取 FavoritesManager 实例"""
    return get_container().resolve(FavoritesManager)
