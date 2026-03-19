from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict

@dataclass
class ProcessModule:
    name: str
    path: Path
    hmodule: int
    pattern_cache: Dict[str, int] = field(default_factory=dict)