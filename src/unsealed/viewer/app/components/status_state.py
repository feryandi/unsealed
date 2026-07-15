from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StatusComponent:
  """State for the sticky bottom status bar.

  `loading` drives the spinner; `message` is the text shown (a loading
  label while busy, otherwise the current file / idle text). Intended to
  grow into a general status/metadata bar over time.
  """

  loading: bool = False
  message: str = ""
