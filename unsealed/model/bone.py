
class Bone:
  def __init__(self):
    self.count = 0
    self.name = None
    self.parent = None

    self.tm = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
               [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    self.tm_inverse = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [
        0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]

    self.loc = [0.0, 0.0, 0.0]
    self.sca = [1.0, 1.0, 1.0]
    self.rot = [0.0, 0.0, 0.0, 1.0]

  def __repr__(self):
    return f"<Bone name:{self.name} parent:{self.parent}>"
