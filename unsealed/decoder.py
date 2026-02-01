from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from decoder.act.file import SealActorFileDecoder
from decoder.an1.file import SealAnimationFileDecoder
from decoder.bn1.file import SealBoneFileDecoder
from decoder.map.file import SealMapFileDecoder
from decoder.mdt.file import SealMdtFileDecoder
from decoder.ms1.file import SealMeshFileDecoder
from decoder.tex.file import SealTextureFileDecoder
from decoder.sfx.file import SealSfxFileDecoder
from decoder.spr.file import SealSprFileDecoder
from decoder.sha.file import SealShaFileDecoder
from decoder.mat.file import SealMatFileDecoder
from decoder.men.file import SealMenFileDecoder


def get_file_type(filename):
  """Extract file extension from filename."""
  if '.' in filename:
    return filename.split('.')[-1].lower()
  return None


def decode_file(filepath: str):
  """Detect file type and call the correct processor from `main`.

  If `filepath` has no extension, this will try common extensions
  (ms1, tex, map, mdt) by appending them and checking for file existence.
  """
  filepath = os.path.abspath(filepath)
  file_type = get_file_type(filepath)

  decoder = None
  if file_type == "act":
    decoder = SealActorFileDecoder(filepath)
  if file_type == "an1":
    decoder = SealAnimationFileDecoder(filepath)
  if file_type == "bn1":
    decoder = SealBoneFileDecoder(filepath)
  if file_type == "map":
    decoder = SealMapFileDecoder(filepath)
  if file_type == "mat":
    decoder = SealMatFileDecoder(filepath)
  if file_type == "mdt":
    decoder = SealMdtFileDecoder(filepath)
  if file_type == "men":
    decoder = SealMenFileDecoder(filepath)
  if file_type == "ms1":
    decoder = SealMeshFileDecoder(filepath)
  if file_type == 'sfx':
    decoder = SealSfxFileDecoder(filepath)
  if file_type == 'sha':
    decoder = SealShaFileDecoder(filepath)
  if file_type == 'spr':
    decoder = SealSprFileDecoder(filepath)
  if file_type == "tex":
    decoder = SealTextureFileDecoder(filepath)

  if decoder is not None:
    result = decoder.decode()
    return result

  print(f"Error: unsupported file type: {file_type}")
  return None


def main(argv: Optional[list[str]] = None):
  parser = argparse.ArgumentParser(description="Unsealed: Decoder CLI")
  parser.add_argument(
      "input", nargs="+", help="Path to a file")
  args = parser.parse_args(argv)

  for inp in args.input:
    try:
      decoded = decode_file(inp)
      print(f"Decoded file: {inp}")
      print(f"Decoded contents:")
      print(decoded)
    except Exception as e:
      print(f"Failed to process {inp}: {e}")
      import traceback
      traceback.print_exc()


if __name__ == "__main__":
  sys.exit(main())
