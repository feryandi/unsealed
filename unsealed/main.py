import os
import json
from PIL import Image

from decoder.act.file import SealActorFileDecoder
from decoder.an1.file import SealAnimationFileDecoder
from decoder.bn1.file import SealBoneFileDecoder
from decoder.ms1.file import SealMeshFileDecoder
from decoder.tex.file import SealTextureFileDecoder
from decoder.map.file import SealMapFileDecoder
from decoder.mdt.file import SealMdtFileDecoder
from decoder.spr.file import SealSprFileDecoder
from encoder.gltf import GLTF
from encoder.glb import GLB
from encoder.heightmap import HeightmapEncoder

from model.model import Model
from actor.actor import SealActor
from actor.action import SealAction
from utils.strings import find_correct_path
import base64
import gzip


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
    texture_path = os.path.join(search_dir, texture_filename + '.te1')
    texture_path = find_correct_path(texture_path)
    if not os.path.isfile(texture_path):
      print(f"Error: Texture file not found: {texture_path}")
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


def decode_sprite(files, search_dir, output_path):
  """Decode sprite file from tex file"""

  for filename, data in files:
    result = decode_texture(filename, search_dir, output_path)
    if not result:
      print(f"Warning: Unable to decode texture for sprite: {filename}")
      continue

    texture_filename = filename.split('.')[0]
    texture_path = os.path.join(output_path, texture_filename + '.png')
    with Image.open(os.path.join(output_path, texture_path)) as im:
      for idx, (a, b, c, d) in enumerate(data):
        sprite = im.crop((a, c, b, d))
        sprite_output_path = os.path.join(
            output_path, f"{filename}_sprite_{idx}.png")
        sprite.save(sprite_output_path)

  return True


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

  # Also try to process same-named .tex and .mdt files for richer map rendering
  tex_path = os.path.join(search_dir, filename + '.tex')
  tex_path = find_correct_path(tex_path)
  if os.path.isfile(tex_path):
    try:
      process_tex(tex_path, output_path)
    except Exception as e:
      print(f"Warning: Failed to process texture {tex_path}: {e}")

  mdt_path = os.path.join(search_dir, filename + '.mdt')
  if os.path.isfile(mdt_path):
    try:
      process_mdt(mdt_path, output_path)
    except Exception as e:
      print(f"Warning: Failed to process mdt {mdt_path}: {e}")

  if not os.path.exists(output_path):
    os.makedirs(output_path)
  map_data_path = os.path.join(output_path, 'map_data.' + filename + '.json')

  # Also produce a PNG heightmap for reference (optional)
  try:
    png_path = os.path.join(output_path, filename + '.heightmap.png')
    heightmap = HeightmapEncoder(terrain)
    heightmap.encode(png_path)
    print(f"Successfully exported heightmap to: {png_path}.png")
  except Exception:
    pass

  object_files = getattr(terrain, "object_files", [])
  print(f"\nFound {len(object_files)} objects in the map")

  embedded_glbs = []
  for object_file in object_files:
    object_name = object_file.split('.')[0]
    try:
      model = decode_mesh(object_name, search_dir, output_path)
      # write glTF (existing behaviour)
      gltf2_encoder = GLTF()
      dest = os.path.join(output_path, object_name)
      gltf2_encoder.encode(model, dest)
      # also write GLB for embedding and faster loading
      try:
        glb_encoder = GLB(model)
        glb_encoder.encode(dest)
      except Exception:
        # if GLB encoding fails, continue without GLB
        pass

      # if a .glb exists, embed it now
      glb_path = os.path.join(output_path, object_name + '.glb')
      if os.path.isfile(glb_path):
        try:
          with open(glb_path, 'rb') as gf:
            gb = gf.read()
          embedded_glbs.append({
              'name': object_name,
              'filename': os.path.basename(glb_path),
              'data_b64': base64.b64encode(gb).decode('ascii')
          })
        except Exception:
          pass
    except Exception as e:
      print(f"Failed to extract {object_name}: {str(e)}")

  # After object extraction, assemble final JSON with embedded assets
  try:
    data = terrain.to_serializable()

    embedded_textures = []
    for tex in getattr(terrain, 'textures', []) or []:
      if not tex:
        continue
      tex_name = tex.split('.')[0]
      for ext in ('.dds', '.tga', '.png'):
        p = os.path.join(output_path, tex_name + ext)
        p = find_correct_path(p)
        if os.path.isfile(p):
          try:
            with open(p, 'rb') as tf:
              b = tf.read()
            embedded_textures.append({
                'name': tex_name,
                'filename': os.path.basename(p),
                'ext': ext.lstrip('.'),
                'data_b64': base64.b64encode(b).decode('ascii')
            })
          except Exception:
            pass
          break

    embedded_lightmap = None
    lm = getattr(terrain, 'lightmap', None)
    if lm:
      lm_name = lm.split('.')[0]
      for ext in ('.dds', '.tga', '.png'):
        p = os.path.join(output_path, lm_name + ext)
        p = find_correct_path(p)
        if os.path.isfile(p):
          try:
            with open(p, 'rb') as lf:
              b = lf.read()
            embedded_lightmap = {
                'name': lm_name,
                'filename': os.path.basename(p),
                'ext': ext.lstrip('.'),
                'data_b64': base64.b64encode(b).decode('ascii')
            }
          except Exception:
            embedded_lightmap = None
          break

    if embedded_textures:
      data['embedded_textures'] = embedded_textures
    if embedded_lightmap:
      data['embedded_lightmap'] = embedded_lightmap
    if embedded_glbs:
      data['embedded_glbs'] = embedded_glbs

    # write both plain JSON and gzipped JSON for compatibility and smaller transfer
    json_text = json.dumps(data)
    with open(map_data_path, 'w', encoding='utf-8') as f:
      f.write(json_text)
    # gzipped version
    try:
      gz_path = map_data_path + '.gz'
      with gzip.open(gz_path, 'wb') as gz:
        gz.write(json_text.encode('utf-8'))
    except Exception:
      pass
    print(f"Successfully exported map JSON to: {map_data_path} (and .gz)")
  except Exception as e:
    print(f"Failed to write map JSON: {e}")


def process_mdt(filepath, output_path):
  """Process MDT file."""
  print(f"Processing MDT file: {filepath}")

  mdt_decoder = SealMdtFileDecoder(filepath)
  files = mdt_decoder.decode()

  for filename, data in files:
    output_file_path = os.path.join(output_path, filename)
    with open(output_file_path, "wb") as f:
      f.write(data)

  print(f"Extracted {len(files)} files from the MDT file")


def process_spr(filepath, output_path):
  """Process SPR file."""
  print(f"Processing SPR file: {filepath}")

  decoder = SealSprFileDecoder(filepath)
  files = decoder.decode()

  decode_sprite(files, os.path.dirname(filepath), output_path)
  print(f"Extracted {len(files)} sprites from the SPR file")


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
  print("- .spr (Sprite files)")
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
      elif file_type == 'tex' or (file_type is None and os.path.isfile(filepath + '.tex')) or \
              file_type == 'te1' or (file_type is None and os.path.isfile(filepath + '.te1')):
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
      elif file_type == 'spr' or (file_type is None and os.path.isfile(filepath + '.spr')):
        if file_type is None:
          filepath = filepath + '.spr'
        process_spr(filepath, output_path)
      else:
        print(f"Error: Unsupported file: {filename}")
    except Exception as e:
      print(f"An error occurred: {e}")
      import traceback
      traceback.print_exc()


if __name__ == "__main__":
  main()
