"""HUD widget data classes.

These describe the panels/buttons the HUD renderer draws each frame and the
action identifiers click handlers dispatch on. They live outside the
`rendering` package so mode panel modules can import them without pulling in
GL — eliminating the old circular-import workaround between `rendering` and
`modes/<m>/panels.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Tuple


class HudAction:
  """Action identifier constants for HudButton.action."""

  OPEN = "open"
  PLAY = "play"
  STOP = "stop"
  SELECT_ANIM = "select_anim"
  TOGGLE_Q3 = "toggle_q3"


@dataclass
class HudButton:
  """
  A clickable button rendered inside a HudPanel.

  icon        : Unicode symbol shown left of the label (empty string = icon-less)
  label       : Short text label
  action      : Action identifier dispatched on click (e.g. "play", "open", "select_anim")
  action_data : Optional payload forwarded to dispatch_action (e.g. animation index)
  rect        : Screen-space (x, y, w, h) in pixels — filled by HudRenderer each frame
  """

  icon: str
  label: str
  action: str
  action_data: Any = None
  rect: Tuple[int, int, int, int] = field(default_factory=lambda: (0, 0, 0, 0))


@dataclass
class HudPanel:
  """
  Describes one HUD text panel.

  x / y are pixel offsets from an edge:
    x >= 0 : offset from left edge
    x <  0 : offset from right edge  (panel right edge is -x pixels from window right)
    y >= 0 : offset from top edge
    y <  0 : offset from bottom edge
  highlight_idx      : index of the line to render in a brighter colour (-1 = none)
  buttons            : horizontal row of HudButton drawn below text lines
  list_items         : vertical list of HudButton drawn below the button row
  list_highlight_idx : index in list_items to highlight as the active selection
  """

  lines: List[str]
  x: int = 10
  y: int = 10
  highlight_idx: int = -1
  buttons: List[HudButton] = field(default_factory=list)
  list_items: List[HudButton] = field(default_factory=list)
  list_highlight_idx: int = -1
