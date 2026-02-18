import os
from pathlib import Path

from ...utils.file import File
from ...assets.terrain import Terrain


class SealMapDecoder:
  def __init__(self, path: Path):
    self.version = 1
    self.path = path
    self.filename = os.path.splitext(os.path.basename(path))[0].split(".")[0]
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open map file")

  def decode(self) -> Terrain:
    if self.file is None:
      raise Exception("File was not initialized properly")

    terrain = Terrain(512, 512)
    self.version = self.__decode_version()

    if self.version == 5:
      # Unsupported even by the game?
      # Example: 67.map
      return terrain

    s = self.file.read_string(20)
    if self.version > 10:
      _ = self.file.read(1)

    s = self.file.read_string(172)
    if self.version == 10:
      _ = self.file.read(1)

    _ = self.file.read(7)

    if self.version >= 14:
      s = self.file.read_string(40)

    if self.version > 10:
      s = self.file.read_string(32)
      s = self.file.read_string(32)

    # Textures
    n = self.file.read_int()
    for i in range(n):
      s = self.file.read_string(16 * 4)
      _ = self.file.read(4)
      terrain.add_texture(s)

    # Lightmap texture
    s = self.file.read_string(16 * 4)
    terrain.add_lightmap(s)

    # Texture Layer 1
    i = 64
    a = []
    for i in range(i):
      x = self.file.read_int()
      a.append(x)
    terrain.add_terrain_layer_a(a)

    # Texture Layer 2
    i = 64
    a = []
    for i in range(i):
      x = self.file.read_int()
      a.append(x)
    terrain.add_terrain_layer_b(a)

    # Heightmap
    i = 512 * 512
    n = []
    for i in range(i):
      x = self.file.read_float()
      n.append(x)
    terrain.add_heightmap(n)

    # Walkable area
    i = 512 * 512
    n = []
    for i in range(i):
      x = self.file.read_int()
      n.append(x)

    # Object placement
    a = self.file.read_int()
    for x in range(a):
      n = self.file.read_int()  # This could be related to object index
      p = [self.file.read_float(), self.file.read_float(), self.file.read_float()]
      r = [self.file.read_float(), self.file.read_float(), self.file.read_float()]
      if self.version > 11:
        r.append(self.file.read_float())
      terrain.add_object(n, p, r)

    num_objects = self.file.read_int()
    for x in range(num_objects):
      s = self.file.read_string(204)
      terrain.add_object_file(s)

    return terrain

  def __decode_version(self) -> int:
    header = self.file.read_string(64)
    if header == "Map File v.5":
      return 5
    if header == "Map File v.10":
      return 10
    if header == "Map File v.11":
      return 11
    if header == "Map File v.12":
      return 12
    if header == "Map File v.13":
      return 13
    if header == "Map File v.14":
      return 14
    return 10
