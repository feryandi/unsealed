"""SprMode — viewer mode for .spr sprite-atlas files.

The pipeline yields one SpriteAtlas per referenced texture and a
SpriteRef per declared sprite (plus a sentinel ref for "the whole
atlas"). The HUD navigates atlases × cropped-sprite-indices; the
extension picks UVs from the active SpriteRef at draw time.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, Tuple, cast

from imgui_bundle import imgui

from unsealed.reader.vfs import Resource
from ...sprite_atlas import FULL_ATLAS_IDX
from ..base import BaseMode, RenderExtension
from .camera import SprCamera
from .extensions import SprExtension
from .pipeline import SprViewerPipeline
from .scene import SprScene

if TYPE_CHECKING:
  from ...app.world import AppWorld
  from ...camera import Camera
  from ...scenes import ViewerScene
  from ..context import ModeContext


class SprMode(BaseMode):
  name = "spr"
  extensions = (".spr",)
  scene_type = SprScene

  def __init__(self) -> None:
    self._render_extensions: List[RenderExtension] = [SprExtension()]

  def render_extensions(self) -> "Iterable[RenderExtension]":
    return self._render_extensions

  def decode(self, res: Resource, shader_cache: Optional[dict] = None) -> "ViewerScene":
    return SprViewerPipeline().run(res)

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = SprCamera()
    if isinstance(scene, SprScene):
      w, h = _active_sprite_size(scene)
      if w > 0 and h > 0:
        cam.fit_image(w, h, win_w, win_h)
    return cam

  def draw_hud(self, world: "AppWorld") -> None:
    ctx = world.scene.context
    if ctx is None:
      return
    scene = cast(SprScene, ctx.scene)
    cam = cast(SprCamera, ctx.camera)
    self._draw_control_window(world, scene, cam, ctx.path.name)
    self._draw_atlas_window(world, scene)

  def _draw_control_window(
    self, world: "AppWorld", scene: SprScene, cam: SprCamera, filename: str
  ) -> None:
    active_atlas = scene.active_atlas()
    sprite_label = _active_sprite_label(scene)
    w, h = _active_sprite_size(scene)

    imgui.set_next_window_pos((10, 10), imgui.Cond_.first_use_ever.value)
    imgui.begin("SPR Atlas")
    imgui.text(f"File     : {filename}")
    imgui.text(f"Textures : {len(scene.atlases)}")
    if active_atlas is not None:
      imgui.text(f"Texture  : {active_atlas.name}")
    if sprite_label is not None:
      imgui.text(f"Sprite   : {sprite_label}")
    if w > 0 and h > 0:
      imgui.text(f"Size     : {w} x {h} px")
    imgui.text(f"Zoom     : {int(cam.zoom * 100)}%")
    imgui.separator()
    if imgui.button("Open File"):
      world.open_dialog()
    imgui.separator()
    imgui.text_disabled("Drag : pan   Scroll : zoom")
    imgui.text_disabled("O : open   Esc : quit")
    imgui.end()

  def _draw_atlas_window(self, world: "AppWorld", scene: SprScene) -> None:
    """Right-side hierarchy: one tree node per atlas, one selectable per
    cropped sprite. Clicking the atlas header selects the full atlas;
    clicking a sprite selects that sub-rectangle."""
    win_w = world.window.width
    imgui.set_next_window_pos((win_w - 320, 10), imgui.Cond_.first_use_ever.value)
    imgui.set_next_window_size((310, 600), imgui.Cond_.first_use_ever.value)
    imgui.begin("Sprites")

    if not scene.atlases:
      imgui.text_disabled("(empty)")
      imgui.end()
      return

    base_flag = (
      imgui.TreeNodeFlags_.open_on_arrow.value
      | imgui.TreeNodeFlags_.open_on_double_click.value
      | imgui.TreeNodeFlags_.span_avail_width.value
    )

    for atlas_idx, atlas in enumerate(scene.atlases):
      flag = base_flag
      is_active = atlas_idx == scene.selected_atlas
      if is_active and scene.selected_sprite == FULL_ATLAS_IDX:
        flag |= imgui.TreeNodeFlags_.selected.value
      label = _atlas_label(atlas.name)
      open_ = imgui.tree_node_ex(f"{label}##atlas{atlas_idx}", flag)
      if imgui.is_item_clicked() and not imgui.is_item_toggled_open():
        world.select_spr_entry(atlas_idx, FULL_ATLAS_IDX)
      if open_:
        sprite_indices = (
          scene.atlas_sprite_indices[atlas_idx]
          if atlas_idx < len(scene.atlas_sprite_indices)
          else []
        )
        for sprite_idx in sprite_indices:
          item_label = f"sprite_{sprite_idx}##a{atlas_idx}s{sprite_idx}"
          selected = is_active and scene.selected_sprite == sprite_idx
          if imgui.selectable(item_label, selected)[0]:
            world.select_spr_entry(atlas_idx, sprite_idx)
        imgui.tree_pop()

    imgui.end()

  def on_mouse_motion(self, dx: int, dy: int, mctx: "ModeContext") -> None:
    if any(mctx.buttons):
      cast(SprCamera, mctx.camera).pan(dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, mctx: "ModeContext") -> None:
    cast(SprCamera, mctx.camera).zoom_step(direction, mx, my, mctx.width, mctx.height)


def _atlas_label(ref_filename: str) -> str:
  """Strip the .tex/.te1 suffix from the .spr's reference for a cleaner
  tree label."""
  stem = Path(ref_filename).stem
  return stem or ref_filename


def _active_sprite_size(scene: SprScene) -> Tuple[int, int]:
  ref = scene.active_ref()
  if ref is None:
    return 0, 0
  return ref.width, ref.height


def _active_sprite_label(scene: SprScene) -> Optional[str]:
  if scene.active_atlas() is None:
    return None
  if scene.selected_sprite == FULL_ATLAS_IDX:
    return "(full atlas)"
  return f"sprite_{scene.selected_sprite}"
