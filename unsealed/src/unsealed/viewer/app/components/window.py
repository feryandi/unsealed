from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class WindowComponent:
    width: int = 1280
    height: int = 720
    running: bool = False
    font: Optional[object] = None
