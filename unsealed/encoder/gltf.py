import base64
import io
import json
import math
import struct

import numpy as np

from utils.strings import is_string_empty
from utils.matrix import decompose_mtx


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

    self.model = None

    self.node_name_to_node_idx = {}
    self.node_idx_to_mesh = {}
    self.geo_material_idx_to_gltf_material_idx = {}

  def encode(self, model, path):
    self.model = model
    if self.model is None:
      raise Exception("No model to encode")

    # Skeleton should be first
    # : Because it doesn't have any dependecies to other nodes
    self.__encode_skeleton()

    # Material should be before mesh
    # : Because mesh needs the GLTF's material index due to submaterial fix
    self.__encode_material()

    # Mesh
    self.__encode_mesh()

    # Animation should be last
    # : It needs data from both mesh and bone nodes
    self.__encode_animation()

    with open(path + ".gltf", "w") as f:
      f.write(json.dumps(self.gltf, indent=2))

  def __encode_material(self):
    if self.model is None:
      raise Exception("No model to encode")

    materials = self.model.geometry.materials
    if len(materials) == 0:
      return

    self.gltf["images"] = []
    self.gltf["textures"] = []
    self.gltf["materials"] = []

    bitmaps = []
    for idx, material in enumerate(materials):
      subs = material.sub_materials
      bitmap = material.bitmap
      alpha_mode = "MASK"
      if material.alpha_mode == 1:
        alpha_mode = "BLEND"
      for sub in subs:
        bitmap = sub.bitmap
        self.__add_material(bitmap, alpha_mode)
        bitmaps.append(bitmap)
      if len(subs) == 0:
        self.__add_material(bitmap, alpha_mode)
        bitmaps.append(bitmap)
      # else:
      #   if not is_string_empty(material.bitmap):
      #     raise Exception("Expect bitmap to be empty on material that has submaterial")
      self.geo_material_idx_to_gltf_material_idx[idx] = len(
          bitmaps) - max(1, len(subs))

  def __add_material(self, bitmap, alpha_mode="MASK"):
    self.gltf["materials"].append({
        "pbrMetallicRoughness": {
            "metallicFactor": 0.0,  # TODO
            "roughnessFactor": 1.0  # TODO
        },
        "alphaMode": alpha_mode
    })
    if not is_string_empty(bitmap):
      bitmap_filename = bitmap.split(".")[0]
      bitmap_png = bitmap_filename + ".png"  # TODO: Streamline this into pipeline
      self.gltf["images"].append({
          "uri": bitmap_png  # TODO: Streamline this into pipeline
      })
      self.gltf["textures"].append({
          "source": len(self.gltf["images"]) - 1
      })
      self.gltf["materials"][-1]["pbrMetallicRoughness"]["baseColorTexture"] = {
          "index": len(self.gltf["textures"]) - 1
      }

  def __encode_skeleton(self):
    if self.model is None:
      raise Exception("No model to encode")

    skeleton = self.model.skeleton

    if skeleton is None:
      return

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
        mtx = np.array(diff)
        loc, rot, sca = decompose_mtx(mtx)

      node_idx = self.__add_node(
          name=bone.name,
          translation=[loc[0], loc[1], loc[2]],
          rotation=[rot[0], rot[1], rot[2], rot[3]],
          scale=[sca[0], sca[1], sca[2]]
      )
      self.node_idx_to_mesh[node_idx] = bone
      joints.append(node_idx)

      if bone.parent is not None:
        parent_idx = self.node_name_to_node_idx[bone.parent.lower()]
        self.__add_node_children(parent_idx, node_idx)
      else:
        self.gltf["scenes"][0]["nodes"].append(node_idx)

      s = [item for row in bone.tm_inverse for item in row]

      skin_bytes.write(struct.pack('f'*len(s), *s))

    b = self.__add_buffer(skin_bytes)
    skin_accessor_idx = self.__add_accessor(
        b, 5126, len(skeleton.bones), "MAT4")

    self.gltf["skins"] = [{
        "inverseBindMatrices": skin_accessor_idx,
        "joints": joints
    }]

  def __encode_animation(self):
    if self.model is None:
      raise Exception("No model to encode")

    animation_groups = self.model.animations
    if len(animation_groups) == 0:
      return

    self.gltf["animations"] = []
    for animation_group_name in animation_groups:
      animation_gltf = {}
      if animation_group_name is not None:
        animation_gltf["name"] = animation_group_name
      animation_gltf["samplers"] = []
      animation_gltf["channels"] = []
      animation_group = animation_groups[animation_group_name]

      for animation in animation_group:
        node_idx = -1
        try:
          node_idx = self.node_name_to_node_idx[animation.mesh_name.lower(
          )]
        except:
          # print("No node named " + str(animation.mesh_name) + " found")
          continue
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

          animation_bytes.write(struct.pack(
              'f'*len(keyframes), *keyframes))
          animation_bytes.write(
              struct.pack('f'*len(values), *values))

          b = self.__add_buffer(animation_bytes)
          a_input = self.__add_accessor(b, 5126, len(sub), "SCALAR")
          a_output = self.__add_accessor(b, 5126, len(
              sub), output_types[idx], byte_offset=len(keyframes) * 4)

          animation_gltf["samplers"].append({
              "input": a_input,
              "interpolation": "LINEAR",
              "output": a_output
          })
          sampler_idx = len(animation_gltf["samplers"]) - 1
          animation_gltf["channels"].append({
              "sampler": sampler_idx,
              "target": {
                  "node": node_idx,
                  "path": path_names[idx]
              }
          })
      if len(animation_gltf["samplers"]) != 0:
        self.gltf["animations"].append(animation_gltf)
    if len(self.gltf["animations"]) == 0:
      del self.gltf["animations"]

  def __encode_mesh(self):
    if self.model is None:
      raise Exception("No model to encode")

    meshes = self.model.geometry.meshes

    for mesh in meshes:
      mesh_gltf = {
          "name": mesh.name,
          "primitives": []
      }

      material = self.model.geometry.materials[mesh.material_index]

      joints_accessors = self.__add_accessors_split_four(
          mesh.joints, 5123)
      weights_accessors = self.__add_accessors_split_four(
          mesh.weights, 5126)
      vertices_accesors = self.__add_accessors_vertices(mesh.vertices)

      for k in mesh.indices:
        i = int(k)
        primitive = {}
        primitive["mode"] = 4
        primitive["attributes"] = {}

        primitive["attributes"]["NORMAL"] = vertices_accesors["normal"]
        primitive["attributes"]["POSITION"] = vertices_accesors["position"]
        primitive["attributes"]["TEXCOORD_0"] = vertices_accesors["textcoord"]

        indices = mesh.indices[k]
        indices_parts = len(indices)
        indices_buffer = self.__add_indices_buffer(indices)
        indices_accessor = self.__add_accessor(
            indices_buffer, 5123, indices_parts, "SCALAR")
        primitive["indices"] = indices_accessor

        # TODO: Check how submaterial affect this
        for idx, a in enumerate(joints_accessors):
          primitive["attributes"]["JOINTS_" + str(idx)] = a

        # TODO: Check how submaterial affect this
        for idx, a in enumerate(weights_accessors):
          primitive["attributes"]["WEIGHTS_" + str(idx)] = a

        if material is not None:
          primitive["material"] = self.geo_material_idx_to_gltf_material_idx[mesh.material_index] + i

        mesh_gltf["primitives"].append(primitive)

      self.gltf["meshes"].append(mesh_gltf)

      if len(joints_accessors) > 0 and len(weights_accessors) > 0:
        node_idx = self.__add_node(
            name=mesh.name,
            mesh=len(self.gltf["meshes"]) - 1,
            skin=0 if "skins" in self.gltf else None
        )
        self.node_idx_to_mesh[node_idx] = mesh
      else:
        tm = np.array(mesh.tm).T
        mtx = np.array(tm)

        if not is_string_empty(mesh.parent):
          try:
            # Fix to change global transformation to local transformation
            parent_idx = self.node_name_to_node_idx[mesh.parent.lower()]
            parent = self.node_idx_to_mesh[parent_idx]
            ntm = np.array(parent.tm).T
            ptm = np.array(ntm)
            pivot = np.linalg.inv(ptm)
            diff = np.matmul(pivot, tm)
            mtx = np.array(diff)
          except Exception as e:
            raise Exception(
                f"Unable to find parent mesh named: {e}")

        loc, rot, sca = decompose_mtx(mtx)
        node_idx = self.__add_node(
            name=mesh.name,
            mesh=len(self.gltf["meshes"]) - 1,
            translation=[loc[0], loc[1], loc[2]],
            rotation=[rot[0], rot[1], rot[2], rot[3]],
            scale=[sca[0], sca[1], sca[2]]
        )
        self.node_idx_to_mesh[node_idx] = mesh

        if not is_string_empty(mesh.parent):
          parent_idx = self.node_name_to_node_idx[mesh.parent.lower(
          )]
          self.__add_node_children(parent_idx, node_idx)

      if is_string_empty(mesh.parent):
        self.gltf["scenes"][0]["nodes"].append(
            len(self.gltf["nodes"]) - 1)

  def __add_accessors_vertices(self, vertices):
    position_bytes = io.BytesIO()
    normal_bytes = io.BytesIO()
    texcoord_bytes = io.BytesIO()

    first_vertex = True
    for v in vertices:
      p = [v.position[0], v.position[1], v.position[2]]
      if first_vertex:
        p_min = list(v.position)
        p_max = list(v.position)
        first_vertex = False
      else:
        p_min = [
            min(p_min[0], v.position[0]),
            min(p_min[1], v.position[1]),
            min(p_min[2], v.position[2]),
        ]
        p_max = [
            max(p_max[0], v.position[0]),
            max(p_max[1], v.position[1]),
            max(p_max[2], v.position[2]),
        ]
      position_bytes.write(struct.pack('f'*len(p), *p))
      n = [v.normal[0], v.normal[1], v.normal[2]]
      normal_bytes.write(struct.pack('f'*len(n), *n))
      t = [v.texcoord[0], v.texcoord[1]]
      texcoord_bytes.write(struct.pack('f'*len(t), *t))

    b = self.__add_buffer(position_bytes)
    p_a = self.__add_accessor(b, 5126, len(
        vertices), "VEC3", min=p_min, max=p_max)
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

  def __add_node(self, name=None, mesh=None, skin=None, translation=None, rotation=None, scale=None):
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
        print("Node name duplicate detected: " + str(key))
      self.node_name_to_node_idx[key] = idx
    return idx

  def __add_node_children(self, parent_idx, child_idx):
    node = self.gltf["nodes"][parent_idx]
    if "children" not in node:
      node["children"] = []
    node["children"].append(child_idx)

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

  def __add_accessor(self, buffer_view_idx, component_type, count, type, byte_offset=0, min=None, max=None):
    accessor = {
        "bufferView": buffer_view_idx,
        "byteOffset": byte_offset,
        "componentType": component_type,
        "count": count,
        "type": type
    }
    if min is not None:
      accessor["min"] = min
    if max is not None:
      accessor["max"] = max
    self.gltf["accessors"].append(accessor)
    return len(self.gltf["accessors"]) - 1

  def __add_accessors_split_four(self, data, component_type):
    data_bytes = self.__split_by_fours(data)
    data_max_length = 8  # TODO
    accessors = []

    t = None
    if component_type == 5123:
      t = 'H'
    if component_type == 5126:
      t = 'f'
    if t is None:
      raise Exception("Unsupported component type: " +
                      str(component_type))

    for i in range(data_max_length):
      is_empty = True
      w_bytes = io.BytesIO()
      for weight in data_bytes:
        w = [0, 0, 0, 0]
        if len(weight) > i:
          w = weight[i]
          is_empty = False
        w_bytes.write(struct.pack(t * len(w), *w))
      if is_empty:
        break
      b = self.__add_buffer(w_bytes)
      accessors.append(self.__add_accessor(
          b, component_type, len(data_bytes), "VEC4"))
    return accessors

  def __split_by_fours(self, data):
    data_bytes = []
    for d in data:
      parts = []
      num_parts = math.ceil(len(d) / 4)
      for i in range(num_parts):
        flattened = [0, 0, 0, 0]
        for j in range(4):
          idx = j + (i * 4)
          if len(d) > idx:
            flattened[j] = d[idx]
        parts.append(flattened)
      data_bytes.append(parts)
    return data_bytes
