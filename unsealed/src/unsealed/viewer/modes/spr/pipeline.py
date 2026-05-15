"""Pipeline for .spr files → SprScene.

Delegates the .spr decode + atlas materialization to the shared
`decode_spr_for_viewer` helper, then derives the per-atlas list of
cropped-sprite indices the HUD needs.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from ...sprite_atlas import FULL_ATLAS_IDX, decode_spr_for_viewer
from .scene import SprScene


class SprViewerPipeline:
  """Decode a .spr into a SprScene of (atlases, sprite_refs)."""

  def run(self, path: Path) -> SprScene:
    try:
      atlases, sprite_refs = decode_spr_for_viewer(path)
    except Exception as e:
      print(f"[spr] decode failed: {e}")
      return SprScene(file_name=path.name)

    atlas_sprite_indices: List[List[int]] = []
    for atlas in atlases:
      indices = sorted(
        sprite_idx
        for (ref_name, sprite_idx) in sprite_refs.keys()
        if ref_name == atlas.name and sprite_idx != FULL_ATLAS_IDX
      )
      atlas_sprite_indices.append(indices)

    return SprScene(
      file_name=path.name,
      atlases=atlases,
      sprite_refs=sprite_refs,
      atlas_sprite_indices=atlas_sprite_indices,
      selected_atlas=0,
      selected_sprite=FULL_ATLAS_IDX,
    )
