from actor.action import SealAction


class SealActor:
  def __init__(self, name: str, filename: str):
    self.name = name
    self.filename = filename
    self.actions: list[SealAction] = []

  def add_action(self, action):
    self.actions.append(action)
