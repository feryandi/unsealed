"""
OverlayPass — wireframe toggle and selection highlight.

Reads geometry from the RenderRegistry and draws line-mode polygons offset
slightly toward the camera, on top of the deferred-lit colour buffer.
"""
from __future__ import annotations

from numpy.typing import NDArray
from OpenGL.GL import (
    GL_ELEMENT_ARRAY_BUFFER,
    GL_FILL,
    GL_FRONT_AND_BACK,
    GL_LINE,
    GL_POLYGON_OFFSET_LINE,
    GL_TRIANGLES,
    GL_UNSIGNED_SHORT,
    glBindBuffer,
    glBindVertexArray,
    glDisable,
    glDrawElements,
    glDrawElementsInstanced,
    glEnable,
    glGetUniformLocation,
    glPolygonMode,
    glPolygonOffset,
    glUniform4f,
    glUseProgram,
)

from ..registry import RenderRegistry
from ..shaders import _u_mat4


class OverlayPass:
    """Renders wireframe and selection-highlight overlays using pre-compiled programs."""

    def __init__(self, wire_prog: int, sel_prog: int, sel_inst_prog: int) -> None:
        self._wire_prog = wire_prog
        self._sel_prog = sel_prog
        self._sel_inst_prog = sel_inst_prog

    def render_wireframe(
        self, registry: RenderRegistry, view: NDArray, proj: NDArray
    ) -> None:
        glUseProgram(self._wire_prog)
        _u_mat4(self._wire_prog, "uView", view)
        _u_mat4(self._wire_prog, "uProjection", proj)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glEnable(GL_POLYGON_OFFSET_LINE)
        glPolygonOffset(-1.0, -1.0)

        for eid in registry.entity_ids():
            buf = registry.buffers[eid]
            mat = registry.materials[eid]
            xform = registry.transforms[eid]
            _u_mat4(self._wire_prog, "uModel", xform.model_matrix)
            glBindVertexArray(buf.vao)
            for prim in mat.primitives:
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, prim.ebo)
                glDrawElements(GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None)

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glDisable(GL_POLYGON_OFFSET_LINE)
        glBindVertexArray(0)
        glUseProgram(0)

    def render_selection(
        self,
        registry: RenderRegistry,
        entity_id: int,
        view: NDArray,
        proj: NDArray,
    ) -> None:
        if entity_id not in registry.buffers:
            return

        buf = registry.buffers[entity_id]
        mat = registry.materials[entity_id]
        xform = registry.transforms[entity_id]

        prog = self._sel_inst_prog if buf.instance_count > 1 else self._sel_prog
        glUseProgram(prog)
        _u_mat4(prog, "uView", view)
        _u_mat4(prog, "uProjection", proj)
        glUniform4f(glGetUniformLocation(prog, "uColor"), 1.0, 0.85, 0.1, 1.0)

        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glEnable(GL_POLYGON_OFFSET_LINE)
        glPolygonOffset(-1.0, -1.0)

        glBindVertexArray(buf.vao)
        if buf.instance_count > 1:
            _u_mat4(prog, "uModel", xform.model_matrix)
            for prim in mat.primitives:
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, prim.ebo)
                glDrawElementsInstanced(
                    GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None, buf.instance_count
                )
        else:
            model = (
                buf.inst_mats_cpu[0] @ xform.model_matrix
                if buf.inst_mats_cpu is not None
                else xform.model_matrix
            )
            _u_mat4(prog, "uModel", model)
            for prim in mat.primitives:
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, prim.ebo)
                glDrawElements(GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None)

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glDisable(GL_POLYGON_OFFSET_LINE)
        glBindVertexArray(0)
        glUseProgram(0)
