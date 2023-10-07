
class Terrain:
  def __init__(self, heightmap, width, height):
    self.heightmap = heightmap
    self.width = width
    self.height = height

  def __repr__(self):
    return f"<Terrain width:{self.width} height:{self.height} >"
