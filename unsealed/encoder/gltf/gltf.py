import base64
import io
import json
import math
import struct

import numpy as np
import mathutils


class GLTF:
  def __init__(self):
    self.gltf = {}
    self.gltf["asset"] = {"version": "2.0"}
    self.gltf["buffers"] = []
    self.gltf["bufferViews"] = []
    self.gltf["accessors"] = []
    self.gltf["meshes"] = []
    self.gltf["nodes"] = []
    self.gltf["scenes"] = [{
      "nodes": []
    }]
    self.gltf["scene"] = 0

    self.node_name_to_node_idx = {}

  def encode(self, path):
    with open(path + ".gltf", "w") as f:
      f.write(json.dumps(self.gltf, indent=2))

  def add_node(self, name = None, mesh = None, skin = None, translation = None, rotation = None, scale = None):
    node = {}
    if name is not None:
      node["name"] = name
    if mesh is not None:
      node["mesh"] = mesh
    if skin is not None:
      node["skin"] = skin
    if translation is not None:
      node["translation"] = translation
    if rotation is not None:
      node["rotation"] = rotation
    if scale is not None:
      node["scale"] = scale
    self.gltf["nodes"].append(node)
    idx = len(self.gltf["nodes"]) - 1
    if name is not None:
      key = name.lower()
      if key in self.node_name_to_node_idx:
        raise Exception("Node name duplicate detected")
      self.node_name_to_node_idx[key] = idx # TODO: Rethink! This should be a problem to solved in bn1 decoder, not here
    return idx # TODO: Use this

  def add_node_children(self, parent_idx, child_idx):
    if "children" not in self.gltf["nodes"][parent_idx]:
      self.gltf["nodes"][parent_idx]["children"] = []
    self.gltf["nodes"][parent_idx]["children"].append(child_idx)

  def add_mesh(self, mesh, material = None):
    mesh_gltf = {
      "name": mesh.name,
      "primitives": []
    }

    materials = 1
    if material is not None:
      if len(material.sub_materials) != 0:
        materials = len(material.sub_materials)
      else:
        materials = 1

    joints_accessors = self.__add_joints(mesh.joints)
    weights_accessors = self.__add_weights(mesh.weights)
    vertices_accesors = self.__add_vertices(mesh.vertices)
    indices_buffer = self.__add_indices_buffer(mesh.indices)
    print(len(mesh.indices))
    for i in range(materials):
      primitive = {}
      primitive["mode"] = 4
      primitive["attributes"] = {}

      primitive["attributes"]["NORMAL"] = vertices_accesors["normal"]
      primitive["attributes"]["POSITION"] = vertices_accesors["position"]
      primitive["attributes"]["TEXCOORD_0"] = vertices_accesors["textcoord"]

      indices_parts = len(mesh.indices) // materials
      indices_accessor = self.__add_accessor(indices_buffer, 5123, indices_parts, "SCALAR", byte_offset = indices_parts * i * 2)
      primitive["indices"] = indices_accessor

      for idx, a in enumerate(joints_accessors):
        primitive["attributes"]["JOINTS_" + str(idx)] = a

      for idx, a in enumerate(weights_accessors):
        primitive["attributes"]["WEIGHTS_" + str(idx)] = a

      if material is not None:
        primitive["material"] = mesh.material_index + i # TODO

      mesh_gltf["primitives"].append(primitive)

    self.gltf["meshes"].append(mesh_gltf)

    if len(joints_accessors) > 0 and len(weights_accessors) > 0:
      self.add_node(
        name = mesh.name,
        mesh = len(self.gltf["meshes"]) - 1,
        skin = 0 # TODO?
      )
    else:
      # Decompose transformation matrix
      tm = np.array(mesh.tm).T
      mtx = mathutils.Matrix(tm)
      loc, rot, sca = mtx.decompose()
      self.add_node(
        name = mesh.name,
        mesh = len(self.gltf["meshes"]) - 1,
        translation = [loc[0], loc[1], loc[2]],
        rotation = [rot[1], rot[2], rot[3], rot[0]],
        scale =[sca[0], sca[1], sca[2]]
      )
    if mesh.parent is None or not mesh.parent.strip():
      self.gltf["scenes"][0]["nodes"].append(len(self.gltf["nodes"]) - 1)

  def fix_hack_mesh_with_bone_parent(self, mesh, skeleton):
    # TODO: Fix this hack. 
    # The fix need to rethink the way that we store mesh and bones and how we can detect the connection early on.
    if mesh.parent is None or not mesh.parent.strip():
      return
    parent_idx = self.node_name_to_node_idx[mesh.parent.lower()]
    node_idx = self.node_name_to_node_idx[mesh.name.lower()]
    self.add_node_children(parent_idx, node_idx)

    # Fix to change global transformation to local transformation
    parent = skeleton.bones[skeleton.bone_name_to_id[mesh.parent.lower()]]
    pivot = np.array(parent.tm_inverse).T
    target = np.array(mesh.tm).T
    diff = np.matmul(pivot, target)
    mtx = mathutils.Matrix(diff)
    loc, rot, sca = mtx.decompose()

    self.gltf["nodes"][node_idx]["translation"] = [loc[0], loc[1], loc[2]]
    self.gltf["nodes"][node_idx]["rotation"] = [rot[1], rot[2], rot[3], rot[0]]
    self.gltf["nodes"][node_idx]["scale"] = [sca[0], sca[1], sca[2]]

  def add_skin(self, skeleton):
    skin_bytes = io.BytesIO()
    joints = []

    for bone in skeleton.bones:
      loc = bone.loc
      rot = [bone.rot[0], bone.rot[1], bone.rot[2], bone.rot[3]]
      sca = bone.sca

      if bone.parent is not None:
        # Convert to local transformation
        parent = skeleton.bones[skeleton.bone_name_to_id[bone.parent.lower()]]
        pivot = np.array(parent.tm_inverse).T
        target = np.array(bone.tm).T
        diff = np.matmul(pivot, target)
        mtx = mathutils.Matrix(diff)
        loc, rot, sca = mtx.decompose()

      node_idx = self.add_node(
        name = bone.name,
        translation = [loc[0], loc[1], loc[2]],
        rotation = [rot[1], rot[2], rot[3], rot[0]],
        scale =[sca[0], sca[1], sca[2]]
      )
      joints.append(node_idx)

      if bone.parent is not None:
        parent_idx = self.node_name_to_node_idx[bone.parent.lower()]
        self.add_node_children(parent_idx, node_idx)
      else:
        self.gltf["scenes"][0]["nodes"].append(node_idx)

      s = [item for row in bone.tm_inverse for item in row]

      skin_bytes.write(struct.pack('f'*len(s), *s))

    b = self.__add_buffer(skin_bytes)
    skin_accessor_idx = self.__add_accessor(b, 5126, len(skeleton.bones), "MAT4")

    self.gltf["skins"] = [{
      "inverseBindMatrices": skin_accessor_idx,
      "joints": joints
    }]

  def add_material(self, material):
    # TODO: Currently adding more material didn't do anything, it will just use 1 material
    if "materials" not in self.gltf:
      self.gltf["materials"] = []
    if "textures" not in self.gltf:
      self.gltf["textures"] = []
    if "images" not in self.gltf:
      self.gltf["images"] = []

    bitmap = material.bitmap.split(".")[0]
    bitmap_png = bitmap + ".png"
    self.gltf["images"].append({
      "uri": bitmap_png # TODO: Streamline this into pipeline
    })
    self.gltf["textures"].append({
      "source": len(self.gltf["images"]) - 1
    })
    self.gltf["materials"].append({
      "pbrMetallicRoughness" : {
        "baseColorTexture" : {
          "index" : len(self.gltf["textures"]) - 1
        },
        "metallicFactor" : 0.0,
        "roughnessFactor" : 1.0
      }
    })

    # TODO: Search for this data on the ms1 file. Mapping of mesh to material.
    # for mesh in self.gltf["meshes"]:
    #   mesh["primitives"][0]["material"] = 0

    if len(self.gltf["textures"]) == 0:
      del self.gltf["textures"]
    if len(self.gltf["images"]) == 0:
      del self.gltf["images"]


  def add_animation(self, animations):
    # TODO: This is hacky thing, unable to add more animation this way
    if "animations" not in self.gltf:
      self.gltf["animations"] = []
    i = len(self.gltf["animations"])
    self.gltf["animations"].append({
        "samplers": [],
        "channels": []
    })

    for a in animations:
      animation = self.__create_animation(a)
      for sampler in animation["samplers"]:
        self.gltf["animations"][i]["samplers"].append(sampler)
      for channel in animation["channels"]:
        self.gltf["animations"][i]["channels"].append(channel)
        # TODO: Super hacky thing
        self.gltf["animations"][i]["channels"][-1]["sampler"] = len(self.gltf["animations"][i]["channels"]) - 1

    if len(self.gltf["animations"][i]["samplers"]) == 0:
      del self.gltf["animations"]

  def __create_animation(self, animation):
    # TODO: Maybe something better?
    animation_gltf = {
      "samplers": [],
      "channels": []
    }
    node_idx = self.node_name_to_node_idx[animation.mesh_name.lower()]
    path_names = ["translation", "rotation", "scale"]
    output_types = ["VEC3", "VEC4", "VEC3"]
    for idx, sub in enumerate([animation.transforms, animation.rotations, animation.scales]):
      if len(sub) == 0:
        continue

      animation_bytes = io.BytesIO()
      keyframes = []
      values = []

      for x in sub:
        frame_num = x.time / animation.smallest_keyframe
        time_sec = frame_num / animation.fps
        keyframes.append(time_sec)
        values.extend(x.value)

      animation_bytes.write(struct.pack('f'*len(keyframes), *keyframes))
      animation_bytes.write(struct.pack('f'*len(values), *values))

      b = self.__add_buffer(animation_bytes)
      a_input = self.__add_accessor(b, 5126, len(sub), "SCALAR")
      a_output = self.__add_accessor(b, 5126, len(sub), output_types[idx], byte_offset = len(keyframes) * 4)

      animation_gltf["samplers"].append(self.__create_animation_sampler(a_input, a_output))
      sampler_idx = len(animation_gltf["samplers"]) - 1
      animation_gltf["channels"].append(self.__create_animation_channel(sampler_idx, node_idx, path_names[idx]))
    return animation_gltf

  def __create_animation_sampler(self, input_accessor_idx, output_accessor_idx, interpolation = "LINEAR"):
    return {
      "input": input_accessor_idx,
      "interpolation": interpolation,
      "output": output_accessor_idx
    }

  def __create_animation_channel(self, sampler_accessor_idx, node_idx, path):
    return {
      "sampler": sampler_accessor_idx,
      "target": {
        "node": node_idx,
        "path": path
      }
    }

  def __add_vertices(self, vertices):
    position_bytes = io.BytesIO()
    normal_bytes = io.BytesIO()
    texcoord_bytes = io.BytesIO()

    for v in vertices:
      p = [v.position[0], v.position[1], v.position[2]]
      position_bytes.write(struct.pack('f'*len(p), *p))
      n = [v.normal[0], v.normal[1], v.normal[2]]
      normal_bytes.write(struct.pack('f'*len(n), *n))
      t = [v.texcoord[0], v.texcoord[1]]
      texcoord_bytes.write(struct.pack('f'*len(t), *t))

    b = self.__add_buffer(position_bytes)
    p_a = self.__add_accessor(b, 5126, len(vertices), "VEC3")
    b = self.__add_buffer(normal_bytes)
    n_a = self.__add_accessor(b, 5126, len(vertices), "VEC3")
    b = self.__add_buffer(texcoord_bytes)
    t_a = self.__add_accessor(b, 5126, len(vertices), "VEC2")

    return {
      "position": p_a,
      "normal": n_a,
      "textcoord": t_a
    } 
      
  def __add_indices_buffer(self, indices):
    indices_bytes = io.BytesIO()

    for i in indices:
      p = [i]
      indices_bytes.write(struct.pack('H'*len(p), *p))

    return self.__add_buffer(indices_bytes)
    # return self.__add_accessor(b, 5123, len(indices), "SCALAR")

  def __add_joints(self, joints):
    joints_bytes = self.__split_by_fours(joints)
    joints_max_length = 8  # TODO
    accessors = []

    for i in range(joints_max_length):
      is_empty = True
      j_bytes = io.BytesIO()
      for joint in joints_bytes:
        j = [0, 0, 0, 0]
        if len(joint) > i:
          j = joint[i]
          is_empty = False
        j_bytes.write(struct.pack('H'*len(j), *j))
      if is_empty:
        break
      b = self.__add_buffer(j_bytes)
      accessors.append(self.__add_accessor(b, 5123, len(joints_bytes), "VEC4"))
    return accessors

  def __add_weights(self, weights):
    weights_bytes = self.__split_by_fours(weights)
    weights_max_length = 8  # TODO
    accessors = []

    for i in range(weights_max_length):
      is_empty = True
      w_bytes = io.BytesIO()
      for weight in weights_bytes:
        w = [0, 0, 0, 0]
        if len(weight) > i:
          w = weight[i]
          is_empty = False
        w_bytes.write(struct.pack('f'*len(w), *w))
      if is_empty:
        break
      b = self.__add_buffer(w_bytes)
      accessors.append(self.__add_accessor(b, 5126, len(weights_bytes), "VEC4"))
    return accessors

  def __split_by_fours(self, data):
    data_bytes = []
    for d in data:
      parts = []
      num_parts = math.ceil(len(d) / 4)
      for i in range(num_parts):
        flattened = []
        for j in range(4):
          idx = j + (i * 4)
          if len(d) > idx:
            flattened.append(d[idx])
          else:
            flattened.append(0)
        parts.append(flattened)
      data_bytes.append(parts)
    return data_bytes

  def __add_buffer(self, data):
    data.seek(0)
    bdata = data.read()
    b64 = base64.b64encode(bdata).decode('ascii')
    if len(bdata) > 0:
      self.gltf["buffers"].append({
        "byteLength": len(bdata),
        "uri": "data:application/octet-stream;base64," + b64
      })
      self.gltf["bufferViews"].append({
        "buffer": len(self.gltf["buffers"]) - 1,
        "byteLength": len(bdata),
        "byteOffset": 0,
      })
      return len(self.gltf["bufferViews"]) - 1
    return -1
  
  def __add_accessor(self, buffer_view_idx, component_type, count, type, byte_offset = 0):
    self.gltf["accessors"].append({
      "bufferView" : buffer_view_idx,
      "byteOffset" : byte_offset,
      "componentType" : component_type,
      "count" : count,
      "type" : type
    })
    return len(self.gltf["accessors"]) - 1
