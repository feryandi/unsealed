import numpy as np
from PIL import Image


class HeightmapEncoder():
  def __init__(self, terrain):
    self.terrain = terrain

  def encode(self, path):
    heightmap = np.array(self.terrain.heightmap)
    altitudes = heightmap.reshape(self.terrain.height, self.terrain.width)

    alt_min = altitudes.min()
    alt_range = altitudes.max() - alt_min

    if alt_range > 0:
      altitudes -= alt_min
      altitudes *= 65535.0 / alt_range

    # Convert to uint16
    altitudes = altitudes.astype(np.uint16)

    # Mode 'I;16' is for 16-bit unsigned integer grayscale
    img = Image.fromarray(altitudes, mode='I;16')
    img.save(path)
