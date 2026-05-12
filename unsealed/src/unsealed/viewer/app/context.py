"""ViewerContext: per-file loaded-state container for the viewer app.

Encapsulates the scene, camera, mode, and path for one loaded file.
ViewerContext.load() picks a Mode by file extension, decodes the file
via the Mode, and asks the Mode to construct the camera.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
  from ..camera import Camera
  from ..modes import Mode
  from ..scenes import ViewerScene


@dataclass
class ViewerContext:
  """Holds the scene, camera, mode and path for one loaded file."""

  scene: "ViewerScene"
  camera: "Camera"
  mode: "Mode"
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
    """Pick the matching Mode by extension, decode, build camera."""
    from ..modes import for_path

    mode = for_path(path)
    scene = mode.decode(path, shader_cache)
    camera = mode.make_camera(scene, win_w, win_h)
    return cls(scene=scene, camera=camera, mode=mode, path=path)
