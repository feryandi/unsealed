"""ForwardPass — alpha-blended forward draws for transparent primitives.

Runs after the deferred lighting pass. Uses the same forward programs as
the wireframe/selection passes (mesh / skin / inst), keyed by ShaderVariant.
"""

from __future__ import annotations

from typing import Dict, List

from numpy.typing import NDArray
from OpenGL.GL import (
  GL_BLEND,
  GL_ELEMENT_ARRAY_BUFFER,
  GL_FALSE,
  GL_ONE_MINUS_SRC_ALPHA,
  GL_SRC_ALPHA,
  GL_TEXTURE0,
  GL_TEXTURE_2D,
  GL_TRIANGLES,
  GL_TRUE,
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
  glGetUniformLocation,
  glUniform1i,
  glUniform4f,
  glUniformMatrix4fv,
  glUseProgram,
)

from ..registry import RenderRegistry
from ..shaders import _u_mat4, _u_vec3
from ..types import (
  DrawCommand,
  ShaderVariant,
  _GpuPrimitive,
  _IDENTITY_BONE_FLAT,
  _MAX_BONES,
)


def _bind_primitive_material(prog: int, prim: _GpuPrimitive) -> None:
  """Bind texture/colour for a forward draw. Caller manages depth mask."""
  glUniform1i(
    glGetUniformLocation(prog, "uHasTexture"), int(prim.texture_id is not None)
  )
  glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

  if prim.texture_id is not None:
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, prim.texture_id)
    glUniform1i(glGetUniformLocation(prog, "uTexture"), 0)
  else:
    glBindTexture(GL_TEXTURE_2D, 0)
  c = prim.base_color
  glUniform4f(glGetUniformLocation(prog, "uBaseColor"), c[0], c[1], c[2], c[3])


class ForwardPass:
  """Forward alpha-blended pass for transparent (base_color.a < 1) primitives."""

  def __init__(self, mesh_prog: int, skin_prog: int, inst_prog: int) -> None:
    self._mesh_prog = mesh_prog
    self._skin_prog = skin_prog
    self._inst_prog = inst_prog
    self._prog_map: Dict[ShaderVariant, int] = {
      ShaderVariant.SKINNED: skin_prog,
      ShaderVariant.INSTANCED: inst_prog,
    }

  def render(
    self,
    registry: RenderRegistry,
    commands: List[DrawCommand],
    view: NDArray,
    proj: NDArray,
    light_dir: NDArray,
  ) -> None:
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDepthMask(GL_FALSE)

    # Shared uniforms uploaded to all three forward programs.
    for prog in (self._mesh_prog, self._skin_prog, self._inst_prog):
      glUseProgram(prog)
      _u_mat4(prog, "uView", view)
      _u_mat4(prog, "uProjection", proj)
      _u_vec3(prog, "uLightDir", light_dir)

    for cmd in commands:
      buf = registry.buffers[cmd.entity_id]
      mat = registry.materials[cmd.entity_id]
      prim = mat.primitives[cmd.primitive_idx]

      prog = self._prog_map.get(cmd.variant, self._mesh_prog)
      glUseProgram(prog)
      _u_mat4(prog, "uModel", cmd.model_matrix)

      if cmd.variant == ShaderVariant.SKINNED:
        loc_b = glGetUniformLocation(prog, "uBoneMatrices[0]")
        if loc_b != -1:
          if cmd.bone_matrices_flat is not None:
            glUniformMatrix4fv(loc_b, cmd.bone_count, GL_TRUE, cmd.bone_matrices_flat)
          else:
            glUniformMatrix4fv(loc_b, _MAX_BONES, GL_TRUE, _IDENTITY_BONE_FLAT)

      _bind_primitive_material(prog, prim)
      # _bind_primitive_material leaves depth mask alone; ensure it's FALSE so
      # transparent surfaces don't occlude each other during this pass.
      glDepthMask(GL_FALSE)

      glBindVertexArray(buf.vao)
      glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, prim.ebo)
      if cmd.instance_count > 1:
        glDrawElementsInstanced(
          GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None, cmd.instance_count
        )
      else:
        glDrawElements(GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None)

    glBindVertexArray(0)
    glDepthMask(GL_TRUE)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glUseProgram(0)
