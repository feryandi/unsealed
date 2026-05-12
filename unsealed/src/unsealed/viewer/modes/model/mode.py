"""ModelMode — viewer mode for .ms1 / .act files (skinned/animated meshes)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, cast

from ..base import BaseMode
from .camera import OrbitCamera
from .panels import ModelControlPanel
from .pipeline import ModelViewerPipeline
from .scene import ModelScene

if TYPE_CHECKING:
  from ...app.components.animation import AnimationComponent
  from ...app.context import ViewerContext
  from ...app.world import AppWorld
  from ...camera import Camera
  from ...rendering import HudPanel
  from ...scenes import ViewerScene


class ModelMode(BaseMode):
  name = "model"
  extensions = (".ms1", ".act")
  scene_type = ModelScene

  def decode(
    self, path: Path, shader_cache: Optional[dict] = None
  ) -> "ViewerScene":
    return ModelViewerPipeline().run(path, shader_cache)

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = OrbitCamera()
    if isinstance(scene, ModelScene) and scene.bounds_radius > 0:
      cam.fit_bounds(scene.bounds_center, scene.bounds_radius)
    return cam

  def build_hud_panels(
    self,
    ctx: "ViewerContext",
    anim: "AnimationComponent",
    selected_idx: Optional[int],
    q3_enabled: bool = True,
  ) -> "List[HudPanel]":
    from ...app.panels import AnimationListPanel, PlaybackControlPanel

    scene = cast(ModelScene, ctx.scene)
    panels: "List[HudPanel]" = [ModelControlPanel(scene, ctx.path, q3_enabled)]
    primary = anim.primary
    if primary is not None and primary.enabled and scene.entities:
      entity = scene.entities[anim.primary_entity]  # type: ignore[index]
      group = entity.animation_groups[primary.group_idx]
      anim_names = [g.name for g in entity.animation_groups]
      panels.append(AnimationListPanel(anim_names, primary.group_idx))
      panels.append(
        PlaybackControlPanel(
          group_name=group.name,
          current_time=primary.time,
          duration=group.duration,
          playing=primary.playing,
        )
      )
    return panels

  def on_key(self, key: int, app: "AppWorld") -> None:
    from pygame.locals import (
      K_BACKSPACE,
      K_DOWN,
      K_LEFT,
      K_RIGHT,
      K_SPACE,
      K_UP,
      K_w,
    )

    from ...app.constants import _SCRUB_STEP

    if key == K_w:
      app._wireframe = not app._wireframe
    elif key == K_SPACE:
      app.anim_toggle_play()
    elif key == K_BACKSPACE:
      app.anim_stop()
    elif key == K_UP:
      primary = app.scene.anim.primary
      ctx = app.scene.context
      if primary is not None and primary.enabled and ctx is not None:
        scene = cast(ModelScene, ctx.scene)
        if scene.entities:
          n = len(scene.entities[app.scene.anim.primary_entity].animation_groups)  # type: ignore[index]
          if n > 0:
            app.anim_select((primary.group_idx - 1) % n)
    elif key == K_DOWN:
      primary = app.scene.anim.primary
      ctx = app.scene.context
      if primary is not None and primary.enabled and ctx is not None:
        scene = cast(ModelScene, ctx.scene)
        if scene.entities:
          n = len(scene.entities[app.scene.anim.primary_entity].animation_groups)  # type: ignore[index]
          if n > 0:
            app.anim_select((primary.group_idx + 1) % n)
    elif key == K_LEFT:
      app.anim_scrub(-_SCRUB_STEP)
    elif key == K_RIGHT:
      app.anim_scrub(_SCRUB_STEP)

  def on_mouse_down(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None:
    if button == 3:
      app._set_capture(True)

  def on_mouse_up(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None:
    if button == 3:
      app._set_capture(False)

  def on_mouse_motion(self, dx: int, dy: int, app: "AppWorld") -> None:
    cam = cast(OrbitCamera, app._camera)
    if app._btn[2] or app._btn[0]:
      cam.orbit(-dx, dy)
    elif app._btn[1]:
      cam.pan(-dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, app: "AppWorld") -> None:
    cast(OrbitCamera, app._camera).zoom(direction)
