"""
command_builder.py — builds DrawCommand lists from the RenderRegistry and RenderContext.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from .registry import RenderRegistry
from .types import (
  DrawCommand,
  RenderContext,
  ShaderVariant,
  _IDENTITY_BONE_FLAT,
  _MAX_BONES,
)


def pack_bone_matrices(bones: Optional[List[NDArray]]) -> Tuple[int, NDArray]:
  """Pack a list of 4×4 bone matrices into a flat float32 array for GL upload."""
  if bones:
    bc = min(len(bones), _MAX_BONES)
    return bc, np.array([m.flatten() for m in bones[:bc]], dtype=np.float32).flatten()
  return _MAX_BONES, _IDENTITY_BONE_FLAT


def build_commands(
  registry: RenderRegistry,
  ctx: RenderContext,
) -> Tuple[List[DrawCommand], List[DrawCommand], List[DrawCommand]]:
  """
  Produce one DrawCommand per (entity, instance, primitive) and classify
  into opaque (G-Buffer), transparent (forward alpha blend), or q3 lists.
  """
  opaque: List[DrawCommand] = []
  transparent: List[DrawCommand] = []
  q3: List[DrawCommand] = []

  for eid in registry.entity_ids():
    buf = registry.buffers[eid]
    xform = registry.transforms[eid]
    mat = registry.materials[eid]

    draw_params: List[Tuple[NDArray, Optional[NDArray], int, ShaderVariant]] = []

    if xform.is_skinned and buf.inst_mats_cpu is not None:
      map_bones = ctx.map_bone_matrices.get(eid) if ctx.map_bone_matrices else None
      bc, bf = pack_bone_matrices(map_bones)
      for k in range(buf.instance_count):
        model = buf.inst_mats_cpu[k] @ xform.model_matrix
        draw_params.append((model, bf, bc, ShaderVariant.SKINNED))

    elif (
      not xform.is_skinned and ctx.map_node_matrices and eid in ctx.map_node_matrices
    ):
      anim_model = ctx.map_node_matrices[eid]
      if buf.inst_mats_cpu is not None:
        for k in range(buf.instance_count):
          model = buf.inst_mats_cpu[k] @ anim_model
          draw_params.append((model, None, 0, ShaderVariant.PLAIN))
      else:
        draw_params.append((anim_model, None, 0, ShaderVariant.PLAIN))

    else:
      if buf.instance_count > 1:
        draw_params.append((xform.model_matrix, None, 0, ShaderVariant.INSTANCED))
      elif xform.is_skinned:
        bc, bf = pack_bone_matrices(ctx.bone_matrices)
        model = (
          buf.inst_mats_cpu[0] @ xform.model_matrix
          if buf.inst_mats_cpu is not None
          else xform.model_matrix
        )
        draw_params.append((model, bf, bc, ShaderVariant.SKINNED))
      else:
        model = (
          buf.inst_mats_cpu[0] @ xform.model_matrix
          if buf.inst_mats_cpu is not None
          else xform.model_matrix
        )
        draw_params.append((model, None, 0, ShaderVariant.PLAIN))

    for prim_idx, prim in enumerate(mat.primitives):
      is_q3 = bool(prim.q3_stages)
      is_transparent = not is_q3 and prim.base_color[3] < 1.0
      for model, bf, bc, variant in draw_params:
        if is_q3 and variant == ShaderVariant.INSTANCED:
          if buf.inst_mats_cpu is not None:
            for k in range(buf.instance_count):
              inst_model = buf.inst_mats_cpu[k] @ xform.model_matrix
              q3.append(
                DrawCommand(
                  entity_id=eid,
                  variant=ShaderVariant.PLAIN,
                  model_matrix=inst_model,
                  primitive_idx=prim_idx,
                  instance_count=1,
                  bone_matrices_flat=None,
                  bone_count=0,
                )
              )
        else:
          ic = buf.instance_count if variant == ShaderVariant.INSTANCED else 1
          cmd = DrawCommand(
            entity_id=eid,
            variant=variant,
            model_matrix=model,
            primitive_idx=prim_idx,
            instance_count=ic,
            bone_matrices_flat=bf,
            bone_count=bc,
          )
          if is_q3:
            q3.append(cmd)
          elif is_transparent:
            transparent.append(cmd)
          else:
            opaque.append(cmd)

  return opaque, transparent, q3
