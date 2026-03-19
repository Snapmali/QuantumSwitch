"""Logging configuration using loguru."""
import sys
from pathlib import Path
from loguru import logger

# Remove default handler
logger.remove()


def _get_debug_mode() -> bool:
    """Lazy import settings to avoid circular dependency."""
    try:
        from ..config import settings
        return settings.DEBUG
    except ImportError:
        return False


# Add console handler with colored output
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if _get_debug_mode() else "INFO"
)

# Add file handler for persistent logs
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logger.add(
    log_dir / "app.log",
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    encoding="utf-8",
    enqueue=True
)

__all__ = ["logger"]
