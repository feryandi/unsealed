from assets.resource import Resource


class Action:
  def __init__(self, name: str | None, filename: str):
    self.name = name
    self.filename = filename
    self.resources: list[Resource] = []

  def add_resource(self, resource):
    # This resource could be: sound, effect, etc.
    # TODO: Need to figure out how to decode it from the .act file
    self.resources.append(resource)
