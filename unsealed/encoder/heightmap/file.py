import cv2
import numpy as np

class HeightmapEncoder():
  def __init__(self, terrain):
    self.terrain = terrain

  def encode(self, path):
    heightmap = np.array(self.terrain.heightmap) 
    altitudes = heightmap.reshape(self.terrain.height, self.terrain.width)
    # TODO: Adjust these calculation as needed
    alt_range = (altitudes.max() - altitudes.min())
    altitudes -= altitudes.min()
    altitudes *= 65535.0/alt_range
    altitudes = altitudes.astype(np.uint16)
    cv2.imwrite(path, altitudes)
