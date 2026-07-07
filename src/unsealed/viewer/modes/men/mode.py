"""MenMode — viewer mode for .men game UI files."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, List, Optional, Tuple, cast

from imgui_bundle import imgui

from unsealed.reader.vfs import Resource
from ..base import BaseMode, RenderExtension
from .camera import MenCamera
from .extensions import MenExtension
from .pipeline import MenViewerPipeline
from .scene import STATE_NAMES, MenElement, MenScene

if TYPE_CHECKING:
  from ...app.world import AppWorld
  from ...camera import Camera
  from ...scenes import ViewerScene
  from ..context import ModeContext


class MenMode(BaseMode):
  name = "men"
  extensions = (".men",)
  scene_type = MenScene

  def __init__(self) -> None:
    self._render_extensions: List[RenderExtension] = [MenExtension()]

  def render_extensions(self) -> "Iterable[RenderExtension]":
    return self._render_extensions

  def decode(
    self, res: Resource, shader_cache: Optional[dict] = None
  ) -> "ViewerScene":
    return MenViewerPipeline().run(res)

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = MenCamera()
    if isinstance(scene, MenScene) and scene.canvas_w > 0 and scene.canvas_h > 0:
      cam.fit_image(scene.canvas_w, scene.canvas_h, win_w, win_h)
    return cam

  def draw_hud(self, world: "AppWorld") -> None:
    from ...app.panels import draw_unknowns_window

    ctx = world.scene.context
    if ctx is None:
      return
    scene = cast(MenScene, ctx.scene)
    cam = cast(MenCamera, ctx.camera)

    self._draw_control_window(world, scene, cam, ctx.path.name)
    self._draw_element_tree(world, scene)
    active = scene.active_element()
    if active is not None and scene.selected_element_idx is not None:
      self._draw_element_detail(world, active, scene.selected_element_idx)
    draw_unknowns_window(scene)

  def _draw_control_window(
    self, world: "AppWorld", scene: MenScene, cam: MenCamera, filename: str
  ) -> None:
    imgui.set_next_window_pos((10, 10), imgui.Cond_.first_use_ever.value)
    imgui.begin("Menu (.men)")
    imgui.text(f"File     : {filename}")
    imgui.text(f"Version  : {scene.version}")
    imgui.text(f"Sprites  : {scene.spr_file_name or '<missing>'}")
    imgui.text(f"Elements : {len(scene.elements)}")
    imgui.text(f"Canvas   : {scene.canvas_w} x {scene.canvas_h} px")
    imgui.text(f"Zoom     : {int(cam.zoom * 100)}%")
    imgui.separator()
    if imgui.button("Open File"):
      world.open_dialog()
    imgui.separator()
    imgui.text_disabled("Click sprite : inspect")
    imgui.text_disabled("Drag : pan   Scroll : zoom")
    imgui.text_disabled("O : open   Esc : quit")
    imgui.end()

  def _draw_element_tree(self, world: "AppWorld", scene: MenScene) -> None:
    """Left-side tree of all elements in DFS order, with hide toggles per node."""
    win_h = world.window.height
    imgui.set_next_window_pos((10, 240), imgui.Cond_.first_use_ever.value)
    imgui.set_next_window_size((300, max(200, win_h - 260)), imgui.Cond_.first_use_ever.value)
    imgui.begin("Elements")
    if not scene.elements:
      imgui.text_disabled("(no elements)")
      imgui.end()
      return

    for root in scene.root_indices:
      self._draw_element_node(world, scene, root)
    imgui.end()

  def _draw_element_node(
    self, world: "AppWorld", scene: MenScene, idx: int
  ) -> None:
    el = scene.elements[idx]
    label = el.label or f"<el {idx}>"
    selected = (idx == scene.selected_element_idx)

    flag = (
      imgui.TreeNodeFlags_.open_on_arrow.value
      | imgui.TreeNodeFlags_.open_on_double_click.value
      | imgui.TreeNodeFlags_.span_avail_width.value
      | imgui.TreeNodeFlags_.default_open.value
    )
    if selected:
      flag |= imgui.TreeNodeFlags_.selected.value
    if not el.children:
      flag |= imgui.TreeNodeFlags_.leaf.value

    # Tree node spans the row (span_avail_width) so the inline hide button
    # sits on top of it. Allow the button to win click priority over the
    # tree node, and defer the selection so a button click doesn't also
    # select the row.
    imgui.set_next_item_allow_overlap()
    open_ = imgui.tree_node_ex(f"{label}##el{idx}", flag)
    tree_clicked = imgui.is_item_clicked() and not imgui.is_item_toggled_open()

    imgui.same_line()
    imgui.push_id(f"hide{idx}")
    hide_clicked = imgui.small_button("show" if el.hidden else "hide")
    imgui.pop_id()

    if hide_clicked:
      world.toggle_men_hide(idx)
    elif tree_clicked:
      world.select_men_element(idx)

    if open_:
      for child in el.children:
        self._draw_element_node(world, scene, child)
      imgui.tree_pop()

  def _draw_element_detail(
    self, world: "AppWorld", element: MenElement, idx: int
  ) -> None:
    raw = element.raw
    win_w = world.window.width
    imgui.set_next_window_pos((win_w - 360, 10), imgui.Cond_.first_use_ever.value)
    imgui.set_next_window_size((350, 600), imgui.Cond_.first_use_ever.value)
    opened, keep_open = imgui.begin(f"Element {idx}", True)
    if not keep_open:
      world.close_men_detail()
    if not opened:
      imgui.end()
      return

    imgui.text(f"label    : {element.label}")
    imgui.text(f"type     : {element.type}")
    imgui.text(f"spr_file : {element.spr_file or '<inherits>'}")
    imgui.text(f"spr_idx  : {element.spr_idx}")
    imgui.text(f"rect     : {list(element.rectangle)}")
    if "sublabel" in raw:
      imgui.text(f"sublabel : {raw.get('sublabel')}")
    if "alpha" in raw:
      imgui.text(f"alpha    : {raw.get('alpha')}")

    # Group / tree info.
    if imgui.collapsing_header("Group", imgui.TreeNodeFlags_.default_open.value):
      imgui.text(
        f"  parent       : "
        f"{element.parent if element.parent is not None else '<root>'}"
      )
      imgui.text(f"  subtree_size : {element.subtree_size}")
      if element.children:
        imgui.text(f"  children     : {element.children}")
      imgui.text(f"  hidden       : {'yes' if element.hidden else 'no'}")
      if imgui.button("Show group" if element.hidden else "Hide group"):
        world.toggle_men_hide(idx)

    # State sprites.
    present_states = [s for s in STATE_NAMES if s in element.state_indices]
    if present_states and imgui.collapsing_header(
      "State sprites", imgui.TreeNodeFlags_.default_open.value
    ):
      for state in present_states:
        sprite_idx = element.state_indices[state]
        is_active = (state == element.active_state)
        if imgui.selectable(
          f"{state:<8}: {sprite_idx}##st{state}", is_active
        )[0]:
          world.set_men_state(idx, state)

    # Captured-but-unnamed fields (the various unknown ints).
    unknown_keys = [
      k for k in raw if k == "unknowns" or "unknown" in k or k == "v3_block"
    ]
    if unknown_keys and imgui.collapsing_header("Unknowns"):
      for k in unknown_keys:
        val = raw.get(k)
        if isinstance(val, list):
          for i, v in enumerate(val):
            imgui.text(f"  {k}[{i}] : {v}")
        else:
          imgui.text(f"  {k} : {val}")

    imgui.end()

  # ── input handlers ──────────────────────────────────────────────────────

  def on_mouse_down(self, button: int, pos: tuple[int, int], mctx: "ModeContext") -> None:
    # Record where LMB went down so we can distinguish a click from a drag
    # in on_mouse_up (any drag distance cancels the pick).
    if button == 1:
      mctx.set_lmb_down(pos)

  def on_mouse_up(self, button: int, pos: tuple[int, int], mctx: "ModeContext") -> None:
    if button != 1:
      return
    down = mctx.lmb_down_pos
    mctx.set_lmb_down(None)
    if down is None:
      return
    if abs(pos[0] - down[0]) > 3 or abs(pos[1] - down[1]) > 3:
      return  # drag, not click
    self._pick_element(pos, mctx)

  def on_mouse_motion(self, dx: int, dy: int, mctx: "ModeContext") -> None:
    if any(mctx.buttons):
      cast(MenCamera, mctx.camera).pan(dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, mctx: "ModeContext") -> None:
    cast(MenCamera, mctx.camera).zoom_step(
      direction, mx, my, mctx.width, mctx.height
    )

  # ── private ─────────────────────────────────────────────────────────────

  def _pick_element(self, pos: tuple[int, int], mctx: "ModeContext") -> None:
    """Convert screen pos → canvas pixel coords, find topmost element under it.

    Iterates in reverse so later-drawn (= topmost) elements win.
    """
    ctx = mctx.scene_context
    if ctx is None:
      return
    scene = cast(MenScene, ctx.scene)
    cam = cast(MenCamera, ctx.camera)
    canvas = _screen_to_canvas(pos, cam, mctx.width, mctx.height,
                               scene.canvas_w, scene.canvas_h)
    if canvas is None:
      scene.selected_element_idx = None
      return

    cx, cy = canvas
    for i in range(len(scene.elements) - 1, -1, -1):
      if i in scene.hidden_set:
        continue
      el = scene.elements[i]
      if _rect_contains(el.rectangle, cx, cy):
        scene.selected_element_idx = i
        return
    scene.selected_element_idx = None


def _screen_to_canvas(
  pos: tuple[int, int], cam: MenCamera, win_w: int, win_h: int,
  canvas_w: int, canvas_h: int,
) -> Optional[Tuple[float, float]]:
  """Map screen pixel pos to canvas pixel coords (origin top-left, y-down)."""
  if cam.zoom <= 0 or canvas_w <= 0 or canvas_h <= 0:
    return None
  mx, my = pos
  # World (origin center, y-up): same ortho ImageCamera uses.
  wx = cam.pan_x + (mx - win_w * 0.5) / cam.zoom
  wy = cam.pan_y + (win_h * 0.5 - my) / cam.zoom
  # World → canvas pixel coords (origin top-left, y-down).
  cx = wx + canvas_w * 0.5
  cy = canvas_h * 0.5 - wy
  return cx, cy


def _rect_contains(rect: Tuple[int, int, int, int], x: float, y: float) -> bool:
  x1, y1, x2, y2 = rect
  lo_x, hi_x = (x1, x2) if x1 <= x2 else (x2, x1)
  lo_y, hi_y = (y1, y2) if y1 <= y2 else (y2, y1)
  return lo_x <= x <= hi_x and lo_y <= y <= hi_y
