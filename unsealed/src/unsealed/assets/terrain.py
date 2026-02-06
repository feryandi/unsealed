import json
import base64
import numpy as np
import zlib

from array import array
from ..core.asset import Asset


class Terrain(Asset):
  def __init__(self, width, height):
    self.heightmap = []
    self.width = width
    self.height = height
    self.objects = []
    self.object_files = []
    self.textures = []
    self.lightmap = None
    self.terrain_layer_a = []
    self.terrain_layer_b = []

  def add_heightmap(self, heightmap):
    self.heightmap = heightmap

  def add_object_file(self, filename):
    self.object_files.append(filename)

  def add_object(self, idx, pos, rot):
    self.objects.append(
      {
        "idx": idx,
        "pos": pos,
        "rot": rot,
      }
    )

  def add_terrain_layer_a(self, terrain_layer):
    self.terrain_layer_a = terrain_layer

  def add_terrain_layer_b(self, terrain_layer):
    self.terrain_layer_b = terrain_layer

  def add_texture(self, texture):
    self.textures.append(texture)

  def add_lightmap(self, lightmap):
    self.lightmap = lightmap

  def to_json(self):
    return json.dumps(self.to_serializable())

  def to_serializable(self):
    """Return a compact, JSON-serializable dict.

    The `heightmap` is encoded as base64 of Float32 bytes to keep the
    JSON compact and easy to decode in JS as a Float32Array.
    """
    # convert heightmap list -> bytes -> base64 with optional float16 + zlib
    hm_b64 = None
    hm_encoding = None
    if self.heightmap:
      # prefer numpy-based float16 + zlib if numpy is available
      if np is not None:
        try:
          arr = np.array(self.heightmap, dtype=np.float32)
          arr16 = arr.astype(np.float16)
          bytes_data = arr16.tobytes()
          comp = zlib.compress(bytes_data, level=6)
          hm_b64 = base64.b64encode(comp).decode("ascii")
          hm_encoding = "f16+zlib"
        except Exception:
          hm_b64 = None
          hm_encoding = None

      if hm_b64 is None:
        # fallback to float32 with zlib
        try:
          a = array("f", self.heightmap)
          bytes_data = a.tobytes()
          comp = zlib.compress(bytes_data, level=6)
          hm_b64 = base64.b64encode(comp).decode("ascii")
          hm_encoding = "f32+zlib"
        except Exception:
          try:
            a = array("f", self.heightmap)
            hm_b64 = base64.b64encode(a.tobytes()).decode("ascii")
            hm_encoding = "f32"
          except Exception:
            hm_b64 = None
            hm_encoding = None

    data = {
      "width": self.width,
      "height": self.height,
      # if hm_b64 is present, clients should decode it as Float32s
      "heightmap_b64": hm_b64,
      # encoding tag: one of f16+zlib, f32+zlib, f32, or null
      "heightmap_encoding": hm_encoding,
      # keep a legacy `heightmap` raw array when encoding would fail
      "heightmap": None if hm_b64 is not None else self.heightmap,
      "lightmap": self.lightmap,
      "textures": self.textures,
      "terrain_layer_a": self.terrain_layer_a,
      "terrain_layer_b": self.terrain_layer_b,
      "objects": self.objects,
      "object_files": self.object_files,
    }
    return data

  def __repr__(self):
    return f"<Terrain width:{self.width} height:{self.height} >"
