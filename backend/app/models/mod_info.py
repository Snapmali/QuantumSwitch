"""Mod information data model."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModInfo:
    """Information about a Mod."""
    name: str
    path: str
    enabled: bool
    author: Optional[str] = None
    version: Optional[str] = None
