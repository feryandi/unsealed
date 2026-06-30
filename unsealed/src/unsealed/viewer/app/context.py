"""ViewerContext: per-file loaded-state container for the viewer app.

Encapsulates the scene, camera, mode, and path for one loaded file.
ViewerContext.load() picks a Mode by file extension, decodes the file
via the Mode, and asks the Mode to construct the camera.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
  from ..camera import Camera
  from ..modes import Mode
  from ..scenes import ViewerScene
  from ...vfs import Resource


@dataclass
class ViewerContext:
  """Holds the scene, camera, mode and path for one loaded file."""

  scene: "ViewerScene"
  camera: "Camera"
  mode: "Mode"
  path: "Resource"

  # ── public factory ───────────────────────────────────────────────────────-

  @classmethod
  def load(
    cls,
    res: "Resource",
    win_w: int,
    win_h: int,
    shader_cache: Optional[Dict[str, Any]] = None,
  ) -> "ViewerContext":
    """Pick the matching Mode by extension, decode, build camera."""
    from ..modes import for_path

    mode = for_path(res)
    scene = mode.decode(res, shader_cache)
    camera = mode.make_camera(scene, win_w, win_h)
    return cls(scene=scene, camera=camera, mode=mode, path=res)
