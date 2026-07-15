from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class InputComponent:
  btn: List[bool] = field(default_factory=lambda: [False, False, False])
  captured: bool = False
  lmb_down_pos: Optional[tuple[int, int]] = None
