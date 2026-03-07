from __future__ import annotations

from ...rendering import HudAction, HudButton, HudPanel


class PlaybackControlPanel(HudPanel):
  """Bottom-left panel: animation info + Play/Pause and Stop buttons."""

  def __init__(
    self, group_name: str, current_time: float, duration: float, playing: bool
  ) -> None:
    play_btn = (
      HudButton("||", "Pause", HudAction.PLAY)
      if playing
      else HudButton("▶", "Play", HudAction.PLAY)
    )
    super().__init__(
      lines=[f"[{group_name}]  {current_time:.2f} / {duration:.2f}s"],
      buttons=[play_btn, HudButton("■", "Stop", HudAction.STOP)],
      x=10,
      y=-10,
    )
