"""
Q3Pass — forward pass for Q3 multi-stage shader primitives.

Phase 3.2: init() accepts mgl context.
"""
from __future__ import annotations

from typing import List, Tuple

import moderngl
import numpy as np
from numpy.typing import NDArray
from OpenGL.GL import (
  GL_BACK,
  GL_CULL_FACE,
  GL_DEPTH_TEST,
  GL_ELEMENT_ARRAY_BUFFER,
  GL_FRONT,
  GL_LEQUAL,
  GL_TEXTURE0,
  GL_TEXTURE_2D,
  GL_TRIANGLES,
  GL_UNSIGNED_SHORT,
  glBindBuffer,
  glBindTexture,
  glBindVertexArray,
  glActiveTexture,
  glCullFace,
  glDepthFunc,
  glDepthMask,
  glDisable,
  glDrawElements,
  glEnable,
  glUseProgram,
  GL_ONE_MINUS_SRC_ALPHA,
  GL_SRC_ALPHA,
  GL_BLEND,
  glBlendFunc,
)

from ..registry import RenderRegistry
from ..shaders import ShaderProgram, _Q3STAGE_FRAG, _Q3STAGE_VERT, _compile_prog
from ..types import DrawCommand, PassState, RenderContext
from .base import RenderPass


def _spherical_billboard(model_mat: NDArray, view: NDArray) -> NDArray:
  """Replace rotation with camera orientation so the quad always faces the camera."""
  pos = model_mat[:3, 3]
  scale_x = float(np.linalg.norm(model_mat[:3, 0]))
  scale_y = float(np.linalg.norm(model_mat[:3, 1]))
  scale_z = float(np.linalg.norm(model_mat[:3, 2]))

  right = view[0, :3]
  up = view[1, :3]
  fwd = -view[2, :3]

  bb = np.identity(4, dtype=np.float32)
  bb[:3, 0] = right * scale_x
  bb[:3, 1] = up * scale_y
  bb[:3, 2] = fwd * scale_z
  bb[:3, 3] = pos
  return bb


def _compute_tex_matrix(
  tc_mods: List[Tuple[str, Tuple[float, ...]]], time: float
) -> NDArray:
  """
  Compose a column-major 3×3 UV-transform matrix from a list of tcMod ops.

  Supported ops: ("rotate", (deg_per_sec,)), ("scroll", (s, t)), ("scale", (s, t))
  """
  result = np.identity(3, dtype=np.float32)

  for mod_type, params in tc_mods:
    if mod_type == "rotate" and len(params) >= 1:
      angle = np.radians((params[0] * time) % 360.0)
      cos_a, sin_a = np.float32(np.cos(angle)), np.float32(np.sin(angle))
      t_to = np.array([[1, 0, -0.5], [0, 1, -0.5], [0, 0, 1]], dtype=np.float32)
      rot = np.array(
        [[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]], dtype=np.float32
      )
      t_back = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1]], dtype=np.float32)
      result = t_back @ rot @ t_to @ result

    elif mod_type == "scroll" and len(params) >= 2:
      tx, ty = params[0] * time, -params[1] * time
      tx = max(min(tx, 1e6), -1e6)
      ty = max(min(ty, 1e6), -1e6)
      trans = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], dtype=np.float32)
      result = trans @ result

    elif mod_type == "scale" and len(params) >= 2:
      sx, sy = params[0], params[1]
      scale = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], dtype=np.float32)
      result = scale @ result

  return result.T.flatten()


class Q3Pass(RenderPass):
  """Forward pass for Q3 multi-stage shader primitives."""

  def __init__(self) -> None:
    self._prog: ShaderProgram | None = None

  def init(self, mgl: moderngl.Context) -> None:
    self._prog = _compile_prog(_Q3STAGE_VERT, _Q3STAGE_FRAG)

  def cleanup(self) -> None:
    if self._prog is not None:
      self._prog.delete()
      self._prog = None

  def execute(
    self,
    ctx: RenderContext,
    state: PassState,
    registry: RenderRegistry,
  ) -> None:
    if not state.q3 or not ctx.q3_enabled:
      return
    self._draw(state.q3, ctx, state.view, state.proj, registry)

  def _draw(
    self,
    commands: List[DrawCommand],
    ctx: RenderContext,
    view: NDArray,
    proj: NDArray,
    registry: RenderRegistry,
  ) -> None:
    assert self._prog is not None
    prog = self._prog
    prog.use()
    glEnable(GL_BLEND)
    glDepthMask(False)
    prog.mat4("uView", view)
    prog.mat4("uProjection", proj)

    for cmd in commands:
      buf = registry.buffers[cmd.entity_id]
      mat = registry.materials[cmd.entity_id]
      prim = mat.primitives[cmd.primitive_idx]

      glBindVertexArray(buf.vao)
      model_mat = (
        _spherical_billboard(cmd.model_matrix, view)
        if prim.is_billboard
        else cmd.model_matrix
      )
      prog.mat4("uModel", model_mat)

      if prim.two_sided:
        glDisable(GL_CULL_FACE)
        glDepthMask(False)
        glDepthFunc(GL_LEQUAL)
      else:
        # _mirror_x negates clip-space X, reversing all triangle winding.
        # GL_BACK would cull the intended front faces, so use GL_FRONT instead.
        glEnable(GL_CULL_FACE)
        glCullFace(GL_FRONT)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

      for stage in prim.q3_stages:
        glBlendFunc(stage.blend_src, stage.blend_dst)

        tex_mat = _compute_tex_matrix(stage.tc_mods, ctx.time)
        prog.mat3("uTexMatrix", tex_mat)
        prog.i1("uTcGenEnv", int(stage.tc_gen_env))

        if stage.anim_tex_ids:
          frame_idx = int(stage.anim_fps * ctx.time) % len(stage.anim_tex_ids)
          active_tex = stage.anim_tex_ids[frame_idx]
        elif stage.tex_id is not None:
          active_tex = stage.tex_id
        else:
          active_tex = None

        if active_tex is not None:
          glActiveTexture(GL_TEXTURE0)
          glBindTexture(GL_TEXTURE_2D, active_tex)
          prog.i1("uHasTexture", 1)
          prog.i1("uTexture", 0)
        else:
          glBindTexture(GL_TEXTURE_2D, 0)
          prog.i1("uHasTexture", 0)

        c = prim.base_color
        prog.f4("uBaseColor", c[0], c[1], c[2], c[3])

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, prim.ebo)
        glDrawElements(GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None)

    glDisable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glEnable(GL_DEPTH_TEST)
    glBindVertexArray(0)
    glDepthMask(True)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glUseProgram(0)
