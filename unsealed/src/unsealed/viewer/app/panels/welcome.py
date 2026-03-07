from __future__ import annotations

from ...rendering import HudAction, HudButton, HudPanel


class WelcomePanel(HudPanel):
  def __init__(self) -> None:
    super().__init__(
      lines=["Unsealed 3D Viewer"],
      buttons=[HudButton("", "Open File", HudAction.OPEN)],
      x=10,
      y=10,
    )
