"""Pipeline for model files (.ms1 mesh, .act actor) — produces a ModelScene."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from unsealed.assets import Material

from ...camera import compute_bounds
from ...scenes import (
  AnimatedEntity,
  ViewerAnimationGroup,
  ViewerBone,
  ViewerBoneAnimation,
  ViewerKeyframe,
  ViewerMesh,
  ViewerPrimitive,
  ViewerQ3Stage,
  ViewerSkeleton,
)
from ..image.pipeline import TexViewerPipeline
from .scene import ModelScene


class ModelViewerPipeline:
  """Decode a .ms1 or .act file into a ModelScene."""

  _PALETTE: List = [
    (0.72, 0.52, 0.52),
    (0.52, 0.72, 0.52),
    (0.52, 0.52, 0.72),
    (0.72, 0.72, 0.52),
    (0.52, 0.72, 0.72),
    (0.72, 0.52, 0.72),
  ]

  def run(self, path: Path, shader_cache: Optional[Dict] = None) -> ModelScene:
    shaders = shader_cache

    from unsealed.formats.base import collect_unknowns

    if path.suffix.lower() == ".act":
      from unsealed.formats.act.format import SealActorFormat

      fmt = SealActorFormat()
    else:
      from unsealed.formats.ms1.format import SealMeshFormat

      fmt = SealMeshFormat()
    model = fmt.decode(path)
    scene = ModelViewerPipeline._model_to_scene(model, path, shaders)
    scene.unknowns = collect_unknowns(fmt)
    return scene

  @classmethod
  def _model_to_scene(
    cls, model, path: Path, shaders: Optional[Dict] = None
  ) -> ModelScene:
    """Convert a decoded Model asset into a ModelScene."""
    scene = ModelScene()
    all_pos: List[np.ndarray] = []

    if model.geometry is None:
      return scene

    # Build material-name → Shader lookup from model.shaders (.sha file).
    # Keys are lowercased material names; values carry shader_name + sub_shaders.
    shader_by_mat: Dict[str, object] = {}
    if model.shaders:
      for s in model.shaders.shaders:
        shader_by_mat[s.material_name.lower()] = s

    # Pre-build world-matrix lookup so child meshes can compute their local transform.
    name_to_world: Dict[str, np.ndarray] = {}
    for m in model.geometry.meshes:
      if m.tm is not None:
        name_to_world[m.name.lower()] = np.array(m.tm, dtype=np.float32).T

    for mesh in model.geometry.meshes:
      if not mesh.vertices or not mesh.indices:
        continue

      is_skinned = any(j for j in mesh.joints)

      # ── vertex buffer ────────────────────────────────────────────────────
      vdata: List[float] = []
      for v_idx, v in enumerate(mesh.vertices):
        vdata.extend(v.position)
        vdata.extend(v.normal)
        vdata.extend(v.texcoord)
        all_pos.append(np.array(v.position, dtype=np.float32))

        if is_skinned:
          joints_raw = mesh.joints[v_idx] if v_idx < len(mesh.joints) else []
          weights_raw = mesh.weights[v_idx] if v_idx < len(mesh.weights) else []

          joints4 = (list(joints_raw) + [0, 0, 0, 0])[:4]
          weights4 = (list(weights_raw) + [0.0, 0.0, 0.0, 0.0])[:4]

          w_sum = sum(weights4)
          if w_sum > 1e-6:
            weights4 = [w / w_sum for w in weights4]
          else:
            weights4 = [1.0, 0.0, 0.0, 0.0]

          vdata.extend([float(j) for j in joints4])
          vdata.extend(weights4)

      vertex_data = np.array(vdata, dtype=np.float32)

      parent_name: Optional[str] = (
        mesh.parent if mesh.parent and mesh.parent.strip() else None
      )
      if mesh.tm is not None:
        world_mat = np.array(mesh.tm, dtype=np.float32).T
        model_matrix = world_mat
        if parent_name:
          pw = name_to_world.get(parent_name.lower())
          if pw is not None:
            local_model_matrix: Optional[np.ndarray] = (
              np.linalg.inv(pw) @ world_mat
            ).astype(np.float32)
          else:
            parent_name = None
            local_model_matrix = None
        else:
          local_model_matrix = None
      else:
        model_matrix = np.identity(4, dtype=np.float32)
        local_model_matrix = None
        parent_name = None

      viewer_mesh = ViewerMesh(
        name=mesh.name,
        vertex_data=vertex_data,
        model_matrix=model_matrix,
        is_skinned=is_skinned,
        parent_name=parent_name,
        local_model_matrix=local_model_matrix,
      )

      # ── resolve material ────────────────────────────────────────────────
      material: Optional[Material] = None
      if mesh.material_index is not None and mesh.material_index < len(
        model.geometry.materials
      ):
        material = model.geometry.materials[mesh.material_index]

      # ── primitives (one per sub-material group) ──────────────────────────
      for k, raw_indices in mesh.indices.items():
        sub_idx = int(k)
        scene.tri_count += len(raw_indices) // 3

        bitmap: Optional[str] = None
        if material is not None:
          if material.sub_materials and sub_idx < len(material.sub_materials):
            bitmap = material.sub_materials[sub_idx].bitmap
            base_color = (1.0, 1.0, 1.0, 1.0)
          else:
            bitmap = material.bitmap
            base_color = (1.0, 1.0, 1.0, 1.0)

        # Resolve Q3 shader name. Priority:
        #   1. .sha file mapping (material_name → shader_name)
        #   2. shader_name embedded in the material asset itself (ms1)
        # Both are tried against the Q3 shader cache; the embedded ms1 name is always
        # guaranteed to resolve, so it acts as the reliable fallback.
        q3_key = ""
        if material is not None:
          mat_shader = shader_by_mat.get(material.name.lower())

          # Build candidate shader names: sha mapping first, then ms1-embedded
          sha_name = ""
          ms1_name = ""
          if mat_shader is not None:
            if material.sub_materials and sub_idx < len(mat_shader.sub_shaders):
              sha_name = mat_shader.sub_shaders[sub_idx].shader_name
            else:
              sha_name = mat_shader.shader_name
          if material.sub_materials and sub_idx < len(material.sub_materials):
            ms1_name = material.sub_materials[sub_idx].shader_name or ""
          else:
            ms1_name = material.shader_name or ""

          # Prefer sha name if it resolves; otherwise fall back to ms1 embedded name
          sha_key = Path(sha_name).stem.lower() if sha_name else ""
          ms1_key = Path(ms1_name).stem.lower() if ms1_name else ""
          if shaders and sha_key and sha_key in shaders:
            q3_key = sha_key
          elif shaders and ms1_key and ms1_key in shaders:
            q3_key = ms1_key

        if shaders and q3_key and q3_key in shaders:
          q3_shader = shaders[q3_key]
          q3_stages = cls._resolve_q3_stages(path, q3_shader)
          viewer_mesh.primitives.append(
            ViewerPrimitive(
              indices=np.array(raw_indices, dtype=np.uint16),
              base_color=base_color,
              shader=q3_shader,
              q3_stages=q3_stages,
              two_sided=q3_shader.cull_mode is None,
              is_billboard=q3_shader.is_autosprite,
            )
          )
        else:
          image, w, h = cls._decode_texture(path, bitmap)
          viewer_mesh.primitives.append(
            ViewerPrimitive(
              indices=np.array(raw_indices, dtype=np.uint16),
              image=image,
              image_w=w,
              image_h=h,
              base_color=base_color,
            )
          )

      scene.meshes.append(viewer_mesh)

    if all_pos:
      pts = np.stack(all_pos)
      scene.bounds_center, scene.bounds_radius = compute_bounds(pts)

    # Wrap all the file's meshes in one AnimatedEntity. The entity owns the
    # skeleton + animation groups (formerly scene-level fields).
    skeleton = (
      cls._build_skeleton(model.skeleton) if model.skeleton is not None else None
    )
    anim_groups = (
      cls._build_animation_groups(model.animations) if model.animations else []
    )
    scene.entities.append(
      AnimatedEntity(
        name=path.stem,
        meshes=list(scene.meshes),
        skeleton=skeleton,
        animation_groups=anim_groups,
      )
    )

    return scene

  @staticmethod
  def _decode_texture(
    model_path: Path, bitmap: Optional[str]
  ) -> Tuple[Optional[bytes], int, int]:
    """Resolve and decode a texture referenced by a material bitmap field."""
    if not bitmap:
      return None, 0, 0

    stem = Path(bitmap).stem
    candidates = [model_path.with_name(bitmap)]
    for ext in (".tex", ".te1", ".png", ".jpg", ".bmp", ".dds"):
      candidates.append(model_path.with_name(stem + ext))

    for tex_path in candidates:
      if not tex_path.exists():
        continue
      result = TexViewerPipeline.decode(tex_path)
      if result[0] is not None:
        return result

    return None, 0, 0

  @staticmethod
  def _resolve_q3_stages(model_path: Path, shader) -> List[ViewerQ3Stage]:
    """Resolve each stage of a Q3Shader into a ViewerQ3Stage with pixel data."""
    result: List[ViewerQ3Stage] = []
    for stage in shader.stages:
      image: Optional[bytes] = None
      w = h = 0
      if stage.map_texture is not None:
        image, w, h = ModelViewerPipeline._decode_texture(model_path, stage.map_texture)

      anim_frames: list = []
      for tex_name in stage.anim_textures:
        frame_img, fw, fh = ModelViewerPipeline._decode_texture(model_path, tex_name)
        if frame_img is not None:
          anim_frames.append((frame_img, fw, fh))

      result.append(
        ViewerQ3Stage(
          image=image,
          image_w=w,
          image_h=h,
          anim_frames=anim_frames,
          anim_fps=stage.anim_fps,
          blend_src=stage.blend_src,
          blend_dst=stage.blend_dst,
          tc_mods=stage.tc_mods,
          tc_gen_env=stage.tc_gen_env,
        )
      )
    return result

  @staticmethod
  def _build_skeleton(skeleton) -> ViewerSkeleton:
    """Convert a Skeleton asset into a ViewerSkeleton."""
    viewer_skel = ViewerSkeleton()
    for idx, bone in enumerate(skeleton.bones.values()):
      inverse_bind = np.array(bone.tm_inverse, dtype=np.float32).T
      viewer_bone = ViewerBone(
        name=bone.name,
        parent=bone.parent,
        inverse_bind=inverse_bind,
        bind_rot=np.array(bone.rot, dtype=np.float32),
        bind_sca=np.array(bone.sca, dtype=np.float32),
      )
      viewer_skel.bones.append(viewer_bone)
      viewer_skel.name_to_idx[bone.name] = idx
      viewer_skel.name_to_idx[bone.name.lower()] = idx

    return viewer_skel

  @staticmethod
  def _build_animation_groups(animations: Dict) -> List[ViewerAnimationGroup]:
    """Convert model.animations (Dict[str, List[Animation]]) into ViewerAnimationGroups."""
    groups: List[ViewerAnimationGroup] = []
    for action_name, anim_list in animations.items():
      group = ViewerAnimationGroup(
        name=action_name if action_name is not None else "unnamed"
      )

      for anim in anim_list:
        tps = anim.ticks_per_frame * anim.fps
        if tps < 1e-6:
          continue

        ba = ViewerBoneAnimation(bone_name=anim.mesh_name)

        for kf in anim.transforms:
          ba.translations.append(
            ViewerKeyframe(
              time=kf.time / tps, value=np.array(kf.value, dtype=np.float32)
            )
          )
        for kf in anim.rotations:
          ba.rotations.append(
            ViewerKeyframe(
              time=kf.time / tps, value=np.array(kf.value, dtype=np.float32)
            )
          )
        for kf in anim.scales:
          ba.scales.append(
            ViewerKeyframe(
              time=kf.time / tps, value=np.array(kf.value, dtype=np.float32)
            )
          )

        ba.translations.sort(key=lambda k: k.time)
        ba.rotations.sort(key=lambda k: k.time)
        ba.scales.sort(key=lambda k: k.time)

        group.bone_animations.append(ba)

      all_times: List[float] = [
        kf.time
        for ba in group.bone_animations
        for track in (ba.translations, ba.rotations, ba.scales)
        for kf in track
      ]
      group.duration = max(all_times) if all_times else 0.0
      groups.append(group)

    return groups
