from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class ProcessModule:
    name: str
    path: Path
    hmodule: int