"""SprCamera — alias for the 2-D image camera used by SPR mode."""

from ..image.camera import ImageCamera


class SprCamera(ImageCamera):
  """SPR mode uses the same orthographic 2-D camera as image mode."""

  pass
