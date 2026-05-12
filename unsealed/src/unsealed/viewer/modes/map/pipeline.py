"""Pipeline for .map files — terrain heightmap + surface textures + object meshes."""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from ...scenes import ViewerMesh
from ..image.pipeline import TexViewerPipeline
from ..model.pipeline import ModelViewerPipeline
from .scene import MapScene


class MapViewerPipeline:
  """Decode a .map file into a MapScene."""

  _MAX_OBJECT_TYPES: int = 200

  def run(self, path: Path, shader_cache: Optional[Dict] = None) -> MapScene:
    from unsealed.formats.map.format import SealMapFormat

    terrain = SealMapFormat().decode(path)
    return MapViewerPipeline._terrain_to_scene(terrain, path, shader_cache)

  @staticmethod
  def _terrain_to_scene(terrain, path: Path, shader_cache: Optional[Dict] = None) -> MapScene:
    """Convert a decoded Terrain asset into a MapScene with terrain + objects."""
    scene = MapScene()

    W = terrain.width  # 512
    H = terrain.height  # 512

    # ── Terrain vertex buffer  [pos(3) + uv_a(2) + uv_b(2)] × W*H, stride=28 ─
    x_coords = np.arange(W, dtype=np.float32)
    z_coords = np.arange(H, dtype=np.float32)
    xx, zz = np.meshgrid(x_coords, z_coords)

    heights = (
      np.array(terrain.heightmap, dtype=np.float32).reshape(H, W)
      if terrain.heightmap
      else np.zeros((H, W), dtype=np.float32)
    )

    u_orig = xx.flatten() / (W - 1)
    v_orig = zz.flatten() / (H - 1)

    verts = np.zeros((H * W, 7), dtype=np.float32)
    verts[:, 0] = xx.flatten()
    verts[:, 1] = heights.flatten()
    verts[:, 2] = zz.flatten()
    verts[:, 3] = u_orig  # uv_a.u  (layer_a, rotated)
    verts[:, 4] = 1.0 - v_orig  # uv_a.v
    verts[:, 5] = u_orig  # uv_b.u  (layer_b, original)
    verts[:, 6] = v_orig  # uv_b.v
    scene.terrain_vertex_data = np.ascontiguousarray(verts.flatten())
    scene.terrain_heights = heights

    # ── Terrain index buffer ────────────────────────────────────────────────
    xi = np.arange(W - 1, dtype=np.uint32)
    zi = np.arange(H - 1, dtype=np.uint32)
    xg, zg = np.meshgrid(xi, zi)
    tl = (zg * W + xg).flatten()
    tr = tl + 1
    bl = tl + W
    br = bl + 1
    indices = np.empty(len(tl) * 6, dtype=np.uint32)
    indices[0::6] = tl
    indices[1::6] = bl
    indices[2::6] = tr
    indices[3::6] = tr
    indices[4::6] = bl
    indices[5::6] = br
    scene.terrain_index_data = np.ascontiguousarray(indices)

    # ── Layer arrays ──────────────────────────────────────────────────────
    scene.terrain_layer_a = list(terrain.terrain_layer_a)
    scene.terrain_layer_b = list(terrain.terrain_layer_b)

    # ── Terrain textures (up to 12) ──────────────────────────────────────
    embedded = MapViewerPipeline._load_mdt_blobs(path)
    for tex_name in terrain.textures[:12]:
      rgba, w, h = MapViewerPipeline._resolve_map_texture(path, tex_name, embedded)
      scene.terrain_textures.append(rgba)
      scene.terrain_texture_sizes.append((w, h))
    while len(scene.terrain_textures) < 12:
      scene.terrain_textures.append(None)
      scene.terrain_texture_sizes.append((0, 0))

    # ── Lightmap ────────────────────────────────────────────────────────
    if terrain.lightmap:
      rgba, w, h = MapViewerPipeline._resolve_map_texture(
        path, terrain.lightmap, embedded
      )
      scene.lightmap = rgba
      scene.lightmap_w = w
      scene.lightmap_h = h

    # ── Object meshes (instanced) ────────────────────────────────────────
    instances_by_idx: Dict[int, list] = defaultdict(list)
    for obj in terrain.objects:
      instances_by_idx[obj["idx"]].append(obj)

    total_types = 0

    for idx, obj_instances in instances_by_idx.items():
      if idx >= len(terrain.object_files):
        continue
      if total_types >= MapViewerPipeline._MAX_OBJECT_TYPES:
        break

      filename = terrain.object_files[idx]
      obj_path = MapViewerPipeline._find_object_file(path, filename)
      if obj_path is None:
        continue

      try:
        obj_scene = ModelViewerPipeline().run(obj_path, shader_cache)
      except Exception as e:
        print(f"[viewer] map object '{filename}': {e}")
        continue

      inst_mats: List[np.ndarray] = []
      for instance in obj_instances:
        pos = instance["pos"]
        rot = instance["rot"]
        scale = float(rot[-1]) if len(rot) > 2 else 1.0
        angle_y = float(rot[0]) * math.pi if len(rot) > 0 else 0.0
        angle_x = float(rot[1]) * math.pi if len(rot) > 1 else 0.0
        inst_mats.append(
          MapViewerPipeline._make_instance_matrix(pos, angle_y, angle_x, scale)
        )

      if not inst_mats:
        continue

      inst_arr = np.stack(inst_mats, axis=0).astype(np.float32)

      for mesh in obj_scene.meshes:
        scene.meshes.append(
          ViewerMesh(
            name=mesh.name,
            vertex_data=mesh.vertex_data,
            model_matrix=mesh.model_matrix,
            is_skinned=mesh.is_skinned,
            primitives=mesh.primitives,
            instance_matrices=inst_arr,
            skeleton=obj_scene.skeleton,
            animation_groups=obj_scene.animation_groups,
            source_file=filename,
            parent_name=mesh.parent_name,
            local_model_matrix=mesh.local_model_matrix,
          )
        )

      total_types += 1

    # ── Sky dome (sky.ms1 alongside the .map file) ───────────────────────────
    sky_path = MapViewerPipeline._find_object_file(path, "sky.ms1")
    if sky_path is not None:
      try:
        sky_scene = ModelViewerPipeline().run(sky_path, shader_cache)
        scene.sky_meshes = sky_scene.meshes
      except Exception as e:
        print(f"[viewer] sky.ms1: {e}")

    return scene

  @staticmethod
  def _load_mdt_blobs(map_path: Path) -> Dict[str, bytes]:
    """Try to read embedded texture blobs from the .mdt file alongside the .map."""
    mdt_path = map_path.with_suffix(".mdt")
    if not mdt_path.exists():
      return {}
    try:
      from unsealed.formats.mdt.decoder import SealMdtDecoder

      directory = SealMdtDecoder(mdt_path).decode()
      return {
        blob.filename.lower(): blob.value for blob in directory.list if blob.value
      }
    except Exception:
      return {}

  @staticmethod
  def _resolve_map_texture(
    map_path: Path,
    tex_name: str,
    embedded: Dict[str, bytes],
  ) -> Tuple[Optional[bytes], int, int]:
    """Resolve a terrain texture by name: try embedded blobs first, then disk files."""
    if not tex_name:
      return None, 0, 0

    stem = Path(tex_name).stem.lower()

    if stem in embedded:
      result = TexViewerPipeline._pil_bytes_from_raw(embedded[stem])
      if result[0] is not None:
        return result

    for ext in (".tex", ".te1", ".dds", ".png", ".jpg", ".bmp"):
      candidate = map_path.with_name(stem + ext)
      if not candidate.exists():
        continue
      result = TexViewerPipeline.decode(candidate)
      if result[0] is not None:
        return result

    return None, 0, 0

  @staticmethod
  def _find_object_file(map_path: Path, filename: str) -> Optional[Path]:
    """Locate an .ms1 object file relative to the .map file's directory."""
    stem = Path(filename).stem
    for name in (filename, stem + ".ms1"):
      p = map_path.with_name(name)
      if p.exists():
        return p
    return None

  @staticmethod
  def _make_instance_matrix(
    pos: list, angle_y: float, angle_x: float, scale: float
  ) -> np.ndarray:
    """Build a TRS model matrix for a map object instance."""
    T = np.identity(4, dtype=np.float32)
    T[0, 3] = float(pos[0])
    T[1, 3] = float(pos[1])
    T[2, 3] = float(pos[2])

    cy, sy = math.cos(angle_y), math.sin(angle_y)
    Ry = np.array(
      [
        [cy, 0.0, sy, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-sy, 0.0, cy, 0.0],
        [0.0, 0.0, 0.0, 1.0],
      ],
      dtype=np.float32,
    )

    cx, sx = math.cos(angle_x), math.sin(angle_x)
    Rx = np.array(
      [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, cx, -sx, 0.0],
        [0.0, sx, cx, 0.0],
        [0.0, 0.0, 0.0, 1.0],
      ],
      dtype=np.float32,
    )

    S = np.diag([scale, scale, scale, 1.0]).astype(np.float32)
    return T @ Ry @ Rx @ S
