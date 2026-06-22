"""ModelMode — viewer mode for .ms1 / .act files (skinned/animated meshes)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, cast

from imgui_bundle import imgui

from ..base import AnimationPolicy, BaseMode
from .extensions import InfiniteGridExtension
from .camera import OrbitCamera
from .pipeline import ModelViewerPipeline
from .scene import ModelScene

if TYPE_CHECKING:
  from typing import Iterable

  from ...app.world import AppWorld
  from ...camera import Camera
  from ...rendering.extension import RenderExtension
  from ...scenes import ViewerScene
  from ..context import ModeContext


_MODEL_CONTROLS = [
  "RMB drag    : Orbit (locked)",
  "LMB drag    : Orbit (free)",
  "MMB drag    : Pan",
  "Scroll      : Zoom",
  "R / F       : Reset / Fit",
  "W           : Wireframe",
  "O / Esc     : Open / Quit",
]
_ANIM_CONTROLS = [
  "Space       : Play / Pause",
  "Backspace   : Stop",
  "Up / Down   : Change anim",
  "Left/Right  : Scrub (paused)",
]


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

  def draw_hud(self, world: "AppWorld") -> None:
    from ...app.panels import draw_unknowns_window

    ctx = world.scene.context
    if ctx is None:
      return
    scene = cast(ModelScene, ctx.scene)
    self._draw_control_window(world, scene, ctx.path)
    anim = world.scene.anim
    primary = anim.primary
    if primary is not None and primary.enabled and scene.entities:
      entity = scene.entities[anim.primary_entity]  # type: ignore[index]
      self._draw_animation_list(world, entity, primary.group_idx)
      group = entity.animation_groups[primary.group_idx]
      self._draw_playback_window(
        world,
        group_name=group.name,
        current_time=primary.time,
        duration=group.duration,
        playing=primary.playing,
      )
    draw_unknowns_window(scene)

  def _draw_control_window(
    self, world: "AppWorld", scene: ModelScene, path: Path
  ) -> None:
    primary_entity = scene.entities[0] if scene.entities else None
    anim_count = (
      len(primary_entity.animation_groups) if primary_entity is not None else 0
    )

    imgui.set_next_window_pos((10, 10), imgui.Cond_.first_use_ever.value)
    imgui.begin("Model")
    imgui.text(f"File       : {path.name}")
    imgui.text(f"Meshes     : {len(scene.mesh_names)}")
    imgui.text(f"Triangles  : {scene.tri_count:,}")
    if anim_count:
      imgui.text(f"Animations : {anim_count}")
    imgui.separator()
    if imgui.button("Open File"):
      world.open_dialog()
    imgui.same_line()
    shader_label = "Shader: ON" if world.render.q3_enabled else "Shader: OFF"
    if imgui.button(shader_label):
      world.toggle_q3()
    imgui.separator()
    if anim_count:
      for line in _ANIM_CONTROLS:
        imgui.text_disabled(line)
      imgui.separator()
    for line in _MODEL_CONTROLS:
      imgui.text_disabled(line)
    imgui.end()

  def _draw_animation_list(self, world: "AppWorld", entity, current_idx: int) -> None:
    win_w = world.window.width
    imgui.set_next_window_pos((win_w - 280, 10), imgui.Cond_.first_use_ever.value)
    imgui.set_next_window_size((270, 400), imgui.Cond_.first_use_ever.value)
    imgui.begin("Animations")
    # Animation names are Korean (EUC-KR); push the Hangul font just here so
    # they render, while the rest of the UI keeps the default monospace font.
    kr = world.imgui.korean_font
    if kr is not None:
      imgui.push_font(kr, 0.0)  # 0.0 = keep current size
    for i, group in enumerate(entity.animation_groups):
      selected = (i == current_idx)
      if imgui.selectable(f"{group.name}##anim{i}", selected)[0]:
        world.anim_select(i)
    if kr is not None:
      imgui.pop_font()
    imgui.end()

  def _draw_playback_window(
    self,
    world: "AppWorld",
    group_name: str,
    current_time: float,
    duration: float,
    playing: bool,
  ) -> None:
    win_h = world.window.height
    imgui.set_next_window_pos((10, win_h - 80), imgui.Cond_.first_use_ever.value)
    imgui.begin("Playback")
    imgui.text(f"[{group_name}]  {current_time:.2f} / {duration:.2f}s")
    if imgui.button("Pause" if playing else "Play"):
      world.anim_toggle_play()
    imgui.same_line()
    if imgui.button("Stop"):
      world.anim_stop()
    imgui.end()

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
