"""
ImagePass — 2-D image viewer pass (tex / te1 files).

Phase 3.2: VBO for the image quad uses ModernGL; VAO still raw GL.
"""
from __future__ import annotations

import ctypes
from typing import Optional

import moderngl
import numpy as np
from OpenGL.GL import (
  GL_ARRAY_BUFFER,
  GL_DEPTH_TEST,
  GL_DYNAMIC_DRAW,
  GL_FLOAT,
  GL_FALSE,
  GL_TEXTURE0,
  GL_TEXTURE_2D,
  GL_TRIANGLES,
  glActiveTexture,
  glBindBuffer,
  glBindTexture,
  glBindVertexArray,
  glBufferData,
  glDeleteTextures,
  glDisable,
  glDrawArrays,
  glDisableVertexAttribArray,
  glEnable,
  glEnableVertexAttribArray,
  glGenBuffers,
  glGenVertexArrays,
  glDeleteVertexArrays,
  glUseProgram,
  glVertexAttribPointer,
)

from ...camera import ImageCamera
from ..registry import RenderRegistry
from ..shaders import ShaderProgram, _IMG_FRAG, _IMG_VERT, _compile_prog, _upload_rgba
from ..types import PassState, RenderContext
from .base import RenderPass


class ImagePass(RenderPass):
  """Renders a 2-D RGBA texture using an orthographic projection."""

  def __init__(self) -> None:
    self._prog: ShaderProgram | None = None
    self._vao: int = 0
    self._vbo: int = 0  # raw GL VBO (dynamic, updated each frame)
    self._tex_id: Optional[int] = None
    self._image_w: int = 0
    self._image_h: int = 0

  def init(self, mgl: moderngl.Context) -> None:
    self._prog = _compile_prog(_IMG_VERT, _IMG_FRAG)
    self._vao = glGenVertexArrays(1)
    # Keep a plain GL VBO for the dynamic quad (updated every frame)
    self._vbo = glGenBuffers(1)

  def load(self, image: object, image_w: int, image_h: int) -> None:
    """Upload an RGBA image for display. Call from load_scene()."""
    self.free()
    if image is not None:
      self._tex_id = _upload_rgba(image, image_w, image_h)
    self._image_w = image_w
    self._image_h = image_h

  def free(self) -> None:
    """Release the uploaded texture."""
    if self._tex_id is not None:
      glDeleteTextures(1, [self._tex_id])
      self._tex_id = None
    self._image_w = 0
    self._image_h = 0

  def cleanup(self) -> None:
    self.free()
    if self._prog is not None:
      self._prog.delete()
      self._prog = None
    if self._vao:
      glDeleteVertexArrays(1, [self._vao])
      self._vao = 0
    if self._vbo:
      from OpenGL.GL import glDeleteBuffers
      glDeleteBuffers(1, [self._vbo])
      self._vbo = 0

  def execute(
    self,
    ctx: RenderContext,
    state: PassState,
    registry: RenderRegistry,
  ) -> None:
    assert self._prog is not None
    if self._tex_id is None or self._image_w == 0 or self._image_h == 0:
      return
    if not isinstance(ctx.camera, ImageCamera):
      return

    aspect = ctx.width / max(ctx.height, 1)
    proj = ctx.camera.projection_matrix(aspect, ctx.width, ctx.height)

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
    self._prog.use()
    self._prog.mat4("uMVP", proj)
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, self._tex_id)
    self._prog.i1("uTexture", 0)
    glDrawArrays(GL_TRIANGLES, 0, 6)
    glDisableVertexAttribArray(0)
    glDisableVertexAttribArray(1)
    glBindVertexArray(0)
    glBindTexture(GL_TEXTURE_2D, 0)
    glUseProgram(0)
    glEnable(GL_DEPTH_TEST)
