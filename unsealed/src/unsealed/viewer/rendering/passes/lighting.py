"""
LightingPass — fullscreen deferred Blinn-Phong lighting quad.

Reads the G-Buffer albedo and normal textures, computes the same
ambient + diffuse formula used in the old forward mesh.frag.glsl,
and writes the final lit colour to the default framebuffer.
"""
from __future__ import annotations

import ctypes

import numpy as np
from numpy.typing import NDArray
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_FALSE,
    GL_FLOAT,
    GL_STATIC_DRAW,
    GL_TEXTURE0,
    GL_TEXTURE1,
    GL_TEXTURE_2D,
    GL_TRIANGLES,
    glBindBuffer,
    glBindTexture,
    glBindVertexArray,
    glBufferData,
    glDeleteBuffers,
    glDeleteProgram,
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
    GL_DEPTH_TEST,
)

from ..shaders import _compile_prog, _u_vec3
from ..shaders import _LIGHTING_VERT, _LIGHTING_FRAG


class LightingPass:
    """Owns the deferred lighting shader and fullscreen quad geometry."""

    def __init__(self) -> None:
        self._prog: int = 0
        self._vao: int = 0
        self._vbo: int = 0

    def init(self) -> None:
        self._prog = _compile_prog(_LIGHTING_VERT, _LIGHTING_FRAG)

        # 6 NDC vertices: xy position + uv, covering [-1,1]² → [0,1]²
        verts = np.array(
            [
                -1.0, -1.0,  0.0, 0.0,
                 1.0, -1.0,  1.0, 0.0,
                 1.0,  1.0,  1.0, 1.0,
                -1.0, -1.0,  0.0, 0.0,
                 1.0,  1.0,  1.0, 1.0,
                -1.0,  1.0,  0.0, 1.0,
            ],
            dtype=np.float32,
        )
        stride = 16  # 4 floats × 4 bytes

        self._vao = glGenVertexArrays(1)
        self._vbo = glGenBuffers(1)
        glBindVertexArray(self._vao)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(8))
        glEnableVertexAttribArray(1)
        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def render(
        self,
        albedo_tex: int,
        normal_tex: int,
        light_dir: NDArray,
    ) -> None:
        """Draw the deferred lighting fullscreen quad."""
        glDisable(GL_DEPTH_TEST)
        glUseProgram(self._prog)

        glUniform1i(glGetUniformLocation(self._prog, "gAlbedo"), 0)
        glUniform1i(glGetUniformLocation(self._prog, "gNormal"), 1)
        _u_vec3(self._prog, "uLightDir", light_dir)

        from OpenGL.GL import glActiveTexture
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, albedo_tex)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, normal_tex)

        glBindVertexArray(self._vao)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)
        glUseProgram(0)

        # Restore for subsequent forward passes
        glActiveTexture(GL_TEXTURE0)
        glEnable(GL_DEPTH_TEST)

    def cleanup(self) -> None:
        if self._prog:
            glDeleteProgram(self._prog)
            self._prog = 0
        if self._vao:
            glDeleteVertexArrays(1, [self._vao])
            self._vao = 0
        if self._vbo:
            glDeleteBuffers(1, [self._vbo])
            self._vbo = 0
