
class Model:
  def __init__(self):
    self.geometry = None
    self.animations = {}
    self.skeleton = None

  def add_geometry(self, geometry):
    self.geometry = geometry

  def add_animation(self, name, animation):
    # TODO: Properly support multi-animation
    if name not in self.animations:
      self.animations[name] = []
    self.animations[name].append(animation)

  def add_skeleton(self, skeleton):
    self.skeleton = skeleton

  def __repr__(self):
    return f"<Model geometry:{self.geometry} skeleton:{self.skeleton} animations:{self.animations}>"
