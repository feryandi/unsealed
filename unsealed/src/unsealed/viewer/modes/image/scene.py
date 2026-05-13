"""ImageScene — scene type for .tex / .te1 / plain image files."""

from dataclasses import dataclass
from typing import Optional

from ...scenes import ViewerScene


@dataclass
class ImageScene(ViewerScene):
  """Scene for the 2-D texture viewer. Holds raw pixel data only."""

  image: Optional[bytes] = None  # raw RGBA bytes, top-to-bottom row order
  image_w: int = 0
  image_h: int = 0
