from geometry.mesh import Mesh

from decoder.ms1.vertex import SealMeshVertexDecoder


class SealMeshMeshDecoder:
  def __init__(self, file):
    self.file = file
    self.tm = None
    self.name = None

  def decode(self):
    name = self.file.read_string(16 * 16 + 1)
    self.name = name
    print(name)
    parent = self.file.read_string(16 * 16)
    mesh = Mesh(name, parent)

    num_vertices = self.file.read_int()
    num_faces = self.file.read_int()
    material_index = self.file.read_int()  # TODO
    mesh.material_index = material_index
    print(material_index)

    # TODO
    ukwn = self.file.read(4)
    has_physique_data = False
    if ukwn == b'\xfe\xff\xff\xff':
      has_physique_data = True
    ukwn = self.file.read(4)

    # Transformation Matrix for vertex
    tm = [
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()]
    ]
      
    if has_physique_data:
      # Do not transform when it has bone / physique data
      tm = None

    mesh.add_transform_matrix(tm)
    print(hex(self.file.pointer))
    _ = self.file.read(4 * 16) # This could be transformation matrix or 0XCDCDCDCD that means uninitialized
    _ = self.file.read(24)
    _ = self.file.read(12)
    _ = self.file.read(68)
    print(hex(self.file.pointer))

    self.__decode_vertices(mesh, num_vertices)
    print(hex(self.file.pointer))
    self.__decode_indices(mesh, num_faces)
    if self.file.is_end() or not has_physique_data:
      return mesh
    self.__decode_physique(mesh)
    return mesh

  def __decode_vertices(self, mesh, num_vertices):
    for x in range(num_vertices):
      decoder = SealMeshVertexDecoder(self.file, mesh.tm)
      v = decoder.decode()
      mesh.add_vertex(v)

  def __decode_indices(self, mesh, num_faces):
    num_face_index = num_faces * 3
    for x in range(num_face_index):
      idx = self.file.read_short()
      # if self.name == "N_seit_new_body":
      #   if x > 860:
      #     print(num_face_index)
      #     continue
      mesh.add_index(idx)
    _padding = self.file.read(4 * num_faces)

  def __decode_physique(self, mesh):
    num_physique = self.file.read_int()
    for bone_idx in range(num_physique):
      p_num = self.file.read_int()
      weights = []
      for _ in range(p_num):
        weights.append(self.file.read_float())
      for i in range(p_num):
        vertex_idx = self.file.read_int()
        mesh.add_joint(vertex_idx, bone_idx)
        mesh.add_weight(vertex_idx, weights[i])
