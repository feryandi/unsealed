"""ModelMode — viewer mode for .ms1 / .act files (skinned/animated meshes)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, cast

from ..base import AnimationPolicy, BaseMode
from .extensions import InfiniteGridExtension
from .camera import OrbitCamera
from .panels import AnimationListPanel, ModelControlPanel, PlaybackControlPanel
from .pipeline import ModelViewerPipeline
from .scene import ModelScene

if TYPE_CHECKING:
  from typing import Iterable

  from ...camera import Camera
  from ...hud_types import HudPanel
  from ...rendering.extension import RenderExtension
  from ...scenes import ViewerScene
  from ..context import ModeContext


class ModelMode(BaseMode):
  name = "model"
  extensions = (".ms1", ".act")
  scene_type = ModelScene
  animation_policy = AnimationPolicy(has_primary=True)

  def __init__(self) -> None:
    self._render_extensions = [InfiniteGridExtension()]

  def render_extensions(self) -> "Iterable[RenderExtension]":
    return self._render_extensions

  def decode(self, path: Path, shader_cache: Optional[dict] = None) -> "ViewerScene":
    return ModelViewerPipeline().run(path, shader_cache)

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = OrbitCamera()
    if isinstance(scene, ModelScene) and scene.bounds_radius > 0:
      cam.fit_bounds(scene.bounds_center, scene.bounds_radius)
    return cam

  def build_hud_panels(self, mctx: "ModeContext") -> "List[HudPanel]":
    ctx = mctx.scene_context
    if ctx is None:
      return []
    scene = cast(ModelScene, ctx.scene)
    panels: "List[HudPanel]" = [ModelControlPanel(scene, ctx.path, mctx.q3_enabled)]
    anim = mctx.anim
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

  def on_key(self, key: int, mctx: "ModeContext") -> None:
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
      mctx.toggle_wireframe()
    elif key == K_SPACE:
      mctx.anim_toggle_play()
    elif key == K_BACKSPACE:
      mctx.anim_stop()
    elif key == K_UP:
      primary = mctx.anim.primary
      ctx = mctx.scene_context
      if primary is not None and primary.enabled and ctx is not None:
        scene = cast(ModelScene, ctx.scene)
        if scene.entities:
          n = len(scene.entities[mctx.anim.primary_entity].animation_groups)  # type: ignore[index]
          if n > 0:
            mctx.anim_select((primary.group_idx - 1) % n)
    elif key == K_DOWN:
      primary = mctx.anim.primary
      ctx = mctx.scene_context
      if primary is not None and primary.enabled and ctx is not None:
        scene = cast(ModelScene, ctx.scene)
        if scene.entities:
          n = len(scene.entities[mctx.anim.primary_entity].animation_groups)  # type: ignore[index]
          if n > 0:
            mctx.anim_select((primary.group_idx + 1) % n)
    elif key == K_LEFT:
      mctx.anim_scrub(-_SCRUB_STEP)
    elif key == K_RIGHT:
      mctx.anim_scrub(_SCRUB_STEP)

  def on_mouse_down(
    self, button: int, pos: tuple[int, int], mctx: "ModeContext"
  ) -> None:
    if button == 3:
      mctx.set_capture(True)

  def on_mouse_up(self, button: int, pos: tuple[int, int], mctx: "ModeContext") -> None:
    if button == 3:
      mctx.set_capture(False)

  def on_mouse_motion(self, dx: int, dy: int, mctx: "ModeContext") -> None:
    cam = cast(OrbitCamera, mctx.camera)
    if mctx.buttons[2] or mctx.buttons[0]:
      cam.orbit(-dx, dy)
    elif mctx.buttons[1]:
      cam.pan(-dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, mctx: "ModeContext") -> None:
    cast(OrbitCamera, mctx.camera).zoom(direction)
