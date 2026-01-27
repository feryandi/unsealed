import os
from PIL import Image

from decoder.act.file import SealActorFileDecoder
from decoder.an1.file import SealAnimationFileDecoder
from decoder.bn1.file import SealBoneFileDecoder
from decoder.ms1.file import SealMeshFileDecoder
from decoder.tex.file import SealTextureFileDecoder
from decoder.map.file import SealMapFileDecoder
from decoder.mdt.file import SealMdtFileDecoder
from encoder.gltf import GLTF
from encoder.glb import GLB
from encoder.heightmap import HeightmapEncoder

from model.model import Model
from actor.actor import SealActor
from actor.action import SealAction
from utils.strings import find_correct_path


def get_file_type(filename):
  """Extract file extension from filename."""
  if '.' in filename:
    return filename.split('.')[-1].lower()
  return None


def decode_texture(bitmap, search_dir, output_path):
  """Decode texture file and convert to PNG."""
  if bitmap is None:
    return True

  texture_filename = bitmap.split('.')[0]
  texture_path = os.path.join(search_dir, texture_filename + '.tex')
  texture_path = find_correct_path(texture_path)

  if not os.path.isfile(texture_path):
    print(f"Warning: Texture file not found: {texture_path}")
    return False

  texture_decoder = SealTextureFileDecoder(texture_path)
  texture = texture_decoder.decode()

  file_type = 'tga'
  # Use os.path.join for cross-platform compatibility
  full_output_dir = output_path
  if not os.path.exists(full_output_dir):
    os.makedirs(full_output_dir)

  texture_out_path = os.path.join(full_output_dir, texture.filename)

  with open(texture_out_path + '.' + file_type, "wb") as f:
    if texture.decoded is None:
      print(f"Error: Texture data is empty for: {texture.filename}")
      return False
    f.write(texture.decoded)
  with Image.open(texture_out_path + '.' + file_type) as im:
    im.save(texture_out_path + '.png')
  return True


def decode_actor(filename, search_dir, output_path):
  """Decode actor file with all related files (ms1, an1, bn1, tex)."""

  actor = SealActor("default", filename)
  actor_filepath = os.path.join(search_dir, filename + '.act')
  if os.path.isfile(actor_filepath):
    actor_decoder = SealActorFileDecoder(actor_filepath)
    actor_decoded = actor_decoder.decode()
    if actor_decoded is not None:
      actor = actor_decoded

  model = decode_mesh(actor.filename, search_dir, output_path, actor.actions)
  return model


def decode_mesh(filename, search_dir, output_path, actions=[]):
  model = Model()

  # Decode ms1
  geometry_decoder = SealMeshFileDecoder(
      os.path.join(search_dir, filename + '.ms1'))
  geometry = geometry_decoder.decode()
  model.add_geometry(geometry)

  # Decode an1
  if len(actions) == 0:
    actions = [SealAction("default", filename)]
  for action in actions:
    ani_name = action.name
    ani_filename = action.filename
    path = os.path.join(search_dir, ani_filename + '.an1')
    if os.path.isfile(path):
      animation_decoder = SealAnimationFileDecoder(path)
      animations = animation_decoder.decode()
      for animation in animations:
        geometry.add_animation(animation)
        model.add_animation(ani_name, animation)

  # Decode bn1
  bone_path = os.path.join(search_dir, filename + '.bn1')
  if os.path.isfile(bone_path):
    skeleton_decoder = SealBoneFileDecoder(bone_path)
    skeleton = skeleton_decoder.decode()
    model.add_skeleton(skeleton)

  # Decode tex
  geometry_obj = getattr(model, 'geometry', None)
  if geometry_obj is not None and getattr(geometry_obj, 'materials', None):
    for material in geometry_obj.materials:
      if getattr(material, 'bitmap', None):
        decode_texture(material.bitmap, search_dir, output_path)
      for submaterial in getattr(material, 'sub_materials', []) or []:
        if getattr(submaterial, 'bitmap', None):
          decode_texture(submaterial.bitmap, search_dir, output_path)

  return model


def process_act(filepath, output_path):
  """Process ACT mesh file."""
  print(f"Processing ACT file: {filepath}")

  # Get the directory where the file is located and the base filename
  search_dir = os.path.dirname(os.path.abspath(filepath))
  filename = os.path.splitext(os.path.basename(filepath))[0]

  model = decode_actor(filename, search_dir, output_path)

  glb_encoder = GLB(model)
  dest = os.path.join(output_path, filename)
  glb_encoder.encode(dest)
  print(f"Successfully exported to: {dest}.glb")


def process_mesh(filepath, output_path):
  """Process MS1 mesh file."""
  print(f"Processing MS1 file: {filepath}")

  # Get the directory where the file is located and the base filename
  search_dir = os.path.dirname(os.path.abspath(filepath))
  filename = os.path.splitext(os.path.basename(filepath))[0]

  model = decode_mesh(filename, search_dir, output_path)

  glb_encoder = GLB(model)
  dest = os.path.join(output_path, filename)
  glb_encoder.encode(dest)
  print(f"Successfully exported to: {dest}.glb")


def process_tex(filepath, output_path):
  """Process TEX texture file."""
  print(f"Processing TEX file: {filepath}")

  search_dir = os.path.dirname(os.path.abspath(filepath))
  filename = os.path.splitext(os.path.basename(filepath))[0]

  texture_path = os.path.join(search_dir, filename + '.tex')
  texture_path = find_correct_path(texture_path)

  if not os.path.isfile(texture_path):
    print(f"Error: Texture file not found: {texture_path}")
    return

  texture_decoder = SealTextureFileDecoder(texture_path)
  texture = texture_decoder.decode()

  file_type = 'tga'
  if not os.path.exists(output_path):
    os.makedirs(output_path)

  output_texture_path = os.path.join(output_path, texture.filename)
  with open(output_texture_path + '.' + file_type, "wb") as f:
    if texture.decoded is None:
      print(f"Error: Texture data is empty for: {texture.filename}")
      return
    f.write(texture.decoded)
  with Image.open(output_texture_path + '.' + file_type) as im:
    im.save(output_texture_path + '.png')

  print(f"Successfully exported to: {output_texture_path}.png")


def process_map(filepath, output_path):
  """Process MAP terrain file."""
  print(f"Processing MAP file: {filepath}")

  search_dir = os.path.dirname(os.path.abspath(filepath))
  filename = os.path.splitext(os.path.basename(filepath))[0]

  map_path = os.path.join(search_dir, filename + '.map')
  map_path = find_correct_path(map_path)

  if not os.path.isfile(map_path):
    print(f"Error: Map file not found: {map_path}")
    return

  map_decoder = SealMapFileDecoder(map_path)
  terrain = map_decoder.decode()

  if terrain is None:
    print(f"Error: Failed to decode map: {map_path}")
    return

  if not os.path.exists(output_path):
    os.makedirs(output_path)

  map_data_path = os.path.join(output_path, filename + '.heightmap.png')
  heightmap = HeightmapEncoder(terrain)
  heightmap.encode(map_data_path)

  print(f"Successfully exported heightmap to: {map_data_path}.png")

  object_files = getattr(terrain, "object_files", [])
  print(f"\nFound {len(object_files)} objects in the map")
  for object_file in object_files:
    object_name = object_file.split('.')[0]
    try:
      model = decode_mesh(object_name, search_dir, output_path)
      gltf2_encoder = GLTF()
      dest = os.path.join(output_path, object_name)
      gltf2_encoder.encode(model, dest)
    except Exception as e:
      print(f"Failed to extract {object_name}: {str(e)}")


def process_mdt(filepath, output_path):
  """Process MDT file."""
  print(f"Processing MDT file: {filepath}")

  search_dir = os.path.dirname(os.path.abspath(filepath))
  filename = os.path.splitext(os.path.basename(filepath))[0]

  mdt_path = os.path.join(search_dir, filename + '.mdt')
  mdt_decoder = SealMdtFileDecoder(mdt_path)
  files = mdt_decoder.decode()

  for filename, data in files:
    output_file_path = os.path.join(output_path, filename)
    with open(output_file_path, "wb") as f:
      f.write(data)

  print(f"Extracted {len(files)} files from the MDT file")


def main():
  """Main function to handle user input and file processing."""
  root_path = os.getcwd()
  output_dir = "output"
  output_path = os.path.join(root_path, output_dir)

  print("\n")
  print("UNSEALED PROJECT")
  print("________________")
  print("\nSupported file types:")
  print("- .act (Actor files)")
  print("- .ms1 (Mesh files)")
  print("- .tex (Texture files)")
  print("- .map (Map files)")
  print("- .mdt (Archive files)")
  print("________________")

  while True:
    filename = input("\nEnter filepath (or 'quit' to exit): ").strip()

    if filename.lower() in ['quit', 'exit', 'q']:
      break

    if not filename:
      continue

    # Convert to absolute path
    if not os.path.isabs(filename):
      filepath = os.path.join(root_path, filename)
    else:
      filepath = filename

    file_type = get_file_type(filename)

    try:
      if file_type == 'act' or (file_type is None and os.path.isfile(filepath + '.act')):
        if file_type is None:
          filepath = filepath + '.act'
        process_act(filepath, output_path)
      elif file_type == 'ms1' or (file_type is None and os.path.isfile(filepath + '.ms1')):
        if file_type is None:
          filepath = filepath + '.ms1'
        process_mesh(filepath, output_path)
      elif file_type == 'tex' or (file_type is None and os.path.isfile(filepath + '.tex')):
        if file_type is None:
          filepath = filepath + '.tex'
        process_tex(filepath, output_path)
      elif file_type == 'map' or (file_type is None and os.path.isfile(filepath + '.map')):
        if file_type is None:
          filepath = filepath + '.map'
        process_map(filepath, output_path)
      elif file_type == 'mdt' or (file_type is None and os.path.isfile(filepath + '.mdt')):
        if file_type is None:
          filepath = filepath + '.mdt'
        process_mdt(filepath, output_path)
      else:
        print(f"Error: Unsupported file: {filename}")
    except Exception as e:
      print(f"An error occurred: {e}")
      import traceback
      traceback.print_exc()


if __name__ == "__main__":
  main()
