import os


def is_valid_ascii_letter(c):
  return c > 20 and c < 128


def is_string_empty(string):
  return string is None or not string.strip()


# TODO: Put this somewhere else
def find_correct_path(path):
  full_filename = (os.path.basename(path)).split('.')
  filename = full_filename[0]
  ext = full_filename[1]
  root_path = os.path.dirname(path)

  combinations = [filename, filename.lower(), filename.upper(), filename.capitalize(), '_'.join(x.capitalize() or '_' for x in filename.split('_'))]

  for combination in combinations:
    try_path = root_path + '/' + combination + '.' + ext
    print(try_path)
    if not os.path.isfile(try_path):
      continue
    return try_path
  return path
