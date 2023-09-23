import os

from PIL import Image

from decoder.act.file import SealActionFileDecoder
from decoder.an1.file import SealAnimationFileDecoder
from decoder.bn1.file import SealBoneFileDecoder
from decoder.ms1.file import SealMeshFileDecoder
from decoder.tex.file import SealTextureFileDecoder
from encoder.obj import ObjEncoder
from encoder.gltf.gltf import GLTF

from model.model import Model


root_path = "/home/feryandi/repositories/unsealed"
filename = "N_arus" # TODO: submaterial (2) is not working
# filename = "N_elis" # TODO: submaterial (2) is not working
# filename = "T_bya" # TODO: act decoder is not working
filename = "N_seit_new_stand" # TODO: submaterial (3) is not working
# filename = "house_madelin_bank"
model = Model()


def process_texture(bitmap):
  if bitmap is None:
    return

  texture_filename = bitmap.split('.')[0]
  texture_path = root_path + '/tests/input/' + texture_filename + '.tex'
  if not os.path.isfile(texture_path):
    texture_path = root_path + '/tests/input/' + texture_filename.lower() + '.tex'
    if not os.path.isfile(texture_path):
      print("Cannot found texture: " + bitmap)
      return
  texture_decoder = SealTextureFileDecoder(texture_path)
  texture = texture_decoder.decode() # TODO: This still returns the decoder

  # TODO: Streamline this to the pipeline?
  file_type = texture.file_type
  file_type = 'tga' # TODO
  texture_path = root_path + '/tests/output/' + texture.filename
  with open(texture_path + '.' + file_type, "wb") as f:
    f.write(texture.decoded)
  with Image.open(texture_path + '.' + file_type) as im:
    im.save(texture_path + '.png')


## DECODERS
geometry_decoder = SealMeshFileDecoder(root_path + '/tests/input/' + filename + '.ms1')
geometry = geometry_decoder.decode()
model.add_geometry(geometry)

action_filepath = root_path + '/tests/input/' + filename + '.act'
if os.path.isfile(action_filepath):
  action_decoder = SealActionFileDecoder(action_filepath)
  actions = action_decoder.decode()
else:
  actions = [{
    "name": "default",
    "filename": filename
  }]

for action in actions:
  ani_name = action["name"]
  ani_filename = action["filename"]
  path = root_path + '/tests/input/' + ani_filename + '.an1'
  if os.path.isfile(path):
    animation_decoder = SealAnimationFileDecoder(path)
    animations = animation_decoder.decode()
    for animation in animations:
      geometry.add_animation(animation)
      model.add_animation(ani_name, animation)

bone_path = root_path + '/tests/input/' + filename + '.bn1'
if os.path.isfile(bone_path):
  skeleton_decoder = SealBoneFileDecoder(bone_path)
  skeleton = skeleton_decoder.decode()
  model.add_skeleton(skeleton)

print(model.geometry.materials)
for material in model.geometry.materials:
  process_texture(material.bitmap)
  for submaterial in material.sub_materials:
    process_texture(submaterial.bitmap)

## ENCODERS
obj_encoder = ObjEncoder(geometry)
obj_encoder.encode(root_path + '/tests/output/' + filename + '.obj')

gltf2_encoder = GLTF()
for mesh in geometry.meshes:
  print(mesh.name)
  if mesh.material_index is not None:
    gltf2_encoder.add_mesh(mesh, material = geometry.materials[mesh.material_index])
  else:
    gltf2_encoder.add_mesh(mesh)
for material in geometry.materials:
  gltf2_encoder.add_material(material)
if model.skeleton is not None:
  gltf2_encoder.add_skin(model.skeleton)
  # TODO: Fix
  for mesh in geometry.meshes:
    gltf2_encoder.fix_hack_mesh_with_bone_parent(mesh, model.skeleton)
for name in model.animations:
  gltf2_encoder.add_animation(model.animations[name])
gltf2_encoder.encode(root_path + '/tests/output/' + filename)
