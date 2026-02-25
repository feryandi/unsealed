from pathlib import Path
from typing import Optional, Union


def is_valid_ascii_letter(c: int) -> bool:
  return c > 20 and c < 128


def is_string_empty(string: Optional[str]) -> bool:
  return string is None or not string.strip()


def find_correct_path(path_str: str) -> Union[Path, str]:
  """
  Finds a file with different case variations using pathlib.
  Works cross-platform (Windows, Linux, macOS).
  """
  original_path = Path(path_str)
  root_path = original_path.parent

  # Handle filename and extension separately
  # .stem is the filename without extension; .suffix is the extension
  filename = original_path.stem
  ext = original_path.suffix  # Includes the dot (e.g., '.txt')

  # Generate case variations for the filename
  combinations = [
    filename,
    filename.lower(),
    filename.upper(),
    filename.capitalize(),
    "_".join(x.capitalize() if x else "_" for x in filename.split("_")),
  ]

  # Try each combination
  for name_variant in combinations:
    # Reconstruct path using the / operator
    try_path = root_path / f"{name_variant}{ext}"

    if try_path.is_file():
      return Path(str(try_path))

  # Return original string if no variation is found
  return path_str
