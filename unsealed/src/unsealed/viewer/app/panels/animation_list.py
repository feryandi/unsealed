from __future__ import annotations

from typing import List

from ...rendering import HudAction, HudButton, HudPanel


class AnimationListPanel(HudPanel):
  """Right-side panel listing all animations as a clickable list."""

  def __init__(self, anim_names: List[str], current_idx: int) -> None:
    super().__init__(
      lines=["Animations:"],
      list_items=[
        HudButton("", name, HudAction.SELECT_ANIM, i) for i, name in enumerate(anim_names)
      ],
      list_highlight_idx=current_idx,
      x=-10,
      y=10,
    )
