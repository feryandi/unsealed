"""
GBufferPass — MRT framebuffer and opaque geometry draw loop.

The FBO has two colour attachments (albedo RGBA8, world-space normal RGBA16F)
and a shared depth renderbuffer (DEPTH_COMPONENT24).  The FBO is lazily
resized whenever the window dimensions change.

Three compiled programs (mesh / skin / inst built with gbuffer.frag.glsl)
are owned here; the existing vertex shaders output vFragPos / vNormal /
vTexCoord so they work unchanged with the new G-Buffer fragment shader.
"""

from __future__ import annotations

from typing import List

from numpy.typing import NDArray
from OpenGL.GL import (
  GL_COLOR_ATTACHMENT0,
  GL_COLOR_ATTACHMENT1,
  GL_COLOR_BUFFER_BIT,
  GL_DEPTH_ATTACHMENT,
  GL_DEPTH_BUFFER_BIT,
  GL_DEPTH_COMPONENT24,
  GL_DRAW_FRAMEBUFFER,
  GL_ELEMENT_ARRAY_BUFFER,
  GL_FRAMEBUFFER,
  GL_HALF_FLOAT,
  GL_NEAREST,
  GL_READ_FRAMEBUFFER,
  GL_RGBA,
  GL_RGBA16F,
  GL_TEXTURE_2D,
  GL_TEXTURE_MAG_FILTER,
  GL_TEXTURE_MIN_FILTER,
  GL_TEXTURE0,
  GL_TRIANGLES,
  GL_TRUE,
  GL_UNSIGNED_BYTE,
  GL_UNSIGNED_SHORT,
  glActiveTexture,
  glBindBuffer,
  glBindFramebuffer,
  glBindTexture,
  glBindVertexArray,
  glBlitFramebuffer,
  glClear,
  glDeleteFramebuffers,
  glDeleteProgram,
  glDeleteRenderbuffers,
  glDeleteTextures,
  glDrawBuffers,
  glDrawElements,
  glDrawElementsInstanced,
  glFramebufferRenderbuffer,
  glFramebufferTexture2D,
  glGenFramebuffers,
  glGenRenderbuffers,
  glGenTextures,
  glGetUniformLocation,
  glBindRenderbuffer,
  glClearColor,
  glRenderbufferStorage,
  glTexImage2D,
  glTexParameteri,
  glUniform1i,
  glUniform4f,
  glUniformMatrix4fv,
  glUseProgram,
  GL_RENDERBUFFER,
  glGetFloatv,
  GL_COLOR_CLEAR_VALUE,
)

from ..registry import RenderRegistry
from ..shaders import _compile_prog, _u_mat4
from ..types import (
  DrawCommand,
  ShaderVariant,
  _GpuPrimitive,
  _IDENTITY_BONE_FLAT,
  _MAX_BONES,
)


def _bind_prim_gbuffer(prog: int, prim: _GpuPrimitive) -> None:
  """Bind texture / flat colour for a G-Buffer draw — no depth mask / blend changes."""
  glUniform1i(
    glGetUniformLocation(prog, "uHasTexture"), int(prim.texture_id is not None)
  )
  if prim.texture_id is not None:
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, prim.texture_id)
    glUniform1i(glGetUniformLocation(prog, "uTexture"), 0)
  else:
    glBindTexture(GL_TEXTURE_2D, 0)
  c = prim.base_color
  glUniform4f(glGetUniformLocation(prog, "uBaseColor"), c[0], c[1], c[2], c[3])


class GBufferPass:
  """Manages the G-Buffer FBO and owns the three G-Buffer shader programs."""

  def __init__(self) -> None:
    self._fbo: int = 0
    self._albedo_tex: int = 0
    self._normal_tex: int = 0
    self._depth_rbo: int = 0
    self._w: int = 0
    self._h: int = 0
    self._mesh_prog: int = 0
    self._skin_prog: int = 0
    self._inst_prog: int = 0

  def init(
    self,
    mesh_vert: str,
    skin_vert: str,
    inst_vert: str,
    gbuf_frag: str,
  ) -> None:
    """Compile the three G-Buffer programs (reuse existing vert shaders)."""
    self._mesh_prog = _compile_prog(mesh_vert, gbuf_frag)
    self._skin_prog = _compile_prog(skin_vert, gbuf_frag)
    self._inst_prog = _compile_prog(inst_vert, gbuf_frag)

  def begin(self, width: int, height: int) -> None:
    """Bind the G-Buffer FBO and clear it. Resizes FBO if dimensions changed."""
    if width != self._w or height != self._h:
      self._setup(width, height)
    glBindFramebuffer(GL_FRAMEBUFFER, self._fbo)
    # Clear with alpha=0 so background pixels (where nothing was drawn) are
    # discarded by the lighting frag's `if (albedo.a < 0.01) discard;`.
    # This lets the default FBO's clear colour show through as the scene background.
    saved = glGetFloatv(GL_COLOR_CLEAR_VALUE)
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glClear(int(GL_COLOR_BUFFER_BIT) | int(GL_DEPTH_BUFFER_BIT))
    glClearColor(saved[0], saved[1], saved[2], saved[3])

  def end(self) -> None:
    """Unbind the G-Buffer FBO, returning to the default framebuffer."""
    glBindFramebuffer(GL_FRAMEBUFFER, 0)

  def blit_depth(self, width: int, height: int) -> None:
    """Copy G-Buffer depth to the default FBO so forward passes depth-test correctly."""
    glBindFramebuffer(GL_READ_FRAMEBUFFER, self._fbo)
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0)
    glBlitFramebuffer(
      0,
      0,
      width,
      height,
      0,
      0,
      width,
      height,
      int(GL_DEPTH_BUFFER_BIT),
      GL_NEAREST,
    )
    glBindFramebuffer(GL_FRAMEBUFFER, 0)

  @property
  def albedo_tex(self) -> int:
    return self._albedo_tex

  @property
  def normal_tex(self) -> int:
    return self._normal_tex

  def draw(
    self,
    registry: RenderRegistry,
    commands: List[DrawCommand],
    view: NDArray,
    proj: NDArray,
  ) -> None:
    """Execute the opaque geometry draw loop into the G-Buffer."""
    if not commands:
      return

    # Upload view/proj shared uniforms once per program
    for prog in (self._mesh_prog, self._skin_prog, self._inst_prog):
      glUseProgram(prog)
      _u_mat4(prog, "uView", view)
      _u_mat4(prog, "uProjection", proj)

    current_prog = -1
    for cmd in commands:
      buf = registry.buffers[cmd.entity_id]
      mat = registry.materials[cmd.entity_id]
      prim = mat.primitives[cmd.primitive_idx]

      prog = self._prog_for(cmd.variant)
      if prog != current_prog:
        glUseProgram(prog)
        current_prog = prog
      _u_mat4(prog, "uModel", cmd.model_matrix)

      if cmd.variant == ShaderVariant.SKINNED:
        loc_b = glGetUniformLocation(prog, "uBoneMatrices[0]")
        if loc_b != -1:
          if cmd.bone_matrices_flat is not None:
            glUniformMatrix4fv(loc_b, cmd.bone_count, GL_TRUE, cmd.bone_matrices_flat)
          else:
            glUniformMatrix4fv(loc_b, _MAX_BONES, GL_TRUE, _IDENTITY_BONE_FLAT)

      _bind_prim_gbuffer(prog, prim)
      glBindVertexArray(buf.vao)
      glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, prim.ebo)
      if cmd.instance_count > 1:
        glDrawElementsInstanced(
          GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None, cmd.instance_count
        )
      else:
        glDrawElements(GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None)

    glBindVertexArray(0)
    glUseProgram(0)

  def cleanup(self) -> None:
    self._teardown()
    for prog in (self._mesh_prog, self._skin_prog, self._inst_prog):
      if prog:
        glDeleteProgram(prog)
    self._mesh_prog = self._skin_prog = self._inst_prog = 0

  # ── private ───────────────────────────────────────────────────────────────

  def _prog_for(self, variant: ShaderVariant) -> int:
    if variant == ShaderVariant.SKINNED:
      return self._skin_prog
    if variant == ShaderVariant.INSTANCED:
      return self._inst_prog
    return self._mesh_prog

  def _setup(self, w: int, h: int) -> None:
    self._teardown()

    self._fbo = glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER, self._fbo)

    # Albedo attachment — RGBA8
    self._albedo_tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, self._albedo_tex)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glFramebufferTexture2D(
      GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self._albedo_tex, 0
    )

    # Normal attachment — RGBA16F
    self._normal_tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, self._normal_tex)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA16F, w, h, 0, GL_RGBA, GL_HALF_FLOAT, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glFramebufferTexture2D(
      GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, GL_TEXTURE_2D, self._normal_tex, 0
    )

    # Depth renderbuffer
    self._depth_rbo = glGenRenderbuffers(1)
    glBindRenderbuffer(GL_RENDERBUFFER, self._depth_rbo)
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, w, h)
    glFramebufferRenderbuffer(
      GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, self._depth_rbo
    )

    glDrawBuffers([GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1])

    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    glBindTexture(GL_TEXTURE_2D, 0)
    self._w, self._h = w, h

  def _teardown(self) -> None:
    if self._fbo:
      glDeleteFramebuffers(1, [self._fbo])
      self._fbo = 0
    if self._albedo_tex:
      glDeleteTextures(1, [self._albedo_tex])
      self._albedo_tex = 0
    if self._normal_tex:
      glDeleteTextures(1, [self._normal_tex])
      self._normal_tex = 0
    if self._depth_rbo:
      glDeleteRenderbuffers(1, [self._depth_rbo])
      self._depth_rbo = 0
    self._w = self._h = 0
