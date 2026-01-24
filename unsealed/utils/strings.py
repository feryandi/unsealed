import os


def is_valid_ascii_letter(c):
  return c > 20 and c < 128


def is_string_empty(string):
  return string is None or not string.strip()


def find_correct_path(path):
  """
  Try to find a file with different case variations.
  Works cross-platform (Windows, Linux, macOS).
  """
  # Normalize the path to use os-specific separators
  path = os.path.normpath(path)

  # Split into directory and filename
  root_path = os.path.dirname(path)
  full_filename = os.path.basename(path)

  # If root_path is empty, use current directory
  if not root_path:
    root_path = '.'

  # Split filename and extension
  if '.' in full_filename:
    parts = full_filename.rsplit('.', 1)
    filename = parts[0]
    ext = parts[1]
  else:
    filename = full_filename
    ext = ''

  # Generate case variations
  combinations = [
      filename,
      filename.lower(),
      filename.upper(),
      filename.capitalize(),
      '_'.join(x.capitalize() if x else '_' for x in filename.split('_'))
  ]

  # Try each combination
  for combination in combinations:
    if ext:
      try_filename = combination + '.' + ext
    else:
      try_filename = combination

    try_path = os.path.join(root_path, try_filename)

    if os.path.isfile(try_path):
      return try_path

  # If nothing found, return original path
  return path
