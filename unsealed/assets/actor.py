from assets.action import Action


class Actor:
  def __init__(self, name: str, filename: str):
    self.name = name
    self.filename = filename
    self.actions: list[Action] = []

  def add_action(self, action):
    self.actions.append(action)
