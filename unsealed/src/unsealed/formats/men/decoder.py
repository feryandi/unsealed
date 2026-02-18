import json
from ...utils.file import File


class SealMenDecoder:
  def __init__(self, path):
    self.path = path
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open men file")

  def decode(self):
    """
    Decodes the MEN file
    """
    if self.file is None:
      raise Exception("File was not initialized properly")

    header_template = "Seal Online UI File v"
    version = 0
    header = self.file.read_string(64)
    if header is not None and header.startswith(header_template):
      # get version number from header, remove prefix
      version = int(header[len(header_template) :].strip())
      # TODO: Version 5: item_custome_buy
    else:
      self.file.reset()

    interface = {}

    spr_file = self.file.read_string(100)
    interface["spr"] = spr_file

    x = self.file.read_int()

    interface["elements"] = []

    while self.file.is_end() is False:
      interface["elements"].append(self._read_element_wrapper(version))

    # return interface
    return json.dumps(interface, indent=2)

  def _read_element(self, version):
    if self.file is None:
      raise Exception("File was not initialized properly")

    element = {}

    label = self.file.read_string(100)
    element["label"] = label
    type = self.file.read_int()
    element["type"] = self._decode_type(type)

    element["spr_idx"] = self.file.read_int()
    element["ui_base_spr_idx"] = self.file.read_int()
    element["ui_click_spr_idx"] = self.file.read_int()
    element["ui_disabled_spr_idx"] = self.file.read_int()
    element["ui_hover_spr_idx"] = self.file.read_int()
    element["ui_focus_spr_idx"] = self.file.read_int()

    for i in range(5):
      print(self.file.read_int())

    if version >= 3:
      x = self.file.read(4)
    if version >= 4:
      x = self.file.read(4)
    if version >= 5:
      x = self.file.read(4)
    if version >= 7:
      x = self.file.read(4)

    rectangle = [
      self.file.read_int(),
      self.file.read_int(),
      self.file.read_int(),
      self.file.read_int(),
    ]
    element["rectangle"] = rectangle

    alpha = [self.file.read_int(), self.file.read_int(), self.file.read_int()]
    element["alpha"] = alpha

    if version >= 3:
      x = self.file.read(24)
      print(x)

    sublabel = self.file.read_string(100)
    element["sublabel"] = sublabel

    y = self.file.read_int()

    return element

  def _read_element_wrapper(self, version):
    if self.file is None:
      raise Exception("File was not initialized properly")

    element = self._read_element(version)

    if version >= 6:
      spr = self.file.read_string(100)
      element["spr_file"] = spr

    return element

  def _decode_type(self, type):
    if type == 0:
      return "image"
    if type == 1:
      return "button"
    if type == 2:
      return "animation"
    if type == 3:
      return "text"
    if type == 4:
      return "scrollbar"
    if type == 5:
      return "scrollarea"
    if type == 6:
      return "input"
    if type == 7:
      return "checkbox"
    if type == 8:
      return "dragdrop"
    if type == 9:
      return "tab"
    return type
