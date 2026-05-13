"""Q3StagePass — forward multi-stage shader draws for Quake-3-style materials.

Each primitive can carry several stages (texture, blend mode, tcMod animations).
Stages are drawn back-to-back on top of the deferred-lit colour buffer.
"""

from __future__ import annotations

from typing import List

from numpy.typing import NDArray
from OpenGL.GL import (
    GL_BACK,
    GL_BLEND,
    GL_CULL_FACE,
    GL_DEPTH_TEST,
    GL_ELEMENT_ARRAY_BUFFER,
    GL_FALSE,
    GL_FRONT,
    GL_SRC_ALPHA,
    GL_ONE_MINUS_SRC_ALPHA,
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
    glCullFace,
    glDepthMask,
    glDisable,
    glDrawElements,
    glEnable,
    glGetUniformLocation,
    glUniform1i,
    glUniform4f,
    glUniformMatrix3fv,
    glUseProgram,
)

from ..math_utils import compute_tex_matrix, spherical_billboard
from ..registry import RenderRegistry
from ..shaders import _u_mat4
from ..types import DrawCommand, RenderContext


class Q3StagePass:
    """Forward pass for Q3 multi-stage shader primitives."""

    def __init__(self, q3_prog: int) -> None:
        self._prog = q3_prog

    def render(
        self,
        registry: RenderRegistry,
        commands: List[DrawCommand],
        ctx: RenderContext,
        view: NDArray,
        proj: NDArray,
    ) -> None:
        prog = self._prog
        glUseProgram(prog)
        glEnable(GL_BLEND)
        glDepthMask(GL_FALSE)
        _u_mat4(prog, "uView", view)
        _u_mat4(prog, "uProjection", proj)

        loc_tex_matrix = glGetUniformLocation(prog, "uTexMatrix")
        loc_tc_gen_env = glGetUniformLocation(prog, "uTcGenEnv")
        loc_has_tex    = glGetUniformLocation(prog, "uHasTexture")
        loc_base_color = glGetUniformLocation(prog, "uBaseColor")
        loc_texture    = glGetUniformLocation(prog, "uTexture")

        for cmd in commands:
            buf  = registry.buffers[cmd.entity_id]
            mat  = registry.materials[cmd.entity_id]
            prim = mat.primitives[cmd.primitive_idx]

            glBindVertexArray(buf.vao)
            model_mat = (
                spherical_billboard(cmd.model_matrix, view)
                if prim.is_billboard
                else cmd.model_matrix
            )
            _u_mat4(prog, "uModel", model_mat)

            if prim.two_sided:
                glDisable(GL_CULL_FACE)
                # cull disable + additive glow: must remain visible from all angles
                # even when opaque geometry has already written closer depth.
                glDisable(GL_DEPTH_TEST)
            else:
                # _mirror_x negates clip-space X, reversing all triangle winding.
                # GL_BACK would cull the intended front faces, so use GL_FRONT instead.
                glEnable(GL_CULL_FACE)
                glCullFace(GL_FRONT)
                glEnable(GL_DEPTH_TEST)

            for stage in prim.q3_stages:
                glBlendFunc(stage.blend_src, stage.blend_dst)

                tex_mat = compute_tex_matrix(stage.tc_mods, ctx.time)
                glUniformMatrix3fv(loc_tex_matrix, 1, GL_FALSE, tex_mat)
                glUniform1i(loc_tc_gen_env, int(stage.tc_gen_env))

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
                    glUniform1i(loc_has_tex, 1)
                    glUniform1i(loc_texture, 0)
                else:
                    glBindTexture(GL_TEXTURE_2D, 0)
                    glUniform1i(loc_has_tex, 0)

                c = prim.base_color
                glUniform4f(loc_base_color, c[0], c[1], c[2], c[3])

                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, prim.ebo)
                glDrawElements(GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None)

        glDisable(GL_CULL_FACE)
        glCullFace(GL_BACK)  # restore default
        glEnable(GL_DEPTH_TEST)  # restore (may have been disabled for two_sided prims)
        glBindVertexArray(0)
        glDepthMask(GL_TRUE)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glUseProgram(0)
