from model.mesh import Mesh


class Geometry:
  def __init__(self):
    self.meshes = []
    self.mesh_name_to_id = {}
    self.materials = []

  def add_mesh(self, mesh: Mesh):
    self.meshes.append(mesh)
    self.mesh_name_to_id[mesh.name.lower()] = len(self.meshes) - 1

  def add_material(self, material):
    self.materials.append(material)

  def __repr__(self):
    return f"<Node meshes:{self.meshes}>"
