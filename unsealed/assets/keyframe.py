from core.asset import Asset


class Keyframe(Asset):
  def __init__(self, time, value):
    self.time = time
    self.value = value

  def __repr__(self):
    return f"<Keyframe time:{self.time} value:{self.value} >"
