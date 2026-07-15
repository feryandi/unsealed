from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING

import numpy as np
from OpenGL.GL import (
  GL_ARRAY_BUFFER,
  GL_BLEND,
  GL_CULL_FACE,
  GL_DEPTH_TEST,
  GL_DYNAMIC_DRAW,
  GL_FALSE,
  GL_FLOAT,
  GL_ONE_MINUS_SRC_ALPHA,
  GL_SRC_ALPHA,
  GL_TRIANGLES,
  GL_TRUE,
  glBindBuffer,
  glBindVertexArray,
  glBlendFunc,
  glBufferData,
  glDeleteBuffers,
  glDeleteProgram,
  glDeleteVertexArrays,
  glDepthMask,
  glDisable,
  glDrawArrays,
  glEnable,
  glEnableVertexAttribArray,
  glGenBuffers,
  glGenVertexArrays,
  glUseProgram,
  glVertexAttribPointer,
)

from ...rendering.shaders import _compile_prog, _u_mat4, _u_vec3
from ...scenes.scene import ViewerScene
from ..base import RenderPhase

if TYPE_CHECKING:
  from numpy.typing import NDArray
  from ...rendering import RenderContext


_GRID_VERT = """
#version 330 core

layout(location = 0) in vec2 aPos;

out vec2 vNDC;

void main()
{
    vNDC = aPos;
    gl_Position = vec4(aPos, 1.0, 1.0);
}
"""


# Anti-aliased infinite grid on the y=0 plane.
#
#   - Reconstructs a world-space ray from each NDC pixel using the inverse
#     view-projection matrix, intersects it with y=0.
#   - Draws thin minor lines every 1 unit and bold major lines every 10 units
#     with screen-space-derivative anti-aliasing (Blender / Unity style).
#   - Tints the X and Z axes red / blue.
#   - Fades the grid out with distance from the camera.
#   - Writes gl_FragDepth so the grid integrates correctly with the
#     depth buffer (occluded by meshes in front, occludes nothing weirdly).
_GRID_FRAG = """
#version 330 core

in vec2 vNDC;
out vec4 FragColor;

uniform mat4 uViewProj;
uniform mat4 uInvViewProj;
uniform vec3 uCameraPos;

const float MINOR_STEP = 1.0;
const float MAJOR_STEP = 10.0;
const float FADE_START = 30.0;
const float FADE_END   = 200.0;

// One axis-aligned line set at `step` spacing.  Returns line coverage in [0,1].
float gridLine(vec2 coord, float step)
{
    vec2 g = abs(fract(coord / step - 0.5) - 0.5) / fwidth(coord / step);
    float line = min(g.x, g.y);
    return 1.0 - min(line, 1.0);
}

void main()
{
    // Reconstruct a world-space ray for this pixel.
    vec4 nearH = uInvViewProj * vec4(vNDC, -1.0, 1.0);
    vec4 farH  = uInvViewProj * vec4(vNDC,  1.0, 1.0);
    vec3 nearW = nearH.xyz / nearH.w;
    vec3 farW  = farH.xyz  / farH.w;
    vec3 rayDir = normalize(farW - nearW);

    // Intersect ray with the y=0 plane.
    if (abs(rayDir.y) < 1e-5) discard;
    float t = -uCameraPos.y / rayDir.y;
    if (t <= 0.0) discard;

    vec3 p = uCameraPos + rayDir * t;

    // Anti-aliased lines.
    float minor = gridLine(p.xz, MINOR_STEP);
    float major = gridLine(p.xz, MAJOR_STEP);

    // Highlight world axes.
    vec2 axisDist = abs(p.xz) / fwidth(p.xz);
    float axisX = 1.0 - clamp(axisDist.y - 0.5, 0.0, 1.0);  // line along X
    float axisZ = 1.0 - clamp(axisDist.x - 0.5, 0.0, 1.0);  // line along Z

    // Compose: minor (faint), major (brighter), axes (colored).
    vec3 minorCol = vec3(0.35);
    vec3 majorCol = vec3(0.55);
    vec3 col = minorCol * minor;
    col = mix(col, majorCol, major);
    col = mix(col, vec3(0.85, 0.25, 0.30), axisZ);  // Z axis = X coord = 0 → red
    col = mix(col, vec3(0.25, 0.45, 0.90), axisX);  // X axis = Z coord = 0 → blue

    float alpha = max(max(minor, major), max(axisX, axisZ));
    if (alpha <= 0.0) discard;

    // Distance fade.
    float dist = length(p - uCameraPos);
    float fade = 1.0 - clamp((dist - FADE_START) / (FADE_END - FADE_START), 0.0, 1.0);
    alpha *= fade;
    if (alpha <= 0.001) discard;

    // Write correct depth so opaque geometry occludes the grid (and vice versa).
    vec4 clip = uViewProj * vec4(p, 1.0);
    gl_FragDepth = (clip.z / clip.w) * 0.5 + 0.5;

    FragColor = vec4(col, alpha);
}
"""


class InfiniteGridExtension:
  """Blender-style infinite grid on the y=0 plane.

  Drawn at FORWARD_OPAQUE so it sits after sky / lighting but blends against
  scene geometry via per-pixel depth writes (occluded by meshes in front,
  occluding nothing it shouldn't).
  """

  phase = RenderPhase.FORWARD_OPAQUE

  def __init__(self) -> None:
    self._prog: int = 0
    self._vao: int = 0
    self._vbo: int = 0

  def init(self) -> None:
    self._prog = _compile_prog(_GRID_VERT, _GRID_FRAG)

    self._vao = glGenVertexArrays(1)
    self._vbo = glGenBuffers(1)

    # Fullscreen triangle pair in NDC.
    verts = np.array(
      [-1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, 1.0],
      dtype=np.float32,
    )

    glBindVertexArray(self._vao)
    glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_DYNAMIC_DRAW)
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 8, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)

  def upload(self, scene: "ViewerScene") -> None:
    pass

  def render(
    self,
    ctx: "RenderContext",
    view: "NDArray",
    proj: "NDArray",
  ) -> None:
    view_proj = (proj @ view).astype(np.float32)
    inv_view_proj = np.linalg.inv(view_proj).astype(np.float32)
    cam_pos = ctx.camera.position().astype(np.float32)

    glEnable(GL_DEPTH_TEST)
    glDepthMask(GL_TRUE)
    glDisable(GL_CULL_FACE)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glUseProgram(self._prog)
    _u_mat4(self._prog, "uViewProj", view_proj)
    _u_mat4(self._prog, "uInvViewProj", inv_view_proj)
    _u_vec3(self._prog, "uCameraPos", cam_pos)

    glBindVertexArray(self._vao)
    glDrawArrays(GL_TRIANGLES, 0, 6)
    glBindVertexArray(0)
    glUseProgram(0)

  def free_scene(self) -> None:
    pass

  def dispose(self) -> None:
    if self._prog:
      glDeleteProgram(self._prog)
      self._prog = 0
    if self._vao:
      glDeleteVertexArrays(1, [self._vao])
      self._vao = 0
    if self._vbo:
      glDeleteBuffers(1, [self._vbo])
      self._vbo = 0
