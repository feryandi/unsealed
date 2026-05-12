"""SceneConfig — per-scene-type input/camera behaviour.

One concrete subclass per scene type:

  ModelConfig   .ms1, .act   — OrbitCamera + animation keys
  MapConfig     .map         — MapCamera + pan/orbit/picking
  ImageConfig   .tex, .te1   — ImageCamera + pan/zoom
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, cast

from pygame.locals import (
  K_BACKSPACE,
  K_DOWN,
  K_LEFT,
  K_RIGHT,
  K_SPACE,
  K_UP,
  K_w,
)

from ..camera import ImageCamera, MapCamera, OrbitCamera
from ..scenes.image_scene import ImageScene
from ..scenes.map_scene import MapScene
from ..scenes.model_scene import ModelScene
from .constants import _SCRUB_STEP

if TYPE_CHECKING:
  from ..camera import Camera
  from ..scenes.viewer_scene import ViewerScene
  from .world import AppWorld


class SceneConfig(ABC):
  """Abstract base — one concrete subclass per scene type."""

  @abstractmethod
  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera": ...

  # Default no-op handlers; subclasses override only what they need.
  def on_key(self, key: int, app: "AppWorld") -> None: ...
  def on_mouse_down(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None: ...
  def on_mouse_up(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None: ...
  def on_mouse_motion(self, dx: int, dy: int, app: "AppWorld") -> None: ...
  def on_scroll(self, direction: int, mx: int, my: int, app: "AppWorld") -> None: ...


class ModelConfig(SceneConfig):
  """3-D mesh/actor viewer: OrbitCamera, orbit/anim keys."""

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = OrbitCamera()
    if isinstance(scene, ModelScene) and scene.bounds_radius > 0:
      cam.fit_bounds(scene.bounds_center, scene.bounds_radius)
    return cam

  def on_key(self, key: int, app: "AppWorld") -> None:
    if key == K_w:
      app.wireframe = not app.wireframe
    elif key == K_SPACE:
      app.anim_toggle_play()
    elif key == K_BACKSPACE:
      app.anim_stop()
    elif key == K_UP:
      app.anim_cycle(-1)
    elif key == K_DOWN:
      app.anim_cycle(+1)
    elif key == K_LEFT:
      app.anim_scrub(-_SCRUB_STEP)
    elif key == K_RIGHT:
      app.anim_scrub(_SCRUB_STEP)

  def on_mouse_down(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None:
    if button == 3:
      app.set_capture(True)

  def on_mouse_up(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None:
    if button == 3:
      app.set_capture(False)

  def on_mouse_motion(self, dx: int, dy: int, app: "AppWorld") -> None:
    cam = cast(OrbitCamera, app.camera)
    if app.mouse_buttons[2] or app.mouse_buttons[0]:
      cam.orbit(-dx, dy)
    elif app.mouse_buttons[1]:
      cam.pan(-dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, app: "AppWorld") -> None:
    cast(OrbitCamera, app.camera).zoom(direction)


class MapConfig(SceneConfig):
  """RTS-style map viewer: MapCamera, pan/orbit mouse, click-to-pick."""

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = MapCamera()
    cam.fit_map()
    if isinstance(scene, MapScene) and scene.terrain_heights is not None:
      rows, cols = scene.terrain_heights.shape
      cam.set_heightmap(scene.terrain_heights, cols, rows)
    return cam

  def on_mouse_down(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None:
    if button == 1:
      app.lmb_down_pos = pos

  def on_mouse_up(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None:
    if button == 1 and app.lmb_down_pos is not None:
      ox, oy = app.lmb_down_pos
      cx, cy = pos
      if (cx - ox) ** 2 + (cy - oy) ** 2 <= 25:  # ≤ 5 px radius
        app.do_pick(cx, cy)
      app.lmb_down_pos = None

  def on_mouse_motion(self, dx: int, dy: int, app: "AppWorld") -> None:
    cam = cast(MapCamera, app.camera)
    if app.mouse_buttons[2]:
      cam.orbit(dx, -dy)
    elif app.mouse_buttons[0]:
      cam.pan_mouse(dx, -dy)
    elif app.mouse_buttons[1]:
      cam.pan_mouse(dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, app: "AppWorld") -> None:
    cast(MapCamera, app.camera).zoom(direction)


class ImageConfig(SceneConfig):
  """2-D texture viewer: ImageCamera, pan/zoom."""

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = ImageCamera()
    if isinstance(scene, ImageScene):
      cam.fit_image(scene.image_w, scene.image_h, win_w, win_h)
    return cam

  def on_mouse_motion(self, dx: int, dy: int, app: "AppWorld") -> None:
    if any(app.mouse_buttons):
      cast(ImageCamera, app.camera).pan(dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, app: "AppWorld") -> None:
    cast(ImageCamera, app.camera).zoom_step(direction, mx, my, app.width, app.height)
