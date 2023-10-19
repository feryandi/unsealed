import json

class Terrain:
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
    self.objects.append({
      'idx': idx,
      'pos': pos,
      'rot': rot,
    })

  def add_terrain_layer_a(self, terrain_layer):
    self.terrain_layer_a = terrain_layer

  def add_terrain_layer_b(self, terrain_layer):
    self.terrain_layer_b = terrain_layer

  def add_texture(self, texture):
    self.textures.append(texture)

  def add_lightmap(self, lightmap):
    self.lightmap = lightmap

  def to_json(self):
    data = {}
    data["heightmap"] = self.heightmap
    data["lightmap"] = self.lightmap
    data["textures"] = self.textures
    data["terrain_layer_a"] = self.terrain_layer_a
    data["terrain_layer_b"] = self.terrain_layer_b
    data["objects"] = self.objects
    data["object_files"] = self.object_files
    return json.dumps(data)

  def __repr__(self):
    return f"<Terrain width:{self.width} height:{self.height} >"
