"""SprExtension — renders the active sprite from a shared atlas texture.

Uploads one GL texture per source atlas at scene load (then drops the
CPU-side RGBA buffer). At draw time the active SpriteRef supplies both
the quad's pixel dimensions and the normalized UV sub-rectangle into
its atlas, so sprite "selection" never touches the GPU beyond a binding.
"""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
from OpenGL.GL import (
  GL_ARRAY_BUFFER,
  GL_DEPTH_TEST,
  GL_DYNAMIC_DRAW,
  GL_FALSE,
  GL_FLOAT,
  GL_TEXTURE0,
  GL_TEXTURE_2D,
  GL_TRIANGLES,
  glActiveTexture,
  glBindBuffer,
  glBindTexture,
  glBindVertexArray,
  glBufferData,
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
  glUniform1i,
  glUseProgram,
  glVertexAttribPointer,
)

from ...rendering.shaders import (
  _IMG_FRAG,
  _IMG_VERT,
  _compile_prog,
  _u_mat4,
  _upload_rgba,
)
from ..base import RenderPhase
from .camera import SprCamera
from .scene import SprScene

if TYPE_CHECKING:
  from numpy.typing import NDArray

  from ...rendering import RenderContext
  from ...scenes import ViewerScene


class SprExtension:
  """Owned by SprMode. One GL texture per atlas; render picks UVs."""

  phase = RenderPhase.BACKGROUND

  def __init__(self) -> None:
    self._prog: int = 0
    self._vao: int = 0
    self._vbo: int = 0

    # One GL texture per SprScene.atlases entry. Sentinel 0 for failed
    # uploads (still slotted so atlas_idx stays in sync with the scene).
    self._atlas_tex_ids: List[int] = []

    # (selected_atlas, selected_sprite) currently baked into the VBO —
    # used to detect when verts need to be rewritten.
    self._cached_key: Tuple[int, int] = (-2, -2)
    self._has_quad: bool = False

    self._scene: Optional[SprScene] = None

  def init(self) -> None:
    self._prog = _compile_prog(_IMG_VERT, _IMG_FRAG)
    self._vao = glGenVertexArrays(1)
    self._vbo = glGenBuffers(1)

  # ── scene lifecycle ────────────────────────────────────────────────────

  def upload(self, scene: "ViewerScene") -> None:
    self.free_scene()
    if not isinstance(scene, SprScene):
      return
    self._scene = scene

    # One GL texture per atlas. After upload we drop the CPU buffer so
    # only width/height linger on SpriteAtlas (we still need those for
    # UV math at draw time).
    for atlas in scene.atlases:
      if atlas.rgba is None or atlas.rgba.size == 0:
        self._atlas_tex_ids.append(0)
        continue
      data = (
        atlas.rgba.tobytes()
        if atlas.rgba.flags["C_CONTIGUOUS"]
        else np.ascontiguousarray(atlas.rgba).tobytes()
      )
      try:
        tex_id = _upload_rgba(
          data, atlas.width, atlas.height, mipmaps=False, flip_y=False
        )
      except Exception as e:
        print(f"[spr] atlas upload failed for {atlas.name!r}: {e}")
        tex_id = 0
      self._atlas_tex_ids.append(tex_id)
      atlas.rgba = None

  def free_scene(self) -> None:
    if self._atlas_tex_ids:
      for tex in self._atlas_tex_ids:
        if tex:
          glDeleteTextures(1, [tex])
    self._atlas_tex_ids = []
    self._cached_key = (-2, -2)
    self._has_quad = False
    self._scene = None

  def dispose(self) -> None:
    self.free_scene()
    if self._prog:
      glDeleteProgram(self._prog)
      self._prog = 0
    if self._vao:
      glDeleteVertexArrays(1, [self._vao])
      self._vao = 0
    if self._vbo:
      glDeleteBuffers(1, [self._vbo])
      self._vbo = 0

  # ── per-frame render ───────────────────────────────────────────────────

  def render(self, ctx: "RenderContext", view: "NDArray", proj: "NDArray") -> None:
    if self._scene is None or not isinstance(ctx.camera, SprCamera):
      return
    if not self._atlas_tex_ids:
      return

    key = (self._scene.selected_atlas, self._scene.selected_sprite)
    if key != self._cached_key:
      self._rebuild_quad()
      self._cached_key = key

    if not self._has_quad:
      return

    atlas_idx = self._scene.selected_atlas
    if not (0 <= atlas_idx < len(self._atlas_tex_ids)):
      return
    tex_id = self._atlas_tex_ids[atlas_idx]
    if not tex_id:
      return

    aspect = ctx.width / max(ctx.height, 1)
    mvp = ctx.camera.projection_matrix(aspect, ctx.width, ctx.height)

    glDisable(GL_DEPTH_TEST)
    glUseProgram(self._prog)
    _u_mat4(self._prog, "uMVP", mvp)
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glUniform1i(glGetUniformLocation(self._prog, "uTexture"), 0)
    glBindVertexArray(self._vao)
    glDrawArrays(GL_TRIANGLES, 0, 6)
    glBindVertexArray(0)
    glBindTexture(GL_TEXTURE_2D, 0)
    glUseProgram(0)
    glEnable(GL_DEPTH_TEST)

  # ── private ────────────────────────────────────────────────────────────

  def _rebuild_quad(self) -> None:
    """Pack the active sprite's quad (verts + UVs) into the VBO. Six
    verts × (x, y, z, u, v) = 30 floats — same layout as _IMG_VERT
    consumes."""
    self._has_quad = False
    if self._scene is None:
      return
    ref = self._scene.active_ref()
    atlas = self._scene.active_atlas()
    if ref is None or atlas is None:
      return
    if ref.width <= 0 or ref.height <= 0:
      return

    aw = max(1, atlas.width)
    ah = max(1, atlas.height)
    u0 = ref.left / aw
    u1 = ref.right / aw
    # Texture uploaded with flip_y=False, so image row 0 = v=0 (top).
    v0 = ref.top / ah
    v1 = ref.bottom / ah
    hw = ref.width * 0.5
    hh = ref.height * 0.5

    verts = np.array(
      [
        -hw,
        -hh,
        0.0,
        u0,
        v1,
        hw,
        -hh,
        0.0,
        u1,
        v1,
        hw,
        hh,
        0.0,
        u1,
        v0,
        -hw,
        -hh,
        0.0,
        u0,
        v1,
        hw,
        hh,
        0.0,
        u1,
        v0,
        -hw,
        hh,
        0.0,
        u0,
        v0,
      ],
      dtype=np.float32,
    )

    glBindVertexArray(self._vao)
    glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_DYNAMIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(12))
    glEnableVertexAttribArray(1)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    self._has_quad = True
