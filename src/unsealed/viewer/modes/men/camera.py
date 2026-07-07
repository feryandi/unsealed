"""MenCamera — orthographic 2-D camera, shared with image / SPR modes."""

from ..image.camera import ImageCamera


class MenCamera(ImageCamera):
  """.men UI viewer uses the same 2-D orthographic camera as image mode."""
  pass
