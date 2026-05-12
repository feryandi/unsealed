"""
Terrain renderer.

Manages the GPU resources and draw call for the heightmap terrain mesh,
including multi-texture blending and lightmap support.
"""

from __future__ import annotations

import ctypes
from typing import List, Optional

import numpy as np
from numpy.typing import NDArray
from OpenGL.GL import (
  glGenVertexArrays,
  glGenBuffers,
  glBindVertexArray,
  glBindBuffer,
  glBufferData,
  glVertexAttribPointer,
  glEnableVertexAttribArray,
  glUseProgram,
  glActiveTexture,
  glBindTexture,
  glGetUniformLocation,
  glUniform1iv,
  glUniform1i,
  glDrawElements,
  glDeleteBuffers,
  glDeleteVertexArrays,
  glDeleteTextures,
  glDeleteProgram,
  GL_ARRAY_BUFFER,
  GL_ELEMENT_ARRAY_BUFFER,
  GL_FLOAT,
  GL_FALSE,
  GL_STATIC_DRAW,
  GL_TEXTURE0,
  GL_TEXTURE_2D,
  GL_TEXTURE12,
  GL_TRIANGLES,
  GL_UNSIGNED_INT,
)

from .shaders import _compile_prog, _u_mat4, _upload_rgba, _TERRAIN_VERT, _TERRAIN_FRAG
from ..modes.map.scene import MapScene


class TerrainRenderer:
  """Owns all GL resources for the terrain: shader, VAO/VBO/EBO, textures."""

  def __init__(self) -> None:
    self._prog: int = 0
    self._vao: int = 0
    self._vbo: int = 0
    self._ebo: int = 0
    self._idx_count: int = 0
    self._tex_ids: List[Optional[int]] = []
    self._lightmap_tex_id: Optional[int] = None
    self._fallback_tex: int = 0  # 1×1 white RGBA for missing texture slots
    self._layer_a: List[int] = []
    self._layer_b: List[int] = []
    # Pre-built arrays for uniform upload; populated in upload(), constant per scene.
    self._layer_a_arr: NDArray = np.zeros(64, dtype=np.int32)
    self._layer_b_arr: NDArray = np.zeros(64, dtype=np.int32)
    self._sampler_arr: NDArray = np.arange(12, dtype=np.int32)

  def init(self) -> None:
    """Compile the terrain shader and create the fallback texture. Call once after GL context."""
    self._prog = _compile_prog(_TERRAIN_VERT, _TERRAIN_FRAG)
    self._fallback_tex = _upload_rgba(bytes([255, 255, 255, 255]), 1, 1)

  def upload(self, scene: MapScene) -> None:
    """Upload a new terrain scene to the GPU (frees any previously loaded terrain)."""
    self.free_scene()

    if scene.terrain_vertex_data is None or scene.terrain_index_data is None:
      return

    self._vao = glGenVertexArrays(1)
    self._vbo = glGenBuffers(1)
    self._ebo = glGenBuffers(1)

    glBindVertexArray(self._vao)

    glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
    glBufferData(
      GL_ARRAY_BUFFER,
      scene.terrain_vertex_data.nbytes,
      scene.terrain_vertex_data,
      GL_STATIC_DRAW,
    )
    # pos(3) at offset 0, uv_a(2) at offset 12, uv_b(2) at offset 20 — stride 28 bytes
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 28, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 28, ctypes.c_void_p(12))
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 28, ctypes.c_void_p(20))
    glEnableVertexAttribArray(2)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ebo)
    glBufferData(
      GL_ELEMENT_ARRAY_BUFFER,
      scene.terrain_index_data.nbytes,
      scene.terrain_index_data,
      GL_STATIC_DRAW,
    )
    glBindVertexArray(0)

    self._idx_count = len(scene.terrain_index_data)
    self._layer_a = list(scene.terrain_layer_a)
    self._layer_b = list(scene.terrain_layer_b)
    # Pre-build the padded int arrays for uniform upload (static per scene load)
    self._layer_a_arr = np.array((self._layer_a + [0] * 64)[:64], dtype=np.int32)
    self._layer_b_arr = np.array((self._layer_b + [0] * 64)[:64], dtype=np.int32)
    self._sampler_arr = np.arange(12, dtype=np.int32)

    # Upload up to 12 terrain textures
    for rgba, (w, h) in zip(scene.terrain_textures, scene.terrain_texture_sizes):
      if rgba is not None and w > 0 and h > 0:
        self._tex_ids.append(_upload_rgba(rgba, w, h))
      else:
        self._tex_ids.append(None)

    # Upload lightmap
    if scene.lightmap is not None and scene.lightmap_w > 0:
      self._lightmap_tex_id = _upload_rgba(
        scene.lightmap, scene.lightmap_w, scene.lightmap_h
      )

  def render(self, view: NDArray, proj: NDArray) -> None:
    """Draw the terrain mesh with multi-texture blending."""
    if not self._vao or not self._idx_count:
      return

    glUseProgram(self._prog)
    _u_mat4(self._prog, "uView", view)
    _u_mat4(self._prog, "uProjection", proj)

    # Bind terrain textures to GL_TEXTURE0..11 (fallback white for missing slots)
    for i in range(12):
      glActiveTexture(int(GL_TEXTURE0) + i)
      tex = (
        self._tex_ids[i]
        if i < len(self._tex_ids) and self._tex_ids[i] is not None
        else self._fallback_tex
      )
      glBindTexture(GL_TEXTURE_2D, tex)

    # Set sampler array to units 0..11
    loc_tex = glGetUniformLocation(self._prog, "uTextures[0]")
    if loc_tex != -1:
      glUniform1iv(loc_tex, 12, self._sampler_arr)

    # Lightmap on unit 12
    has_lm = self._lightmap_tex_id is not None
    glUniform1i(glGetUniformLocation(self._prog, "uHasLightmap"), int(has_lm))
    if has_lm:
      glActiveTexture(GL_TEXTURE12)
      glBindTexture(GL_TEXTURE_2D, self._lightmap_tex_id)
      glUniform1i(glGetUniformLocation(self._prog, "uLightmap"), 12)

    # Layer index arrays (64 ints each) — pre-built in upload()
    loc_a = glGetUniformLocation(self._prog, "uLayerA[0]")
    loc_b = glGetUniformLocation(self._prog, "uLayerB[0]")
    if loc_a != -1:
      glUniform1iv(loc_a, 64, self._layer_a_arr)
    if loc_b != -1:
      glUniform1iv(loc_b, 64, self._layer_b_arr)

    glBindVertexArray(self._vao)
    glDrawElements(GL_TRIANGLES, self._idx_count, GL_UNSIGNED_INT, None)
    glBindVertexArray(0)
    glUseProgram(0)

    # Reset active texture unit to 0
    glActiveTexture(GL_TEXTURE0)

  def free_scene(self) -> None:
    """Free per-scene GL objects (VAO, VBO, EBO, textures). Keeps fallback_tex and prog."""
    if self._ebo:
      glDeleteBuffers(1, [self._ebo])
      self._ebo = 0
    if self._vbo:
      glDeleteBuffers(1, [self._vbo])
      self._vbo = 0
    if self._vao:
      glDeleteVertexArrays(1, [self._vao])
      self._vao = 0
    for tex in self._tex_ids:
      if tex is not None:
        glDeleteTextures(1, [tex])
    self._tex_ids = []
    if self._lightmap_tex_id is not None:
      glDeleteTextures(1, [self._lightmap_tex_id])
      self._lightmap_tex_id = None
    self._idx_count = 0
    self._layer_a = []
    self._layer_b = []
    self._layer_a_arr = np.zeros(64, dtype=np.int32)
    self._layer_b_arr = np.zeros(64, dtype=np.int32)

  def cleanup(self) -> None:
    """Free all GL resources including the shader program and fallback texture."""
    self.free_scene()
    if self._prog:
      glDeleteProgram(self._prog)
      self._prog = 0
    if self._fallback_tex:
      glDeleteTextures(1, [self._fallback_tex])
      self._fallback_tex = 0
