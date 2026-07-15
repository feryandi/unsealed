"""
Sky dome renderer.

Renders a sky mesh (loaded from sky.ms1) centred on the camera,
using a rotation-only view matrix and the clip.xyww depth trick so
the sky is always drawn behind all other geometry.
"""

from __future__ import annotations

import ctypes
from typing import List, Optional

import numpy as np
from numpy.typing import NDArray
from OpenGL.GL import (
  GL_ARRAY_BUFFER,
  GL_ELEMENT_ARRAY_BUFFER,
  GL_FALSE,
  GL_FLOAT,
  GL_LEQUAL,
  GL_LESS,
  GL_STATIC_DRAW,
  GL_TEXTURE0,
  GL_TEXTURE_2D,
  GL_TRIANGLES,
  GL_UNSIGNED_SHORT,
  glActiveTexture,
  glBindBuffer,
  glBindTexture,
  glBindVertexArray,
  glBufferData,
  glDeleteBuffers,
  glDeleteProgram,
  glDeleteTextures,
  glDeleteVertexArrays,
  glDepthFunc,
  glDepthMask,
  glDrawElements,
  glEnableVertexAttribArray,
  glGenBuffers,
  glGenVertexArrays,
  glGetUniformLocation,
  glUniform1i,
  glUniform4f,
  glUseProgram,
  glVertexAttribPointer,
  GL_TRUE,
)

from ...rendering.shaders import (
  _SKY_FRAG,
  _SKY_VERT,
  _compile_prog,
  _u_mat4,
  _upload_rgba,
)
from ...scenes import ViewerMesh
from ...scenes.scene import _STRIDE_PLAIN


class SkyRenderer:
  """Owns all GL resources for the sky dome: shader, VAO/VBO/EBO, texture."""

  def __init__(self) -> None:
    self._prog: int = 0
    self._vao: int = 0
    self._vbo: int = 0
    self._ebo: int = 0
    self._tex_id: Optional[int] = None
    self._index_count: int = 0
    self._has_sky: bool = False

  def init(self) -> None:
    """Compile the sky shader. Call once after GL context is active."""
    self._prog = _compile_prog(_SKY_VERT, _SKY_FRAG)

  def upload(self, sky_meshes: List[ViewerMesh]) -> None:
    """Upload sky mesh to GPU (frees any previously loaded sky)."""
    self.free_scene()
    if not sky_meshes:
      return

    # Use the first mesh's first primitive as the sky dome geometry.
    mesh = sky_meshes[0]
    if not mesh.primitives:
      return
    prim = mesh.primitives[0]

    self._vao = glGenVertexArrays(1)
    self._vbo = glGenBuffers(1)
    self._ebo = glGenBuffers(1)

    glBindVertexArray(self._vao)

    glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
    glBufferData(
      GL_ARRAY_BUFFER, mesh.vertex_data.nbytes, mesh.vertex_data, GL_STATIC_DRAW
    )

    stride = _STRIDE_PLAIN  # pos(3)+normal(3)+uv(2) × float32 = 32 bytes
    # location 0: position (offset 0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    # location 2: UV (offset 24, skipping normal at offset 12)
    glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
    glEnableVertexAttribArray(2)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ebo)
    glBufferData(
      GL_ELEMENT_ARRAY_BUFFER, prim.indices.nbytes, prim.indices, GL_STATIC_DRAW
    )

    glBindVertexArray(0)

    if prim.image is not None:
      self._tex_id = _upload_rgba(prim.image, prim.image_w, prim.image_h)

    self._index_count = len(prim.indices)
    self._has_sky = True

  def render(self, view: NDArray, proj: NDArray, time: float = 0.0) -> None:
    """Draw the sky dome.

    view/proj are the scene matrices (projection already mirrored).
    """
    if not self._has_sky:
      return

    # Strip camera translation so the dome stays centred on the viewer.
    rot_view = view.copy()
    rot_view[:3, 3] = 0.0

    # Rotate sky 360° every 60 seconds around the Y axis.
    angle = (time / 60.0) * 2.0 * np.pi
    c, s = np.cos(angle), np.sin(angle)
    sky_rot = np.array(
      [[c, 0.0, s, 0.0], [0.0, 1.0, 0.0, 0.0], [-s, 0.0, c, 0.0], [0.0, 0.0, 0.0, 1.0]],
      dtype=np.float32,
    )

    # GL_LEQUAL: sky depth = 1.0 passes where no geometry has written
    # (depth = 1.0 clear).
    glDepthFunc(GL_LEQUAL)
    glDepthMask(GL_FALSE)

    glUseProgram(self._prog)
    _u_mat4(self._prog, "uView", rot_view)
    _u_mat4(self._prog, "uProjection", proj)
    _u_mat4(self._prog, "uModel", sky_rot)

    has_tex = self._tex_id is not None
    glUniform1i(glGetUniformLocation(self._prog, "uHasTexture"), int(has_tex))
    if has_tex:
      glActiveTexture(GL_TEXTURE0)
      glBindTexture(GL_TEXTURE_2D, self._tex_id)
      glUniform1i(glGetUniformLocation(self._prog, "uTexture"), 0)
    glUniform4f(glGetUniformLocation(self._prog, "uBaseColor"), 0.4, 0.6, 0.9, 1.0)

    glBindVertexArray(self._vao)
    glDrawElements(GL_TRIANGLES, self._index_count, GL_UNSIGNED_SHORT, None)
    glBindVertexArray(0)
    glBindTexture(GL_TEXTURE_2D, 0)

    glDepthFunc(GL_LESS)
    glDepthMask(GL_TRUE)
    glUseProgram(0)

  def free_scene(self) -> None:
    """Free per-scene GL objects (keeps shader program)."""
    if self._ebo:
      glDeleteBuffers(1, [self._ebo])
      self._ebo = 0
    if self._vbo:
      glDeleteBuffers(1, [self._vbo])
      self._vbo = 0
    if self._vao:
      glDeleteVertexArrays(1, [self._vao])
      self._vao = 0
    if self._tex_id is not None:
      glDeleteTextures(1, [self._tex_id])
      self._tex_id = None
    self._index_count = 0
    self._has_sky = False

  def cleanup(self) -> None:
    """Free all GL resources including the shader program."""
    self.free_scene()
    if self._prog:
      glDeleteProgram(self._prog)
      self._prog = 0
