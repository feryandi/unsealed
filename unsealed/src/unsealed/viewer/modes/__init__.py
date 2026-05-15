"""
Mode plugin registry. Importing this module auto-registers all built-in modes.

A new file format becomes a viewer mode by adding `viewer/modes/<name>/`
(with mode.py, scene.py, pipeline.py, camera.py, panels.py) and adding the
`register(...)` call below.
"""

from __future__ import annotations

from .base import (
  MODES,
  AnimationPolicy,
  BaseMode,
  Mode,
  RenderExtension,
  RenderPhase,
  for_path,
  for_scene,
  register,
)
from .context import ModeContext
from .image import ImageMode, ImageScene
from .map import MapMode, MapScene
from .men import MenMode, MenScene
from .model import ModelMode, ModelScene
from .spr import SprMode, SprScene

register(ModelMode())
register(MapMode())
register(ImageMode())
register(SprMode())
register(MenMode())

__all__ = [
  "AnimationPolicy",
  "BaseMode",
  "MODES",
  "Mode",
  "ModeContext",
  "RenderExtension",
  "RenderPhase",
  "for_path",
  "for_scene",
  "register",
  "ImageMode",
  "ImageScene",
  "MapMode",
  "MapScene",
  "MenMode",
  "MenScene",
  "ModelMode",
  "ModelScene",
  "SprMode",
  "SprScene",
]
