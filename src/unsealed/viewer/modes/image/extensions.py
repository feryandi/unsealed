"""Image-mode RenderExtension: draws the 2-D texture quad.

Image mode has no 3D geometry — the renderer's mesh passes are no-ops when
an ImageScene is loaded. This extension runs in the BACKGROUND phase (the
earliest mode-pluggable phase), recomputes the projection directly from the
ImageCamera (no mirror-x flip applied), and draws the textured quad.
"""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING, Optional

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

from ...rendering.shaders import _IMG_FRAG, _IMG_VERT, _compile_prog, _u_mat4, _upload_rgba
from ..base import RenderPhase
from .camera import ImageCamera
from .scene import ImageScene

if TYPE_CHECKING:
  from numpy.typing import NDArray

  from ...rendering import RenderContext
  from ...scenes import ViewerScene


class ImageExtension:
  """Renders the 2-D texture quad. Owned by ImageMode."""
  phase = RenderPhase.BACKGROUND

  def __init__(self) -> None:
    self._prog: int = 0
    self._vao: int = 0
    self._vbo: int = 0
    self._tex_id: Optional[int] = None
    self._image_w: int = 0
    self._image_h: int = 0

  def init(self) -> None:
    self._prog = _compile_prog(_IMG_VERT, _IMG_FRAG)
    self._vao = glGenVertexArrays(1)
    self._vbo = glGenBuffers(1)

  def upload(self, scene: "ViewerScene") -> None:
    self.free_scene()
    if not isinstance(scene, ImageScene):
      return
    if scene.image is not None:
      self._tex_id = _upload_rgba(scene.image, scene.image_w, scene.image_h)
    self._image_w = scene.image_w
    self._image_h = scene.image_h

  def render(self, ctx: "RenderContext", view: "NDArray", proj: "NDArray") -> None:
    if self._tex_id is None or not isinstance(ctx.camera, ImageCamera):
      return

    # Recompute proj directly from the ImageCamera — the proj passed in has
    # the renderer's mirror-x applied, which is wrong for 2-D image mode.
    aspect = ctx.width / max(ctx.height, 1)
    mvp = ctx.camera.projection_matrix(aspect, ctx.width, ctx.height)

    hw = self._image_w * 0.5
    hh = self._image_h * 0.5
    verts = np.array(
      [
        -hw, -hh, 0.0, 0.0, 0.0,
         hw, -hh, 0.0, 1.0, 0.0,
         hw,  hh, 0.0, 1.0, 1.0,
        -hw, -hh, 0.0, 0.0, 0.0,
         hw,  hh, 0.0, 1.0, 1.0,
        -hw,  hh, 0.0, 0.0, 1.0,
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

    glDisable(GL_DEPTH_TEST)
    glUseProgram(self._prog)
    _u_mat4(self._prog, "uMVP", mvp)
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, self._tex_id)
    glUniform1i(glGetUniformLocation(self._prog, "uTexture"), 0)
    glDrawArrays(GL_TRIANGLES, 0, 6)
    glBindVertexArray(0)
    glBindTexture(GL_TEXTURE_2D, 0)
    glUseProgram(0)
    glEnable(GL_DEPTH_TEST)

  def free_scene(self) -> None:
    if self._tex_id is not None:
      glDeleteTextures(1, [self._tex_id])
      self._tex_id = None
    self._image_w = 0
    self._image_h = 0

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
