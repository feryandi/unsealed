from typing import List
from .mesh import Mesh
from ..core.asset import Asset
from .material import Material


class Geometry(Asset):
  """
  Geometry intermediate representation.

  Contains classes for handling raw geometric data, including index
  buffers and primitive topology definitions.
  """

  def __init__(self):
    self.meshes: List[Mesh] = []
    self.materials: List[Material] = []

  def __repr__(self):
    return f"<Node meshes:{self.meshes}>"
