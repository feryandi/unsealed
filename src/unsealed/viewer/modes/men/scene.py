"""MenScene — composition of UI elements parsed from a .men file.

The .men file says how to lay out a game UI screen by referencing sprites
inside a sibling .spr atlas (same stem; `login.men` ↔ `login.spr`).
Each element gives:
  - `spr_file` : which subdirectory inside the .spr (e.g. "login.tga")
  - `spr_idx`  : 0-based index of the cropped sprite within that subdir
  - `rectangle`: [x1, y1, x2, y2] target placement in canvas pixel coords

The viewer's job is to draw each element's sprite into its rectangle.
Sprite pixels live once per source atlas (see `viewer.sprite_atlas`);
each MenElement just carries a `SpriteRef` per state pointing at a
sub-rectangle of one of those atlases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ...scenes import ViewerScene
from ...sprite_atlas import SpriteAtlas, SpriteRef


STATE_NAMES: Tuple[str, ...] = ("base", "click", "disabled", "hover", "focus")


@dataclass
class MenElement:
  """One UI element from a .men file, with a SpriteRef per declared state.

  `state_refs` is keyed by state name (subset of STATE_NAMES) — only states
  the .men actually declared get an entry. `active_state` picks which
  ref the viewer currently renders; the detail panel lets the user switch
  it. `state_indices` is the raw sprite-index dump for the panel display.
  """

  label: str
  type: str
  spr_file: Optional[str]  # subdir name in .spr
  spr_idx: int
  rectangle: Tuple[int, int, int, int]  # (x1, y1, x2, y2) pixel coords
  state_refs: Dict[str, SpriteRef] = field(default_factory=dict)
  state_indices: Dict[str, int] = field(default_factory=dict)
  active_state: str = "base"
  # DFS/preorder tree info — indices refer to positions in MenScene.elements.
  parent: Optional[int] = None
  children: List[int] = field(default_factory=list)
  subtree_size: int = 0
  # User-toggled visibility for this element's entire group (subtree). The
  # *effective* hidden state — including ancestor propagation — lives on
  # MenScene.hidden_set so the render hot path is one set lookup.
  hidden: bool = False
  raw: Dict[str, Any] = field(default_factory=dict)  # full attribute dump

  def current_ref(self) -> Optional[SpriteRef]:
    return self.state_refs.get(self.active_state)


@dataclass
class MenScene(ViewerScene):
  """Scene for the .men UI viewer."""

  spr_file_name: str = ""
  atlases: List[SpriteAtlas] = field(default_factory=list)
  elements: List[MenElement] = field(default_factory=list)
  # Indices in `elements` that have no parent — top-level roots of the
  # element forest. The tree is built from each element's `subtree_size`
  # via DFS in MenViewerPipeline.
  root_indices: List[int] = field(default_factory=list)
  canvas_w: int = 0
  canvas_h: int = 0
  version: int = 0
  selected_element_idx: Optional[int] = None
  # Indices that are effectively hidden — union of every `hidden` element's
  # subtree. Recomputed on every visibility toggle via `recompute_hidden_set`.
  hidden_set: Set[int] = field(default_factory=set)

  def active_element(self) -> Optional[MenElement]:
    if self.selected_element_idx is None:
      return None
    if 0 <= self.selected_element_idx < len(self.elements):
      return self.elements[self.selected_element_idx]
    return None

  def recompute_hidden_set(self) -> None:
    """Rebuild `hidden_set` from every element's `hidden` flag.

    For each element with `hidden=True`, mark itself and every descendant.
    Iterative subtree walk via the `children` lists — no recursion limit.
    """
    self.hidden_set.clear()
    for i, el in enumerate(self.elements):
      if not el.hidden:
        continue
      stack = [i]
      while stack:
        idx = stack.pop()
        if idx in self.hidden_set:
          continue
        self.hidden_set.add(idx)
        stack.extend(self.elements[idx].children)
