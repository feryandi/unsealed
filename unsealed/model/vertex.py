
class Vertex:
  def __init__(self, position=[0.0, 0.0, 0.0], normal=[0.0, 0.0, 0.0], texcoord=[0.0, 0.0]):
    self.position = position
    self.normal = normal
    self.texcoord = texcoord

  def __repr__(self):
    return f"<Vertex position:{self.position} normal:{self.normal} texcoord:{self.texcoord}>"
