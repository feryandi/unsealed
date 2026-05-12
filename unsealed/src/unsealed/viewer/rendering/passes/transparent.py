"""
TransparentPass — forward pass for primitives with base_color alpha < 1.

Phase 3.2: init() accepts mgl context.
"""
from __future__ import annotations

from typing import List, Optional

import moderngl
import numpy as np
from numpy.typing import NDArray
from OpenGL.GL import (
  GL_BLEND,
  GL_ELEMENT_ARRAY_BUFFER,
  GL_ONE_MINUS_SRC_ALPHA,
  GL_SRC_ALPHA,
  GL_TEXTURE0,
  GL_TEXTURE_2D,
  GL_TRIANGLES,
  GL_UNSIGNED_SHORT,
  glActiveTexture,
  glBindBuffer,
  glBindTexture,
  glBindVertexArray,
  glBlendFunc,
  glDepthMask,
  glDrawElements,
  glDrawElementsInstanced,
  glEnable,
  glUseProgram,
)

from ..registry import RenderRegistry
from ..shaders import (
  ShaderProgram,
  _INST_VERT,
  _MESH_FRAG,
  _MESH_VERT,
  _SKIN_VERT,
  _compile_prog,
)
from ..types import (
  DrawCommand,
  PassState,
  RenderContext,
  ShaderVariant,
  _GpuPrimitive,
  _IDENTITY_BONE_FLAT,
  _MAX_BONES,
)
from .base import RenderPass


def _bind_primitive_material(prog: ShaderProgram, prim: _GpuPrimitive) -> None:
  prog.i1("uHasTexture", int(prim.texture_id is not None))
  if prim.texture_id is not None:
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, prim.texture_id)
    prog.i1("uTexture", 0)
  else:
    glBindTexture(GL_TEXTURE_2D, 0)
  c = prim.base_color
  prog.f4("uBaseColor", c[0], c[1], c[2], c[3])


class TransparentPass(RenderPass):
  """Forward pass for transparent (alpha < 1) primitives, sorted back-to-front."""

  def __init__(self) -> None:
    self._mesh_prog: ShaderProgram | None = None
    self._skin_prog: ShaderProgram | None = None
    self._inst_prog: ShaderProgram | None = None

  def init(self, mgl: moderngl.Context) -> None:
    self._mesh_prog = _compile_prog(_MESH_VERT, _MESH_FRAG)
    self._skin_prog = _compile_prog(_SKIN_VERT, _MESH_FRAG)
    self._inst_prog = _compile_prog(_INST_VERT, _MESH_FRAG)

  def cleanup(self) -> None:
    for attr in ("_mesh_prog", "_skin_prog", "_inst_prog"):
      prog = getattr(self, attr, None)
      if prog is not None:
        prog.delete()
        setattr(self, attr, None)

  def execute(
    self,
    ctx: RenderContext,
    state: PassState,
    registry: RenderRegistry,
  ) -> None:
    if not state.transparent:
      return

    # Sort back-to-front for correct alpha blending
    camera_pos: Optional[NDArray] = None
    if hasattr(ctx.camera, "position"):
      try:
        camera_pos = np.array(ctx.camera.position(), dtype=np.float32)
      except Exception:
        pass
    if camera_pos is not None:
      state.transparent.sort(
        key=lambda c: float(
          (c.model_matrix[:3, 3] - camera_pos).dot(state.view[:3, 2])
        ),
        reverse=True,
      )

    self._draw(state.transparent, state.view, state.proj, state.light_dir, registry)

  def _draw(
    self,
    commands: List[DrawCommand],
    view: NDArray,
    proj: NDArray,
    light_dir: NDArray,
    registry: RenderRegistry,
  ) -> None:
    assert self._mesh_prog is not None
    assert self._skin_prog is not None
    assert self._inst_prog is not None

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDepthMask(False)

    prog_map = {
      ShaderVariant.SKINNED: self._skin_prog,
      ShaderVariant.INSTANCED: self._inst_prog,
    }

    for p in (self._mesh_prog, self._skin_prog, self._inst_prog):
      p.use()
      p.mat4("uView", view)
      p.mat4("uProjection", proj)
      p.vec3("uLightDir", light_dir)

    for cmd in commands:
      buf = registry.buffers[cmd.entity_id]
      mat = registry.materials[cmd.entity_id]
      prim = mat.primitives[cmd.primitive_idx]

      prog = prog_map.get(cmd.variant, self._mesh_prog)
      prog.use()
      prog.mat4("uModel", cmd.model_matrix)

      if cmd.variant == ShaderVariant.SKINNED:
        if cmd.bone_matrices_flat is not None:
          prog.bone_matrices("uBoneMatrices[0]", cmd.bone_count, cmd.bone_matrices_flat)
        else:
          prog.bone_matrices("uBoneMatrices[0]", _MAX_BONES, _IDENTITY_BONE_FLAT)

      _bind_primitive_material(prog, prim)
      glBindVertexArray(buf.vao)
      glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, prim.ebo)
      if cmd.instance_count > 1:
        glDrawElementsInstanced(
          GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None, cmd.instance_count
        )
      else:
        glDrawElements(GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None)

    glBindVertexArray(0)
    glDepthMask(True)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glUseProgram(0)
