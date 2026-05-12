"""MapConfig — RTS-style map viewer: MapCamera, map HUD, pan/orbit mouse."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, cast

from .base import SceneConfig

if TYPE_CHECKING:
  from ...app.components.animation import AnimationComponent
  from ...camera import Camera
  from ...rendering import HudPanel
  from ...scenes import ViewerScene
  from ..context import ViewerContext
  from ..world import AppWorld


class MapConfig(SceneConfig):
  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    from ...camera import MapCamera
    from ...scenes import MapScene

    cam = MapCamera()
    cam.fit_map()
    if isinstance(scene, MapScene) and scene.terrain_heights is not None:
      cam.set_heightmap(scene.terrain_heights, 512, 512)
    return cam

  def build_hud_panels(
    self,
    ctx: "ViewerContext",
    anim: "AnimationComponent",
    selected_idx: Optional[int],
    q3_enabled: bool = True,
  ) -> "List[HudPanel]":
    from ...scenes import MapScene
    from ..panels import MapControlPanel, ObjectDetailPanel

    scene = cast(MapScene, ctx.scene)
    panels: List[HudPanel] = [MapControlPanel(scene, ctx.path, q3_enabled)]
    if selected_idx is not None and 0 <= selected_idx < len(scene.meshes):
      panels.append(ObjectDetailPanel(scene.meshes[selected_idx]))
    return panels

  def on_mouse_down(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None:
    if button == 1:
      app._lmb_down_pos = pos

  def on_mouse_up(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None:
    if button == 1 and app._lmb_down_pos is not None:
      ox, oy = app._lmb_down_pos
      cx, cy = pos
      if (cx - ox) ** 2 + (cy - oy) ** 2 <= 25:  # ≤ 5 px radius
        app._do_pick(cx, cy)
      app._lmb_down_pos = None

  def on_mouse_motion(self, dx: int, dy: int, app: "AppWorld") -> None:
    from ...camera import MapCamera

    cam = cast(MapCamera, app._camera)
    if app._btn[2]:
      cam.orbit(dx, -dy)
    elif app._btn[0]:
      cam.pan_mouse(dx, -dy)
    elif app._btn[1]:
      cam.pan_mouse(dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, app: "AppWorld") -> None:
    from ...camera import MapCamera

    cast(MapCamera, app._camera).zoom(direction)
