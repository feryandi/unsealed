from __future__ import annotations

from dataclasses import dataclass, field

from ...rendering import Renderer


@dataclass
class RenderComponent:
  renderer: Renderer = field(default_factory=Renderer)
  wireframe: bool = False
  q3_enabled: bool = True
