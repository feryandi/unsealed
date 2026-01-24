from model.vertex import Vertex


class Mesh:
  def __init__(self, name, parent=None):
    self.name = name
    self.parent = parent

    self.vertices = []
    self.indices = {}
    self.old_indices = []
    self.joints = []
    self.weights = []

    self.tm = None
    self.animations = {}
    self.material_index = None

  def add_vertex(self, vertex: Vertex):
    self.vertices.append(vertex)
    self.joints.append([])
    self.weights.append([])

  def add_index(self, n, index):
    if n not in self.indices:
      self.indices[n] = []
    self.indices[n].append(index)
    self.old_indices.append(index)

  def add_joint(self, vertex_idx, bone_idx):
    self.joints[vertex_idx].append(bone_idx)

  def add_weight(self, vertex_idx, weight):
    self.weights[vertex_idx].append(weight)

  def add_transform_matrix(self, transform_matrix):
    self.tm = transform_matrix

  def add_animation(self, animation):
    self.animations[animation.name] = animation

  # TODO: Put this on gltf encoder
  def get_joints_flatten(self):
    # TODO: Support joints more than 4
    flattened = []
    for joint in self.joints:
      for i in range(4):
        if len(joint) > i:
          flattened.append(joint[i])
        else:
          flattened.append(0)
    return flattened

  # TODO: Put this on gltf encoder
  def get_weights_flatten(self):
    # TODO: Support weights more than 4
    flattened = []
    for weight in self.weights:
      for i in range(4):
        if len(weight) > i:
          flattened.append(weight[i])
        else:
          flattened.append(0)
    return flattened

  def __repr__(self):
    return f"<Mesh name:\"{self.name}\">"
