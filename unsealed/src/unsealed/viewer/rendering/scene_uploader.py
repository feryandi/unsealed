"""
scene_uploader.py — uploads ViewerScene meshes to GPU, populating the RenderRegistry.

Phase 3.2: Buffer creation uses moderngl.Context.buffer() instead of
glGenBuffers / glBufferData.  VAO setup still uses raw GL calls because the
primary VAO is bound to the first shader program encountered; additional
programs use the lazy _vao_cache in GpuBufferComp (Option A).
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np

import moderngl
from OpenGL.GL import (
  GL_ARRAY_BUFFER,
  GL_ELEMENT_ARRAY_BUFFER,
  glBindBuffer,
  glBindVertexArray,
  glGenVertexArrays,
)

from .components import BoundsComp, GpuBufferComp, MaterialComp, TransformComp
from .registry import RenderRegistry
from .shaders import _upload_rgba, get_mgl_context
from .types import (
  LAYOUT_INSTANCE,
  LAYOUT_PLAIN,
  LAYOUT_SKINNED,
  _GpuPrimitive,
  _Q3GpuStage,
)


def upload_meshes(scene: object, registry: RenderRegistry) -> None:
  """
  Upload all meshes in a 3-D scene to GPU, populating the registry.

  `scene` must have a `.meshes` attribute that is an iterable of ViewerMesh objects.
  """
  mgl: moderngl.Context = get_mgl_context()

  for eid, mesh in enumerate(scene.meshes):  # type: ignore[union-attr]
    # ── Vertex buffer ────────────────────────────────────────────────────────
    vdata = np.ascontiguousarray(mesh.vertex_data, dtype=np.float32)
    mgl_vbo = mgl.buffer(vdata.tobytes())
    vbo = mgl_vbo.glo  # raw GL name for backward-compat draw calls

    # ── VAO setup (primary — used by most draw calls) ─────────────────────
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)

    if mesh.is_skinned:
      LAYOUT_SKINNED.bind()
    else:
      LAYOUT_PLAIN.bind()

    # ── Instance buffer ───────────────────────────────────────────────────
    mgl_ibo_list: List[moderngl.Buffer] = []
    mgl_inst_vbo: Optional[moderngl.Buffer] = None
    instance_vbo = 0
    instance_count = 1
    if mesh.instance_matrices is not None and len(mesh.instance_matrices) > 0:
      instance_count = len(mesh.instance_matrices)
      data = np.ascontiguousarray(
        mesh.instance_matrices.transpose(0, 2, 1).reshape(-1), dtype=np.float32
      )
      mgl_inst_vbo = mgl.buffer(data.tobytes())
      instance_vbo = mgl_inst_vbo.glo
      glBindBuffer(GL_ARRAY_BUFFER, instance_vbo)
      LAYOUT_INSTANCE.bind()
      glBindBuffer(GL_ARRAY_BUFFER, 0)

    # ── Primitives (index buffers + textures) ─────────────────────────────
    mat_comp = MaterialComp()
    for prim in mesh.primitives:
      idx_data = np.ascontiguousarray(prim.indices)
      mgl_ebo = mgl.buffer(idx_data.tobytes())
      mgl_ibo_list.append(mgl_ebo)
      ebo = mgl_ebo.glo  # raw GL name

      # Bind EBO into the VAO so existing glDrawElements calls work
      glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)

      tex_id: Optional[int] = None
      if prim.image is not None:
        tex_id = _upload_rgba(prim.image, prim.image_w, prim.image_h)

      gpu_prim = _GpuPrimitive(
        ebo=ebo,
        index_count=len(prim.indices),
        texture_id=tex_id,
        base_color=prim.base_color,
        two_sided=prim.two_sided,
        is_billboard=prim.is_billboard,
      )

      if prim.q3_stages:
        for vs in prim.q3_stages:
          tid: Optional[int] = None
          if vs.image is not None:
            tid = _upload_rgba(vs.image, vs.image_w, vs.image_h)
          anim_ids = [_upload_rgba(f[0], f[1], f[2]) for f in vs.anim_frames]
          gpu_prim.q3_stages.append(
            _Q3GpuStage(
              tex_id=tid,
              blend_src=vs.blend_src,
              blend_dst=vs.blend_dst,
              tc_mods=vs.tc_mods,
              tc_gen_env=vs.tc_gen_env,
              anim_tex_ids=anim_ids,
              anim_fps=vs.anim_fps,
            )
          )

      mat_comp.primitives.append(gpu_prim)

    glBindVertexArray(0)

    # ── Bounds ────────────────────────────────────────────────────────────
    stride_f = LAYOUT_SKINNED.stride // 4 if mesh.is_skinned else LAYOUT_PLAIN.stride // 4
    positions = mesh.vertex_data.reshape(-1, stride_f)[:, :3]
    aabb_min = positions.min(axis=0).astype(np.float32)
    aabb_max = positions.max(axis=0).astype(np.float32)

    buf_comp = GpuBufferComp(
      vao=vao,
      vbo=vbo,
      mgl_vbo=mgl_vbo,
      mgl_ibo_list=mgl_ibo_list,
      instance_vbo=instance_vbo,
      mgl_inst_vbo=mgl_inst_vbo,
      instance_count=instance_count,
      inst_mats_cpu=mesh.instance_matrices,
    )
    xform_comp = TransformComp(
      model_matrix=mesh.model_matrix,
      is_skinned=mesh.is_skinned,
    )
    bnds_comp = BoundsComp(aabb_min=aabb_min, aabb_max=aabb_max)

    registry.add(eid, buf_comp, mat_comp, xform_comp, bnds_comp)
