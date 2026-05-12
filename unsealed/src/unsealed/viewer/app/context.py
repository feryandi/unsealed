"""ViewerContext: per-file loaded-state container for the viewer app.

Encapsulates the scene, camera, config, and path for one loaded file.
ViewerContext.load() decodes the file, picks the matching SceneConfig, and
uses the config to create the appropriate camera.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..camera import Camera
from ..scenes import ImageScene, MapScene, ViewerScene
from .scenes import ImageConfig, MapConfig, ModelConfig, SceneConfig


@dataclass
class ViewerContext:
  """Holds the scene, camera, config and path for one loaded file."""

  scene: ViewerScene
  camera: Camera
  config: SceneConfig
  path: Path

  # ── public factory ───────────────────────────────────────────────────────-

  @classmethod
  def load(
    cls,
    path: Path,
    win_w: int,
    win_h: int,
    shader_cache: Optional[Dict[str, Any]] = None,
  ) -> "ViewerContext":
    """Decode *path*, pick the matching config/camera, and return context."""
    scene = cls._decode_scene(path, shader_cache)
    config = cls._pick_config(scene)
    camera = config.make_camera(scene, win_w, win_h)
    return cls(scene=scene, camera=camera, config=config, path=path)

  # ── scene decoding ───────────────────────────────────────────────────────

  @staticmethod
  def _decode_scene(
    path: Path,
    shader_cache: Optional[Dict[str, Any]] = None,
  ) -> ViewerScene:
    """Dispatch to the right pipeline based on file extension."""
    from ..pipeline import MapViewerPipeline, ModelViewerPipeline, TexViewerPipeline

    ext = path.suffix.lower()
    if ext in (".tex", ".te1"):
      return TexViewerPipeline().run(path)
    if ext == ".map":
      return MapViewerPipeline().run(path, shader_cache)
    return ModelViewerPipeline().run(path, shader_cache)

  # ── config selection ─────────────────────────────────────────────────────

  @staticmethod
  def _pick_config(scene: ViewerScene) -> SceneConfig:
    if isinstance(scene, ImageScene):
      return ImageConfig()
    if isinstance(scene, MapScene):
      return MapConfig()
    return ModelConfig()
