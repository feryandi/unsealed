from io import BytesIO
from PIL import Image
from pathlib import Path
from ..formats.tex.format import SealTextureFormat
from ..formats.blob.format import BlobFormat


class TexturePipeline:
  def run(self, filepath: Path, output_dir: Path, convert_to: str | None = None) -> None:
    tex_format = SealTextureFormat()
    potential_tex_types = [
      ".tex",
      ".te1",
    ]

    for tex_types in potential_tex_types:
      path = filepath.with_suffix(tex_types)
      if path.is_file():
        texture_blob = tex_format.decode(path)

        try:
          if convert_to and texture_blob.value and texture_blob.filename:
            texture_bytes = BytesIO(texture_blob.value)
            im = Image.open(texture_bytes)

            png_stream = BytesIO()
            im.save(png_stream, format=convert_to.upper())
            texture_blob.value = png_stream.getvalue()
            texture_blob.extension = convert_to.lower()
        except Exception:
          raise Exception(f"Failed to convert texture to {convert_to}")

        blob_format = BlobFormat()
        blob_format.encode(texture_blob, output_dir)
        return

    raise Exception(f"File not found: {filepath}")
