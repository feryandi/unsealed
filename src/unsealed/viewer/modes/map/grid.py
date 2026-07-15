"""
Grid overlay renderer.

Draws a 512×512 line grid on top of the terrain, following the heightmap so
each cell traces the actual surface. Used for click-to-coord interactions
and as a visual reference for object placement / inspection.

Polygon offset for lines is used to avoid z-fighting with the terrain.
"""

from __future__ import annotations

import ctypes
from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray
from OpenGL.GL import (
  GL_ARRAY_BUFFER,
  GL_BLEND,
  GL_DEPTH_TEST,
  GL_DYNAMIC_DRAW,
  GL_ELEMENT_ARRAY_BUFFER,
  GL_FALSE,
  GL_FLOAT,
  GL_LINES,
  GL_ONE_MINUS_SRC_ALPHA,
  GL_POLYGON_OFFSET_LINE,
  GL_SRC_ALPHA,
  GL_STATIC_DRAW,
  GL_TRIANGLES,
  GL_TRUE,
  GL_UNSIGNED_INT,
  glBindBuffer,
  glBindVertexArray,
  glBlendFunc,
  glBufferData,
  glDeleteBuffers,
  glDeleteProgram,
  glDeleteVertexArrays,
  glDepthMask,
  glDisable,
  glDrawArrays,
  glDrawElements,
  glEnable,
  glEnableVertexAttribArray,
  glGenBuffers,
  glGenVertexArrays,
  glGetUniformLocation,
  glLineWidth,
  glPolygonOffset,
  glUniform4f,
  glUseProgram,
  glVertexAttribPointer,
)

from ...rendering.shaders import _compile_prog, _u_mat4
from .scene import MapScene


_GRID_VERT = """
#version 330 core

layout(location = 0) in vec3 aPos;

uniform mat4 uViewProj;

void main()
{
    gl_Position = uViewProj * vec4(aPos, 1.0);
}
"""


_GRID_FRAG = """
#version 330 core

uniform vec4 uColor;
out vec4 FragColor;

void main()
{
    FragColor = uColor;
}
"""


class GridRenderer:
  """Owns GL state for the heightmap-following 512×512 line grid + cell highlight."""

  # Y lift on top of polygon offset. The grid mesh sits at half-integer cell
  # boundaries, so its line segments cut diagonally across terrain triangles
  # (whose vertices live at integer positions) — polygon offset alone isn't
  # enough to keep them from dipping below the surface in steep terrain.
  _Y_LIFT = 0.5

  # Default appearance.
  _LINE_COLOR = (0.85, 0.85, 0.85, 0.35)
  _HIGHLIGHT_COLOR = (1.0, 0.78, 0.20, 0.55)

  def __init__(self) -> None:
    self._prog: int = 0
    self._line_vao: int = 0
    self._line_vbo: int = 0
    self._line_ebo: int = 0
    self._line_idx_count: int = 0

    # Highlight quad uses its own dynamic VBO (4 verts, regenerated per click).
    self._quad_vao: int = 0
    self._quad_vbo: int = 0
    self._quad_ready: bool = False

    self._heights: Optional[NDArray] = None
    self._map_w: int = 0
    self._map_h: int = 0

  # ── lifecycle ─────────────────────────────────────────────────────────────

  def init(self) -> None:
    self._prog = _compile_prog(_GRID_VERT, _GRID_FRAG)

  def upload(self, scene: MapScene) -> None:
    self.free_scene()

    heights = scene.terrain_heights
    if heights is None:
      return
    H, W = heights.shape
    self._heights = heights
    self._map_w = W
    self._map_h = H

    # ── line VBO: one vertex per heightmap sample at (x, h+lift, z) ─────────
    # Each heightmap sample at index (i, j) is the CENTER of its 1×1 cell,
    # so cell boundaries (= grid lines) sit at half-integer world positions.
    # Shifting the mesh by -0.5 in X/Z places the lines on those boundaries.
    xx, zz = np.meshgrid(
      np.arange(W, dtype=np.float32),
      np.arange(H, dtype=np.float32),
    )
    verts = np.empty((H * W, 3), dtype=np.float32)
    verts[:, 0] = xx.flatten() - 0.5
    verts[:, 1] = heights.flatten() + self._Y_LIFT
    verts[:, 2] = zz.flatten() - 0.5
    verts = np.ascontiguousarray(verts.flatten())

    # ── line IBO: horizontal segments (constant z) + vertical (constant x) ──
    # Horizontal: for each row z, pairs (z*W + x, z*W + x + 1) for x in [0, W-2].
    hx = np.arange(W - 1, dtype=np.uint32)
    hz = np.arange(H, dtype=np.uint32)
    hxg, hzg = np.meshgrid(hx, hz)
    h_a = (hzg * W + hxg).flatten()
    h_b = h_a + 1

    # Vertical: for each column x, pairs (z*W + x, (z+1)*W + x) for z in [0, H-2].
    vz = np.arange(H - 1, dtype=np.uint32)
    vx = np.arange(W, dtype=np.uint32)
    vxg, vzg = np.meshgrid(vx, vz)
    v_a = (vzg * W + vxg).flatten()
    v_b = v_a + W

    indices = np.empty((h_a.size + v_a.size) * 2, dtype=np.uint32)
    indices[0::2] = np.concatenate([h_a, v_a])
    indices[1::2] = np.concatenate([h_b, v_b])
    indices = np.ascontiguousarray(indices)

    self._line_vao = glGenVertexArrays(1)
    self._line_vbo = glGenBuffers(1)
    self._line_ebo = glGenBuffers(1)

    glBindVertexArray(self._line_vao)
    glBindBuffer(GL_ARRAY_BUFFER, self._line_vbo)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 12, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._line_ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
    glBindVertexArray(0)

    self._line_idx_count = int(indices.size)

    # ── highlight quad VAO (4 dynamic verts) ────────────────────────────────
    self._quad_vao = glGenVertexArrays(1)
    self._quad_vbo = glGenBuffers(1)
    glBindVertexArray(self._quad_vao)
    glBindBuffer(GL_ARRAY_BUFFER, self._quad_vbo)
    glBufferData(GL_ARRAY_BUFFER, 6 * 3 * 4, None, GL_DYNAMIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 12, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glBindVertexArray(0)
    self._quad_ready = False

  def free_scene(self) -> None:
    if self._line_ebo:
      glDeleteBuffers(1, [self._line_ebo])
      self._line_ebo = 0
    if self._line_vbo:
      glDeleteBuffers(1, [self._line_vbo])
      self._line_vbo = 0
    if self._line_vao:
      glDeleteVertexArrays(1, [self._line_vao])
      self._line_vao = 0
    if self._quad_vbo:
      glDeleteBuffers(1, [self._quad_vbo])
      self._quad_vbo = 0
    if self._quad_vao:
      glDeleteVertexArrays(1, [self._quad_vao])
      self._quad_vao = 0
    self._line_idx_count = 0
    self._heights = None
    self._quad_ready = False

  def cleanup(self) -> None:
    self.free_scene()
    if self._prog:
      glDeleteProgram(self._prog)
      self._prog = 0

  # ── per-frame ─────────────────────────────────────────────────────────────

  def render(
    self,
    view: NDArray,
    proj: NDArray,
    highlight_cell: Optional[Tuple[int, int]],
  ) -> None:
    if not self._line_idx_count or self._prog == 0:
      return
    view_proj = (proj @ view).astype(np.float32)

    glEnable(GL_DEPTH_TEST)
    glDepthMask(GL_TRUE)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_POLYGON_OFFSET_LINE)
    glPolygonOffset(-1.0, -1.0)
    glLineWidth(1.0)

    glUseProgram(self._prog)
    _u_mat4(self._prog, "uViewProj", view_proj)
    _set_color(self._prog, self._LINE_COLOR)

    glBindVertexArray(self._line_vao)
    glDrawElements(GL_LINES, self._line_idx_count, GL_UNSIGNED_INT, None)
    glBindVertexArray(0)

    glDisable(GL_POLYGON_OFFSET_LINE)

    if highlight_cell is not None:
      self._render_highlight(highlight_cell, view_proj)

    glUseProgram(0)

  # ── private ───────────────────────────────────────────────────────────────

  def _render_highlight(
    self,
    cell: Tuple[int, int],
    view_proj: NDArray,
  ) -> None:
    """Two triangles covering the 1×1 cell centered at (cx, cz)."""
    if self._heights is None:
      return
    cx, cz = cell
    if cx < 0 or cz < 0 or cx >= self._map_w or cz >= self._map_h:
      return

    # Cell (cx, cz) is centered on (cx, cz) and spans (cx-0.5..cx+0.5) in X,
    # (cz-0.5..cz+0.5) in Z. Flat-shade using the cell's own center height —
    # this is good enough visually and avoids edge sampling.
    h = float(self._heights[cz, cx]) + self._Y_LIFT
    x0, x1 = float(cx) - 0.5, float(cx) + 0.5
    z0, z1 = float(cz) - 0.5, float(cz) + 0.5

    verts = np.array(
      [
        x0,
        h,
        z0,
        x1,
        h,
        z0,
        x1,
        h,
        z1,
        x0,
        h,
        z0,
        x1,
        h,
        z1,
        x0,
        h,
        z1,
      ],
      dtype=np.float32,
    )

    _set_color(self._prog, self._HIGHLIGHT_COLOR)
    glDepthMask(GL_FALSE)
    glBindVertexArray(self._quad_vao)
    glBindBuffer(GL_ARRAY_BUFFER, self._quad_vbo)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_DYNAMIC_DRAW)
    glDrawArrays(GL_TRIANGLES, 0, 6)
    glBindVertexArray(0)
    glDepthMask(GL_TRUE)


def _set_color(prog: int, rgba: Tuple[float, float, float, float]) -> None:
  loc = glGetUniformLocation(prog, "uColor")
  if loc != -1:
    glUniform4f(loc, *rgba)
