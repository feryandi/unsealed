"""
GLSL shader loader and compilation helpers.

Shader source files live in the glsl/ subdirectory alongside this module.
The module-level constants (_MESH_VERT, etc.) are loaded once at import time.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from OpenGL.GL import *  # noqa: F401, F403


_GLSL_DIR = Path(__file__).parent / "glsl"


def _load(name: str) -> str:
  return (_GLSL_DIR / name).read_text(encoding="utf-8")


# ─── Shader sources (loaded from glsl/) ──────────────────────────────────────

_MESH_VERT     = _load("mesh.vert.glsl")
_SKIN_VERT     = _load("skin.vert.glsl")
_MESH_FRAG     = _load("mesh.frag.glsl")
_INST_VERT     = _load("inst.vert.glsl")
_WIRE_VERT     = _load("wire.vert.glsl")
_WIRE_FRAG     = _load("wire.frag.glsl")
_IMG_VERT      = _load("img.vert.glsl")
_IMG_FRAG      = _load("img.frag.glsl")
_TERRAIN_VERT  = _load("terrain.vert.glsl")
_TERRAIN_FRAG  = _load("terrain.frag.glsl")
_SEL_VERT      = _load("sel.vert.glsl")
_SEL_INST_VERT = _load("sel_inst.vert.glsl")
_SEL_FRAG      = _load("sel.frag.glsl")
_HUD_VERT      = _load("hud.vert.glsl")
_HUD_FRAG      = _load("hud.frag.glsl")
_GBUFFER_FRAG  = _load("gbuffer.frag.glsl")
_LIGHTING_VERT = _load("lighting.vert.glsl")
_LIGHTING_FRAG = _load("lighting.frag.glsl")
_Q3STAGE_VERT  = _load("q3stage.vert.glsl")
_Q3STAGE_FRAG  = _load("q3stage.frag.glsl")
_SKY_VERT      = _load("sky.vert.glsl")
_SKY_FRAG      = _load("sky.frag.glsl")


# ─── GL compilation helpers ───────────────────────────────────────────────────


def _compile_shader(src: str, kind: int) -> int:
  shader = glCreateShader(kind)
  glShaderSource(shader, src)
  glCompileShader(shader)
  if not glGetShaderiv(shader, GL_COMPILE_STATUS):
    log = glGetShaderInfoLog(shader)
    raise RuntimeError(
      f"Shader compile error:\n{log.decode() if isinstance(log, bytes) else log}"
    )
  return shader


def _compile_prog(vert: str, frag: str) -> int:
  vs = _compile_shader(vert, GL_VERTEX_SHADER)
  fs = _compile_shader(frag, GL_FRAGMENT_SHADER)
  prog = glCreateProgram()
  glAttachShader(prog, vs)
  glAttachShader(prog, fs)
  glLinkProgram(prog)
  glDeleteShader(vs)
  glDeleteShader(fs)
  if not glGetProgramiv(prog, GL_LINK_STATUS):
    log = glGetProgramInfoLog(prog)
    raise RuntimeError(
      f"Program link error:\n{log.decode() if isinstance(log, bytes) else log}"
    )
  return prog


def _u_mat4(prog: int, name: str, mat: NDArray) -> None:
  loc = glGetUniformLocation(prog, name)
  if loc != -1:
    glUniformMatrix4fv(loc, 1, GL_TRUE, mat.astype(np.float32).flatten())


def _u_vec3(prog: int, name: str, vec: NDArray) -> None:
  loc = glGetUniformLocation(prog, name)
  if loc != -1:
    glUniform3f(loc, float(vec[0]), float(vec[1]), float(vec[2]))


def _upload_rgba(data: bytes, w: int, h: int) -> int:
  """
  Upload raw top-to-bottom RGBA bytes to a new GL texture.
  Flips rows via numpy so GL v=0 maps to the bottom of the image.
  The mesh shader then flips V (1-v) so game UVs (v=0 at top) render correctly.
  """
  pixels = np.frombuffer(data, dtype=np.uint8).reshape(h, w, 4)
  pixels = np.ascontiguousarray(np.flip(pixels, axis=0))

  tex_id = glGenTextures(1)
  glBindTexture(GL_TEXTURE_2D, tex_id)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
  # Anisotropic filtering — reduces blurriness of flat planes viewed at oblique angles.
  try:
    from OpenGL.GL.EXT.texture_filter_anisotropic import (
      GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT,
      GL_TEXTURE_MAX_ANISOTROPY_EXT,
    )
    max_aniso = float(glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT))
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, min(max_aniso, 16.0))
  except Exception:
    pass
  glTexImage2D(
    GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels.tobytes()
  )
  glGenerateMipmap(GL_TEXTURE_2D)
  glBindTexture(GL_TEXTURE_2D, 0)
  return tex_id
