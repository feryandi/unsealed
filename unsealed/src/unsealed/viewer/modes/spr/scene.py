"""SprScene — atlas-and-UV view of a .spr sprite sheet.

Mirrors MenScene: one GL texture per source atlas, plus a `SpriteRef`
per sprite that carries pixel coords into its atlas. The "selection" is
a `(atlas_idx, sprite_idx)` pair that picks which sub-rectangle to draw;
`sprite_idx == FULL_ATLAS_IDX (-1)` means "show the whole atlas".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ...scenes import ViewerScene
from ...sprite_atlas import FULL_ATLAS_IDX, SpriteAtlas, SpriteRef


@dataclass
class SprScene(ViewerScene):
  """Scene for the SPR sprite-atlas viewer.

  `atlas_sprite_indices[i]` is the sorted list of cropped-sprite indices
  the .spr declared for atlas `i`. The HUD walks these to render its
  tree without needing to recompute the order each frame.
  """

  file_name: str = ""
  atlases: List[SpriteAtlas] = field(default_factory=list)
  sprite_refs: Dict[Tuple[str, int], SpriteRef] = field(default_factory=dict)
  atlas_sprite_indices: List[List[int]] = field(default_factory=list)
  selected_atlas: int = 0
  selected_sprite: int = FULL_ATLAS_IDX

  def active_atlas(self) -> Optional[SpriteAtlas]:
    if 0 <= self.selected_atlas < len(self.atlases):
      return self.atlases[self.selected_atlas]
    return None

  def active_ref(self) -> Optional[SpriteRef]:
    atlas = self.active_atlas()
    if atlas is None:
      return None
    return self.sprite_refs.get((atlas.name, self.selected_sprite))
