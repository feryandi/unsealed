from __future__ import annotations

from ...rendering import HudAction, HudButton, HudPanel


class ImageControlPanel(HudPanel):
  """Top-left panel shown in 2-D texture viewer mode."""

  def __init__(self, filename: str, image_w: int, image_h: int, zoom_pct: int) -> None:
    super().__init__(
      lines=[
        f"File : {filename}",
        f"Size : {image_w} × {image_h} px",
        f"Zoom : {zoom_pct}%",
        "",
        "Controls:",
        "  Drag      : Pan",
        "  Scroll    : Zoom",
        "  R / F     : Fit image",
        "  O         : Open file",
        "  Esc       : Quit",
      ],
      x=10,
      y=10,
      buttons=[HudButton("", "Open File", HudAction.OPEN)],
    )
