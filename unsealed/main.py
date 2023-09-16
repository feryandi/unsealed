from PIL import Image

from decoder.an1.file import SealAnimationFileDecoder
from decoder.bn1.file import SealBoneFileDecoder
from decoder.ms1.file import SealMeshFileDecoder
from decoder.tex.file import SealTextureFileDecoder
from encoder.obj import ObjEncoder
from encoder.gltf.gltf import GLTF

from model.model import Model


root_path = "/home/feryandi/repositories/unsealed"
filename = "T_Festive_Piya"
model = Model()

## DECODERS
geometry_decoder = SealMeshFileDecoder(root_path + '/tests/input/' + filename +'.ms1')
geometry = geometry_decoder.decode()
model.add_geometry(geometry)

animation_decoder = SealAnimationFileDecoder(root_path + '/tests/input/' + filename +'.an1')
animations = animation_decoder.decode()
for animation in animations:
  geometry.add_animation(animation)
  model.add_animation(filename, animation) # TODO

skeleton_decoder = SealBoneFileDecoder(root_path + '/tests/input/' + filename +'.bn1')
skeleton = skeleton_decoder.decode()
model.add_skeleton(skeleton)

texture_decoder = SealTextureFileDecoder(root_path + '/tests/input/' + filename +'.tex')
texture = texture_decoder.decode() # TODO: This still returns the decoder

# TODO: Streamline this to the pipeline?
file_type = texture.file_type
file_type = 'tga' # TODO
texture_path = root_path + '/tests/output/' + texture.filename
with open(texture_path + '.' + file_type, "wb") as f:
  f.write(texture.decoded)
with Image.open(texture_path + '.' + file_type) as im:
  im.save(texture_path + '.png')

## ENCODERS
obj_encoder = ObjEncoder(geometry)
obj_encoder.encode(root_path + '/tests/output/' + filename + '.obj')

gltf2_encoder = GLTF()
for mesh in geometry.meshes:
  gltf2_encoder.add_mesh(mesh)
for material in geometry.materials:
  gltf2_encoder.add_material(material)
  break
gltf2_encoder.add_skin(model.skeleton)
for name in model.animations:
  gltf2_encoder.add_animation(model.animations[name])
gltf2_encoder.encode(root_path + '/tests/output/' + filename)

print(model)
