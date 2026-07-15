from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WindowComponent:
  width: int = 1280
  height: int = 720
  running: bool = False
