"""MenExtension — draws all .men UI elements as textured quads.

Architecture: one GL texture per *atlas* (shared across many sprites),
not one per (element, state). Each MenElement carries a `SpriteRef`
(atlas_idx + pixel sub-rect) per state; the renderer computes UVs from
the active state's ref and uploads a packed vertex buffer that contains
one quad per element with UVs already baked in. State changes mutate
`el.active_state`; the extension detects the diff on the next frame and
rewrites the small chunk of the VBO that changed.

This collapses what used to be N×5 separate GL texture uploads (~1980 for
the cash UI) into N_atlases uploads (~14), and reduces per-frame texture
binds to N_atlases instead of N_visible_elements.
"""

from __future__ import annotations

import ctypes
import os
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np
from OpenGL.GL import (
  GL_ARRAY_BUFFER,
  GL_BLEND,
  GL_DEPTH_TEST,
  GL_DYNAMIC_DRAW,
  GL_FALSE,
  GL_FLOAT,
  GL_LINES,
  GL_ONE_MINUS_SRC_ALPHA,
  GL_SRC_ALPHA,
  GL_TEXTURE0,
  GL_TEXTURE_2D,
  GL_TRIANGLES,
  glActiveTexture,
  glBindBuffer,
  glBindTexture,
  glBindVertexArray,
  glBlendFunc,
  glBufferData,
  glBufferSubData,
  glDeleteBuffers,
  glDeleteProgram,
  glDeleteTextures,
  glDeleteVertexArrays,
  glDisable,
  glDrawArrays,
  glEnable,
  glEnableVertexAttribArray,
  glGenBuffers,
  glGenVertexArrays,
  glGetUniformLocation,
  glLineWidth,
  glUniform1i,
  glUniform4f,
  glUseProgram,
  glVertexAttribPointer,
)

from ...rendering.shaders import _IMG_VERT, _compile_prog, _u_mat4, _upload_rgba
from ..base import RenderPhase
from .camera import MenCamera
from .scene import MenElement, MenScene

if TYPE_CHECKING:
  from numpy.typing import NDArray

  from ...rendering import RenderContext
  from ...scenes import ViewerScene


_PROFILE = bool(os.environ.get("UNSEALED_PROFILE"))


_MEN_FRAG = """
#version 330 core
in vec2 vUV;
uniform sampler2D uTexture;
out vec4 fragColor;
void main() {
    fragColor = texture(uTexture, vUV);
}
"""

_OUTLINE_VERT = """
#version 330 core
layout(location = 0) in vec3 aPos;
uniform mat4 uMVP;
void main() { gl_Position = uMVP * vec4(aPos, 1.0); }
"""

_OUTLINE_FRAG = """
#version 330 core
out vec4 FragColor;
uniform vec4 uColor;
void main() { FragColor = uColor; }
"""


# Per-element vertex layout: 6 verts × 5 floats (x, y, z, u, v) = 30 floats.
_FLOATS_PER_QUAD = 30
_BYTES_PER_QUAD = _FLOATS_PER_QUAD * 4


class MenExtension:
  """Renders all UI elements using shared atlas textures + selection outline."""

  phase = RenderPhase.BACKGROUND

  def __init__(self) -> None:
    self._img_prog: int = 0
    self._img_vao: int = 0
    self._img_vbo: int = 0
    self._u_mvp_loc: int = -1
    self._u_tex_loc: int = -1

    self._line_prog: int = 0
    self._line_vao: int = 0
    self._line_vbo: int = 0

    # One GL texture per source atlas (indexed by SpriteAtlas position
    # in MenScene.atlases). Sentinel 0 for missing/failed uploads.
    self._atlas_tex_ids: List[int] = []

    # CPU-side packed verts. We keep this so per-element state changes can
    # rewrite just one element's 30-float slot via glBufferSubData rather
    # than re-upload the whole buffer.
    self._verts: Optional[np.ndarray] = None
    # Snapshot of every element's `active_state` at last vertex build. We
    # diff against this each frame to detect state changes.
    self._state_snapshot: List[str] = []

    # Groups elements by which atlas they sample so render can bind each
    # atlas once and issue all of its element draws back-to-back.
    self._atlas_groups: Dict[int, List[int]] = {}

    self._scene: Optional[MenScene] = None

  def init(self) -> None:
    self._img_prog = _compile_prog(_IMG_VERT, _MEN_FRAG)
    self._img_vao = glGenVertexArrays(1)
    self._img_vbo = glGenBuffers(1)
    self._u_mvp_loc = glGetUniformLocation(self._img_prog, "uMVP")
    self._u_tex_loc = glGetUniformLocation(self._img_prog, "uTexture")

    self._line_prog = _compile_prog(_OUTLINE_VERT, _OUTLINE_FRAG)
    self._line_vao = glGenVertexArrays(1)
    self._line_vbo = glGenBuffers(1)

  # ── scene lifecycle ────────────────────────────────────────────────────

  def upload(self, scene: "ViewerScene") -> None:
    self.free_scene()
    if not isinstance(scene, MenScene):
      return
    self._scene = scene

    t0 = time.perf_counter()
    # 1. Upload one GL texture per atlas. Two flags matter for UI sprites:
    #      flip_y=False  — our UV layout already uses v=0=top.
    #      mipmaps=False — sprites render near 1:1, mip pyramid is waste.
    # We drop atlas.rgba once it's on the GPU — width/height stay around
    # for UV math, the CPU pixels don't.
    for atlas in scene.atlases:
      if atlas.rgba is None or atlas.rgba.size == 0:
        self._atlas_tex_ids.append(0)
        continue
      data = atlas.rgba.tobytes() if atlas.rgba.flags["C_CONTIGUOUS"] \
        else np.ascontiguousarray(atlas.rgba).tobytes()
      try:
        tex_id = _upload_rgba(
          data, atlas.width, atlas.height, mipmaps=False, flip_y=False
        )
      except Exception as e:
        print(f"[men] atlas upload failed for {atlas.name!r}: {e}")
        tex_id = 0
      self._atlas_tex_ids.append(tex_id)
      atlas.rgba = None

    # 2. Build the packed vertex buffer once. Future state changes use
    #    glBufferSubData to update just the changed element's slot.
    self._rebuild_verts_and_groups(scene)
    self._upload_full_vbo()

    if _PROFILE:
      uploaded = sum(1 for tid in self._atlas_tex_ids if tid)
      print(
        f"[men profile] MenExtension.upload: "
        f"{(time.perf_counter() - t0) * 1000:6.1f}ms  "
        f"({uploaded}/{len(scene.atlases)} atlas textures, "
        f"{len(scene.elements)} element quads)"
      )

  def free_scene(self) -> None:
    if self._atlas_tex_ids:
      for tex in self._atlas_tex_ids:
        if tex:
          glDeleteTextures(1, [tex])
    self._atlas_tex_ids = []
    self._verts = None
    self._state_snapshot = []
    self._atlas_groups = {}
    self._scene = None

  def dispose(self) -> None:
    self.free_scene()
    for prog in (self._img_prog, self._line_prog):
      if prog:
        glDeleteProgram(prog)
    self._img_prog = 0
    self._line_prog = 0
    for vao in (self._img_vao, self._line_vao):
      if vao:
        glDeleteVertexArrays(1, [vao])
    self._img_vao = 0
    self._line_vao = 0
    for vbo in (self._img_vbo, self._line_vbo):
      if vbo:
        glDeleteBuffers(1, [vbo])
    self._img_vbo = 0
    self._line_vbo = 0

  # ── per-frame render ───────────────────────────────────────────────────

  def render(self, ctx: "RenderContext", view: "NDArray", proj: "NDArray") -> None:
    if self._scene is None or not isinstance(ctx.camera, MenCamera):
      return
    if self._verts is None or not self._atlas_tex_ids:
      return

    self._sync_state_changes()

    aspect = ctx.width / max(ctx.height, 1)
    mvp = ctx.camera.projection_matrix(aspect, ctx.width, ctx.height)

    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glUseProgram(self._img_prog)
    _u_mat4(self._img_prog, "uMVP", mvp)
    glActiveTexture(GL_TEXTURE0)
    glUniform1i(self._u_tex_loc, 0)
    glBindVertexArray(self._img_vao)

    hidden = self._scene.hidden_set
    tex_ids = self._atlas_tex_ids
    for atlas_idx, indices in self._atlas_groups.items():
      if atlas_idx < 0 or atlas_idx >= len(tex_ids):
        continue
      tex_id = tex_ids[atlas_idx]
      if not tex_id:
        continue
      glBindTexture(GL_TEXTURE_2D, tex_id)
      for i in indices:
        if i in hidden:
          continue
        glDrawArrays(GL_TRIANGLES, i * 6, 6)

    glBindVertexArray(0)
    glBindTexture(GL_TEXTURE_2D, 0)
    glUseProgram(0)

    sel_idx = self._scene.selected_element_idx
    if sel_idx is not None and 0 <= sel_idx < len(self._scene.elements):
      self._draw_outline(self._scene.elements[sel_idx], mvp)

    glEnable(GL_DEPTH_TEST)

  # ── private ────────────────────────────────────────────────────────────

  def _sync_state_changes(self) -> None:
    """Detect elements whose `active_state` has changed since the last
    vertex build. For each, rewrite that element's 30-float slot in the
    CPU verts array and push the slot via glBufferSubData.

    If `_atlas_groups` becomes stale (state change moved an element to a
    different atlas) we rebuild the groups too — but only when it actually
    happens, not every frame.
    """
    if self._scene is None or self._verts is None:
      return
    elements = self._scene.elements
    if len(elements) != len(self._state_snapshot):
      # Element count changed underneath us — full rebuild.
      self._rebuild_verts_and_groups(self._scene)
      self._upload_full_vbo()
      return

    changed: List[int] = []
    groups_dirty = False
    for i, el in enumerate(elements):
      if el.active_state == self._state_snapshot[i]:
        continue
      old_ref = self._scene.elements[i].state_refs.get(self._state_snapshot[i])
      new_ref = el.state_refs.get(el.active_state)
      old_atlas = old_ref.atlas_idx if old_ref is not None else -1
      new_atlas = new_ref.atlas_idx if new_ref is not None else -1
      if old_atlas != new_atlas:
        groups_dirty = True
      self._write_element_verts(i, el)
      self._state_snapshot[i] = el.active_state
      changed.append(i)

    if not changed:
      return

    if groups_dirty:
      self._rebuild_atlas_groups(elements)

    # Push just the changed regions. For batches of contiguous indices this
    # could be coalesced, but typical user interaction changes one element
    # at a time so per-element pushes are fine.
    glBindBuffer(GL_ARRAY_BUFFER, self._img_vbo)
    for i in changed:
      offset = i * _BYTES_PER_QUAD
      slice_ = self._verts[i * _FLOATS_PER_QUAD:(i + 1) * _FLOATS_PER_QUAD]
      glBufferSubData(GL_ARRAY_BUFFER, offset, _BYTES_PER_QUAD, slice_)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

  def _rebuild_verts_and_groups(self, scene: MenScene) -> None:
    """Build the full packed vertex buffer + atlas groups from scratch."""
    n = len(scene.elements)
    self._verts = np.zeros(n * _FLOATS_PER_QUAD, dtype=np.float32)
    self._state_snapshot = [el.active_state for el in scene.elements]
    for i, el in enumerate(scene.elements):
      self._write_element_verts(i, el)
    self._rebuild_atlas_groups(scene.elements)

  def _rebuild_atlas_groups(self, elements: List[MenElement]) -> None:
    self._atlas_groups = {}
    for i, el in enumerate(elements):
      ref = el.state_refs.get(el.active_state)
      if ref is None:
        continue
      self._atlas_groups.setdefault(ref.atlas_idx, []).append(i)

  def _write_element_verts(self, i: int, el: MenElement) -> None:
    """Compute the 6 vertices for element `i` and write them into _verts.

    UVs are derived from the element's currently-active SpriteRef: pixel
    coords in the source atlas, normalized by the atlas's dimensions.
    Elements without an active ref (or whose ref points at a missing
    atlas) get zeroed verts — they're effectively invisible without
    paying a per-frame branch in the draw loop.
    """
    assert self._verts is not None
    base = i * _FLOATS_PER_QUAD
    if self._scene is None:
      return
    x0, y0, x1, y1 = _rect_to_world(
      el.rectangle, self._scene.canvas_w, self._scene.canvas_h
    )
    ref = el.state_refs.get(el.active_state)
    if ref is None or ref.atlas_idx < 0 \
        or ref.atlas_idx >= len(self._scene.atlases):
      self._verts[base:base + _FLOATS_PER_QUAD] = 0.0
      return
    atlas = self._scene.atlases[ref.atlas_idx]
    aw = max(1, atlas.width)
    ah = max(1, atlas.height)
    u0 = ref.left   / aw
    u1 = ref.right  / aw
    v0 = ref.top    / ah  # top of sprite = lower v (image row 0)
    v1 = ref.bottom / ah  # bottom of sprite = higher v
    # bottom-left, bottom-right, top-right, bottom-left, top-right, top-left
    self._verts[base + 0:base + 5]   = (x0, y0, 0.0, u0, v1)
    self._verts[base + 5:base + 10]  = (x1, y0, 0.0, u1, v1)
    self._verts[base + 10:base + 15] = (x1, y1, 0.0, u1, v0)
    self._verts[base + 15:base + 20] = (x0, y0, 0.0, u0, v1)
    self._verts[base + 20:base + 25] = (x1, y1, 0.0, u1, v0)
    self._verts[base + 25:base + 30] = (x0, y1, 0.0, u0, v0)

  def _upload_full_vbo(self) -> None:
    """Push the entire packed VBO + bake the attribute layout into the VAO."""
    if self._verts is None:
      return
    glBindVertexArray(self._img_vao)
    glBindBuffer(GL_ARRAY_BUFFER, self._img_vbo)
    glBufferData(GL_ARRAY_BUFFER, self._verts.nbytes, self._verts, GL_DYNAMIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(12))
    glEnableVertexAttribArray(1)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)

  def _draw_outline(self, el: MenElement, mvp: "NDArray") -> None:
    if self._scene is None:
      return
    x0, y0, x1, y1 = _rect_to_world(
      el.rectangle, self._scene.canvas_w, self._scene.canvas_h
    )
    verts = np.array(
      [
        x0, y0, 0.0,  x1, y0, 0.0,
        x1, y0, 0.0,  x1, y1, 0.0,
        x1, y1, 0.0,  x0, y1, 0.0,
        x0, y1, 0.0,  x0, y0, 0.0,
      ],
      dtype=np.float32,
    )

    glBindVertexArray(self._line_vao)
    glBindBuffer(GL_ARRAY_BUFFER, self._line_vbo)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_DYNAMIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 12, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

    glLineWidth(2.0)
    glUseProgram(self._line_prog)
    _u_mat4(self._line_prog, "uMVP", mvp)
    loc = glGetUniformLocation(self._line_prog, "uColor")
    glUniform4f(loc, 0.20, 1.00, 0.35, 1.0)
    glDrawArrays(GL_LINES, 0, 8)
    glBindVertexArray(0)
    glUseProgram(0)


def _rect_to_world(
  rect: Tuple[int, int, int, int], canvas_w: int, canvas_h: int
) -> Tuple[float, float, float, float]:
  """Convert (x1, y1, x2, y2) pixel rect (origin top-left, y-down) to
  world coords (origin center, y-up). Returns (x0, y0_bottom, x1, y1_top).
  """
  x1, y1, x2, y2 = rect
  hw = canvas_w * 0.5
  hh = canvas_h * 0.5
  wx0 = float(x1) - hw
  wx1 = float(x2) - hw
  wy_top = hh - float(y1)
  wy_bot = hh - float(y2)
  return wx0, wy_bot, wx1, wy_top
