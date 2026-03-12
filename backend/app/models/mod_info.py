"""Mod information data model."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModInfo:
    """Information about a Mod."""
    id: int               # Mod 唯一标识符
    name: str
    path: Optional[str]
    enabled: bool
    author: Optional[str] = None
    version: Optional[str] = None
