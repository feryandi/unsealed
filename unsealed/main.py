import os

from PIL import Image

from decoder.act.file import SealActionFileDecoder
from decoder.an1.file import SealAnimationFileDecoder
from decoder.bn1.file import SealBoneFileDecoder
from decoder.ms1.file import SealMeshFileDecoder
from decoder.tex.file import SealTextureFileDecoder
from decoder.map.file import SealMapFileDecoder
from decoder.mdt.file import SealMdtFileDecoder
from encoder.gltf.gltf import GLTF
from encoder.heightmap.file import HeightmapEncoder

from model.model import Model
from utils.strings import find_correct_path


root_path = "/home/feryandi/repositories/unsealed"
output_path = "/tests/output/"
output_path = "/web/output/"
filename = "T_bya" # TODO: splitting to subobject still not fixing texture issue
filename = "house_madelin_bank" # TODO: fail to get bg_madelin_bank_window.png, where is it?
filenames = [
  "N_adelA",   # TODO: Some node are not found (foot)
  "N_adhB",  # TODO: splitting to subobject still not fixing texture issue
  "N_adrian",   # TODO: Meshes cannot be triangles, Texture messed up
  "N_adrian_stand",  # TODO: Some node are not found (foot)
]
filenames = [
  "Bomberman_1_dd",
  "G_flame_dragon",
  "G_dark_leopard_stand",
  "G_Unicon",
]
filenames = [
  "gourmet_tower_01",
  "gourmet_flower_01",
  "house_adel_a000",
  "hosue_raim_stage_0",
]
filenames = [
  "G_Rainbow_Hoverboard_fw",
]
filenames = [
  "house_elim_tutorial",
]
filenames = ["object_grass_s_01", "object_warpzone", "house_elim_church", "house_elim_traintown", "house_elim_sorcery", "house_poor_bookstore", "house_elim_c000", "house_elim_c001", "house_elim_c002", "house_elim_c003", "house_elim_bank", "house_elim_c004", "object_elim_fence_000", "object_elim_fence_001", "object_elim_fence_002", "object_elim_fence_003", "object_elim_fence_004", "object_elim_castledoor_c001", "object_elim_castlewall_c000", "object_elim_castletower_c001", "object_elim_castletower_c000", "object_elim_castledoor_c000", "house_elim_c005", "house_elim_c006", "house_elim_c007", "house_elim_c008", "house_elim_c009", "house_elim_c010", "house_elim_c011", "house_elim_c012", "house_elim_d000", "house_elim_itemshop", "house_elim_knighthall", "house_elim_travel", "house_elim_weaponshop", "object_elim_flowergarden_00", "object_elim_flowergarden_01", "object_elim_flowergarden_02", "object_elim_tree_e001", "object_elim_tree_e002", "object_elim_tree_e003", "object_elim_tree_e004", "object_elim_tree_e005", "object_elim_lamp_000", "object_elim_lamp_001", "object_a00_bench_000", "object_elim_castlewall_c001", "object_box_000", "house_elim_trainingtower", "object_elim_castlewall_c003", "object_elim_castlewall_c002", "object_elim_underdoor_c000", "object_elim_emblem_00", "object_elim_emblem_01", "object_elim_bench_e000", "object_elim_bench_e001", "house_elim_arena", "object_elim_bridge_00", "object_elim_bridge_01", "object_elim_bridge_02", "object_elim_streettree_e001", "object_elim_streettree_e002", "house_elim_gypsi", "house_elim_bookstore", "house_elim_booth", "object_elim_flowerbed_e001", "object_elim_flowerbed_e002", "object_elim_blockfence_00", "object_elim_blockfence_01", "object_elim_blockfence_02", "house_elim_c015", "house_elim_c014", "house_elim_c013", "object_elim_houseflowergarden_e001", "object_elim_houseflowergarden_e002", "object_elim_streettree_e003", "object_elim_streettree_e005", "object_elim_streettree_e004", "object_elim_streettree_e006", "object_elim_flowerbed_e003", "object_elim_flowerbed_e004", "object_elim_flowergarden_e000", "object_elim_flowergarden_e001", "elim_picket_y001", "house_poor_bank", "house_elim_trainning_tower_y000", "house_elim_drinkshop", "house_elim_request", "house_elim_lions", "object_elim_flowergarden_e002", "object_elim_fountain", "object_elim_carriage_001", "house_elimcastle", "object_elim_bridge_03", "object_tree_temperate_e000", "object_tree_temperate_e004", "object_tree_temperate_b001", "object_tree_temperate_b002", "object_tree_temperate_e001", "object_tree_temperate_e003", "object_field_tree_c003", "object_field_tree_01", "object_field_tree_02", "object_field_tree_c002", "object_tree_000", "object_grass_s_03", "object_grass_s_00", "object_grass_s_02", "object_grass_so_002", "object_grass_so_000", "object_grass_so_001", "object_tree_strange_011", "object_tree_strange_001", "object_tree_strange_002", "object_tree_strange_003", "object_tree_strange_005", "object_tree_strange_006", "object_tree_strange_007", "object_tree_strange_008", "object_a00_stone_007", "object_a00_stone_001", "object_a00_stone_002", "object_a00_stone_005", "object_a00_stone_006", "house_elim_tutorial"]
# filenames = ["object_elim_castlewall_c000"]
filenames = ["house_poor_arena"]
filenames = ["object_madelin_tree_y003"]
filenames = ["house_poor_bank"]
filenames = ["object_warpzones"]
model = Model()


# Experiment: Map File
# for i in range(1, 582):
#   map_path = root_path + '/tests/input/' + str(i) + '.map'
#   if os.path.isfile(map_path):
#     map_decoder = SealMapFileDecoder(map_path)
#     m = map_decoder.decode()

map_num = 1 # End's Land
map_num = 540
map_num = 32 # Elim
# map_num = 216
# map_num = 22 # Madelin
# map_num = 2 # Zaid
# map_num = 11 # Lime

map_path = root_path + '/tests/input/' + str(map_num) + '.map'
map_decoder = SealMapFileDecoder(map_path)
terrain = map_decoder.decode()

mdt_path = root_path + '/tests/input/' + str(map_num) + '.mdt'
mdt_decoder = SealMdtFileDecoder(mdt_path, root_path + output_path)
m = mdt_decoder.decode()

map_data_path = root_path + output_path + 'map_data.' + str(map_num)
with open(map_data_path + '.json', "w") as f:
  f.write(terrain.to_json())


def decode_texture(bitmap):
  if bitmap is None:
    return True

  texture_filename = bitmap.split('.')[0]
  texture_path = root_path + '/tests/input/' + texture_filename + '.tex'
  texture_path = find_correct_path(texture_path)
  if not os.path.isfile(texture_path):
    return False
  texture_decoder = SealTextureFileDecoder(texture_path)
  texture = texture_decoder.decode() # TODO: This still returns the decoder

  # TODO: Streamline this to the pipeline?
  file_type = texture.file_type
  file_type = 'tga' # TODO
  texture_path = root_path + output_path + texture.filename
  with open(texture_path + '.' + file_type, "wb") as f:
    f.write(texture.decoded)
  with Image.open(texture_path + '.' + file_type) as im:
    im.save(texture_path + '.png')
  return True


def decode_mesh(filename):
  # Decode ms1
  geometry_decoder = SealMeshFileDecoder(root_path + '/tests/input/' + filename + '.ms1')
  geometry = geometry_decoder.decode()
  model.add_geometry(geometry)

  # Decode act
  action_filepath = root_path + '/tests/input/' + filename + '.act'
  if os.path.isfile(action_filepath):
    action_decoder = SealActionFileDecoder(action_filepath)
    actions = action_decoder.decode()
  else:
    actions = [{
      "name": "default",
      "filename": filename
    }]

  # Decode an1
  for action in actions:
    ani_name = action["name"]
    ani_filename = action["filename"]
    path = root_path + '/tests/input/' + ani_filename + '.an1'
    print(path)
    if os.path.isfile(path):
      print("add anims")
      print(os.path.isfile(path))
      animation_decoder = SealAnimationFileDecoder(path)
      animations = animation_decoder.decode()
      for animation in animations:
        print("add anima")
        geometry.add_animation(animation)
        model.add_animation(ani_name, animation)

  # Decode bn1
  bone_path = root_path + '/tests/input/' + filename + '.bn1'
  if os.path.isfile(bone_path):
    skeleton_decoder = SealBoneFileDecoder(bone_path)
    skeleton = skeleton_decoder.decode()
    model.add_skeleton(skeleton)

  # Decode tex
  for material in model.geometry.materials:
    decode_texture(material.bitmap)
    for submaterial in material.sub_materials:
      decode_texture(submaterial.bitmap)

  return model


def extract_mesh(filename):
  model = decode_mesh(filename)
  gltf2_encoder = GLTF()
  gltf2_encoder.encode(model, root_path + output_path + filename)


for object_file in terrain.object_files:
  print("Extracting: " + object_file)
  try:
    extract_mesh(object_file.split('.')[0])
  except:
    print("Failed to extract: " + object_file)

# # # Testing
# for filename in filenames:
#   print("Extracting: " + filename)
#   extract_mesh(filename)
