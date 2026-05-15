"""ImageMode — viewer mode for .tex / .te1 texture files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, cast

from imgui_bundle import imgui

from ..base import BaseMode, RenderExtension
from .camera import ImageCamera
from .extensions import ImageExtension
from .pipeline import TexViewerPipeline
from .scene import ImageScene

if TYPE_CHECKING:
  from ...app.world import AppWorld
  from ...camera import Camera
  from ...scenes import ViewerScene
  from ..context import ModeContext


class ImageMode(BaseMode):
  name = "image"
  extensions = (".tex", ".te1")
  scene_type = ImageScene

  def __init__(self) -> None:
    self._render_extensions: List[RenderExtension] = [ImageExtension()]

  def render_extensions(self) -> "Iterable[RenderExtension]":
    return self._render_extensions

  def decode(
    self, path: Path, shader_cache: Optional[dict] = None
  ) -> "ViewerScene":
    return TexViewerPipeline().run(path)

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = ImageCamera()
    if isinstance(scene, ImageScene):
      cam.fit_image(scene.image_w, scene.image_h, win_w, win_h)
    return cam

  def draw_hud(self, world: "AppWorld") -> None:
    ctx = world.scene.context
    if ctx is None:
      return
    scene = cast(ImageScene, ctx.scene)
    cam = cast(ImageCamera, ctx.camera)

    imgui.set_next_window_pos((10, 10), imgui.Cond_.first_use_ever.value)
    imgui.begin("Image")
    imgui.text(f"File : {ctx.path.name}")
    imgui.text(f"Size : {scene.image_w} × {scene.image_h} px")
    imgui.text(f"Zoom : {int(cam.zoom * 100)}%")
    imgui.separator()
    if imgui.button("Open File"):
      world.open_dialog()
    imgui.separator()
    imgui.text_disabled("Drag : pan   Scroll : zoom")
    imgui.text_disabled("R / F : fit   O : open   Esc : quit")
    imgui.end()

  def on_mouse_motion(self, dx: int, dy: int, mctx: "ModeContext") -> None:
    if any(mctx.buttons):
      cast(ImageCamera, mctx.camera).pan(dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, mctx: "ModeContext") -> None:
    cast(ImageCamera, mctx.camera).zoom_step(
      direction, mx, my, mctx.width, mctx.height
    )
