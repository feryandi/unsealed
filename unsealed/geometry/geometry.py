from geometry.mesh import Mesh

class Geometry:
  def __init__(self):
    self.meshes = []
    self.mesh_name_to_id = {}
    self.materials = []

  def add_mesh(self, mesh):
    self.meshes.append(mesh)
    self.mesh_name_to_id[mesh.name.lower()] = len(self.meshes) - 1

  def add_material(self, material):
    self.materials.append(material)

  # TODO: animation could be on bone, so this should not be here
  def add_animation(self, animation):
    mesh_id = self.__get_mesh_id_by_name(animation.mesh_name)
    mesh = self.meshes[mesh_id]
    mesh.add_animation(animation)

  def __get_mesh_id_by_name(self, name):
    if name in self.mesh_name_to_id:
      return self.mesh_name_to_id[name.lower()]
    return -1

  # TODO: Delete once not used
  def get_mesh_id_by_name(self, name):
    if name in self.mesh_name_to_id:
      return self.mesh_name_to_id[name.lower()]
    return -1

  def __repr__(self):
    return f"<Node meshes:{self.meshes}>"
