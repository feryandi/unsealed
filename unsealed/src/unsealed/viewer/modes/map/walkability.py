"""
Walkability overlay renderer.

Draws a translucent red wash on the cells where the .map's walkability
grid marks the tile as blocked. The geometry follows the terrain surface
(same heightmap-sampled vertex grid as the terrain mesh) so the colored
patches sit right on top of where the player can't walk.

The blocked / walkable decision is driven by a 512×512 R8 mask texture
(0 = walkable, 255 = blocked). The fragment shader discards walkable
pixels so only the blocked region paints.
"""

from __future__ import annotations

import ctypes
from typing import Optional

import numpy as np
from numpy.typing import NDArray
from OpenGL.GL import (
  GL_ARRAY_BUFFER,
  GL_BLEND,
  GL_CLAMP_TO_EDGE,
  GL_DEPTH_TEST,
  GL_ELEMENT_ARRAY_BUFFER,
  GL_FALSE,
  GL_FLOAT,
  GL_LINEAR,
  GL_NEAREST,
  GL_ONE_MINUS_SRC_ALPHA,
  GL_R8,
  GL_RED,
  GL_SRC_ALPHA,
  GL_STATIC_DRAW,
  GL_TEXTURE0,
  GL_TEXTURE_2D,
  GL_TEXTURE_MAG_FILTER,
  GL_TEXTURE_MIN_FILTER,
  GL_TEXTURE_WRAP_S,
  GL_TEXTURE_WRAP_T,
  GL_TRIANGLES,
  GL_TRUE,
  GL_UNSIGNED_BYTE,
  GL_UNSIGNED_INT,
  glActiveTexture,
  glBindBuffer,
  glBindTexture,
  glBindVertexArray,
  glBlendFunc,
  glBufferData,
  glDeleteBuffers,
  glDeleteProgram,
  glDeleteTextures,
  glDeleteVertexArrays,
  glDepthMask,
  glDisable,
  glDrawElements,
  glEnable,
  glEnableVertexAttribArray,
  glGenBuffers,
  glGenTextures,
  glGenVertexArrays,
  glGetUniformLocation,
  glPixelStorei,
  glTexImage2D,
  glTexParameteri,
  glUniform1f,
  glUniform1i,
  glUseProgram,
  glVertexAttribPointer,
)

GL_UNPACK_ALIGNMENT = 0x0CF5  # not always re-exported by PyOpenGL.GL package

from ...rendering.shaders import _compile_prog, _u_mat4
from .scene import MapScene


_WALK_VERT = """
#version 330 core

layout(location = 0) in vec3 aPos;

uniform mat4 uViewProj;
uniform float uMapW;
uniform float uMapH;

out vec2 vUv;

void main()
{
    // The mesh was built with a -0.5 shift so cell boundaries land on
    // half-integer world coords. Add 0.5 back here so a sample at world
    // (i, j) -- the center of cell (i, j) -- maps to UV that NEAREST-samples
    // mask pixel (i, j) for the whole cell.
    vUv = vec2((aPos.x + 0.5) / uMapW, (aPos.z + 0.5) / uMapH);
    gl_Position = uViewProj * vec4(aPos, 1.0);
}
"""


_WALK_FRAG = """
#version 330 core

in vec2 vUv;
out vec4 FragColor;

uniform sampler2D uWalkTex;
uniform vec4 uBlockedColor;

void main()
{
    float w = texture(uWalkTex, vUv).r;
    if (w < 0.5) discard;
    FragColor = uBlockedColor;
}
"""


class WalkabilityRenderer:
  """Owns GL state for the walkability overlay mesh + mask texture."""

  # Same reasoning as the grid: triangles span half-integer cell boundaries
  # while terrain vertices are at integers, so a small lift isn't enough on
  # steep slopes. Match the grid's lift; walkability doesn't write depth, so
  # the grid's lines still layer cleanly on top.
  _Y_LIFT = 0.5
  _BLOCKED_COLOR = (0.90, 0.20, 0.18, 0.45)

  def __init__(self) -> None:
    self._prog: int = 0
    self._vao: int = 0
    self._vbo: int = 0
    self._ebo: int = 0
    self._idx_count: int = 0
    self._tex: int = 0
    self._map_w: int = 0
    self._map_h: int = 0

  def init(self) -> None:
    self._prog = _compile_prog(_WALK_VERT, _WALK_FRAG)

  def upload(self, scene: MapScene) -> None:
    self.free_scene()

    mask = scene.walkable_data
    heights = scene.terrain_heights
    if mask is None or heights is None:
      return
    H, W = heights.shape
    if mask.shape != (H, W):
      # Walkability resolution doesn't match terrain — skip overlay.
      return

    self._map_w = W
    self._map_h = H

    # ── height-following positions, one per heightmap sample ─────────────
    # Heightmap sample (i, j) is the CENTER of cell (i, j); the cell spans
    # half-integer world boundaries. Shift mesh by -0.5 so triangles align
    # with those boundaries instead of treating samples as cell corners.
    xx, zz = np.meshgrid(
      np.arange(W, dtype=np.float32),
      np.arange(H, dtype=np.float32),
    )
    verts = np.empty((H * W, 3), dtype=np.float32)
    verts[:, 0] = xx.flatten() - 0.5
    verts[:, 1] = heights.flatten() + self._Y_LIFT
    verts[:, 2] = zz.flatten() - 0.5
    verts = np.ascontiguousarray(verts.flatten())

    # ── triangle index buffer (same topology as terrain) ─────────────────
    xi = np.arange(W - 1, dtype=np.uint32)
    zi = np.arange(H - 1, dtype=np.uint32)
    xg, zg = np.meshgrid(xi, zi)
    tl = (zg * W + xg).flatten()
    tr = tl + 1
    bl = tl + W
    br = bl + 1
    indices = np.empty(len(tl) * 6, dtype=np.uint32)
    indices[0::6] = tl
    indices[1::6] = bl
    indices[2::6] = tr
    indices[3::6] = tr
    indices[4::6] = bl
    indices[5::6] = br
    indices = np.ascontiguousarray(indices)

    self._vao = glGenVertexArrays(1)
    self._vbo = glGenBuffers(1)
    self._ebo = glGenBuffers(1)
    glBindVertexArray(self._vao)
    glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 12, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
    glBindVertexArray(0)
    self._idx_count = int(indices.size)

    # ── walkability mask texture (R8, 0 = walkable, 255 = blocked) ───────
    data = np.ascontiguousarray(mask, dtype=np.uint8)
    self._tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, self._tex)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexImage2D(
      GL_TEXTURE_2D, 0, GL_R8, W, H, 0, GL_RED, GL_UNSIGNED_BYTE, data
    )
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glBindTexture(GL_TEXTURE_2D, 0)

  def free_scene(self) -> None:
    if self._ebo:
      glDeleteBuffers(1, [self._ebo])
      self._ebo = 0
    if self._vbo:
      glDeleteBuffers(1, [self._vbo])
      self._vbo = 0
    if self._vao:
      glDeleteVertexArrays(1, [self._vao])
      self._vao = 0
    if self._tex:
      glDeleteTextures([self._tex])
      self._tex = 0
    self._idx_count = 0
    self._map_w = 0
    self._map_h = 0

  def cleanup(self) -> None:
    self.free_scene()
    if self._prog:
      glDeleteProgram(self._prog)
      self._prog = 0

  def render(self, view: NDArray, proj: NDArray) -> None:
    if not self._idx_count or self._prog == 0 or self._tex == 0:
      return
    view_proj = (proj @ view).astype(np.float32)

    glEnable(GL_DEPTH_TEST)
    glDepthMask(GL_FALSE)  # overlay — don't write depth so things stay readable
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glUseProgram(self._prog)
    _u_mat4(self._prog, "uViewProj", view_proj)

    loc = glGetUniformLocation(self._prog, "uMapW")
    if loc != -1:
      glUniform1f(loc, float(self._map_w))
    loc = glGetUniformLocation(self._prog, "uMapH")
    if loc != -1:
      glUniform1f(loc, float(self._map_h))

    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, self._tex)
    loc = glGetUniformLocation(self._prog, "uWalkTex")
    if loc != -1:
      glUniform1i(loc, 0)

    loc = glGetUniformLocation(self._prog, "uBlockedColor")
    if loc != -1:
      from OpenGL.GL import glUniform4f
      glUniform4f(loc, *self._BLOCKED_COLOR)

    glBindVertexArray(self._vao)
    glDrawElements(GL_TRIANGLES, self._idx_count, GL_UNSIGNED_INT, None)
    glBindVertexArray(0)

    glDepthMask(GL_TRUE)
    glUseProgram(0)
