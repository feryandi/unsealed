import io
import os
import struct

from file import File

import sys
import numpy as np

from terrain.terrain import Terrain


class SealMapFileDecoder:
  def __init__(self, path):
    self.path = path
    self.file = None
    self.filename = os.path.splitext(os.path.basename(path))[0].split('.')[0]
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except:
      raise Exception("Unable to open map file")

  def decode(self):
    is_v5 = False
    is_v10 = False
    is_v11 = False
    is_v12 = False
    is_v13 = False

    header = self.file.read_string(64)
    # print(header)
    if header == "Map File v.5":
      return # unsupported even by the game?
    if header == "Map File v.10":
      is_v10 = True
    if header == "Map File v.11":
      is_v11 = True
    if header == "Map File v.12":
      is_v12 = True
    if header == "Map File v.13":
      is_v13 = True

    ukwn = self.file.read(16 + 5)
    ukwn = self.file.read_string(160)
    _ = self.file.read(1 * 16 + 3)

    if not is_v10:
      if not is_v12 and not is_v11 and not is_v13:
        _ = self.file.read(2 * 16 + 8)
      s = self.file.read_string(32)
      s = self.file.read_string(32)

    # Textures
    n = self.file.read_int()
    for i in range(n):
      s = self.file.read_string(16 * 4)
      _ = self.file.read(4)

    # Lightmap texture
    s = self.file.read_string(16 * 4)

    # Texture Layer 1
    i = 64
    a = []
    for i in range(i):
      x = self.file.read_int()
      a.append(x)

    # Texture Layer 2
    i = 64
    a = []
    for i in range(i):
      x = self.file.read_int()
      a.append(x)

    # Heightmap
    i = 512 * 512
    n = []
    for i in range(i):
      x = self.file.read_float()
      # x = self.file.read_int()
      n.append(x)
    terrain = Terrain(n, 512, 512)

    # Walkable area
    i = 512 * 512
    n = []
    for i in range(i):
      x = self.file.read_int()
      n.append(x)
    arr = np.array(n)
    narr =  arr.reshape(512, 512)

    # Object placement
    a = self.file.read_int()
    for x in range(a):
      n = self.file.read_int() # This could be related to obeject index
      p = [self.file.read_float(), self.file.read_float(), self.file.read_float()]
      r = [self.file.read_float(), self.file.read_float(), self.file.read_float()]
      if not is_v10 and not is_v11:
        _ = self.file.read_float()
      # Total: 28 Bytes

    num_objects = self.file.read_int()
    for x in range(num_objects):
      s = self.file.read_string(204)

    return terrain