import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ...utils.file import File

_ELEMENT_TYPE_NAMES: Dict[int, str] = {
  0: "image",
  1: "button",
  2: "animation",
  3: "text",
  4: "scrollbar",
  5: "scrollarea",
  6: "input",
  7: "checkbox",
  8: "dragdrop",
  9: "tab",
  # 12: like tab, layering / toggle?
}


class SealMenDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    self.file: Optional[File] = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open men file")

  def decode(self) -> str:
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
    interface["version"] = version

    spr_file = self.file.read_string(100)
    interface["spr"] = spr_file

    _ = self.file.read_int()

    interface["elements"] = []

    while not self.file.is_end():
      interface["elements"].append(self._read_element_wrapper(version))

    # return interface
    return json.dumps(interface, indent=2)

  def _read_element(self, version: int) -> Dict[str, Any]:
    if self.file is None:
      raise Exception("File was not initialized properly")

    element = {}

    label = self.file.read_string(100)
    element["label"] = label
    element_type = self.file.read_int()
    element["type"] = self._decode_type(element_type)

    element["spr_idx"] = self.file.read_int()
    element["ui_base_spr_idx"] = self.file.read_int()
    element["ui_click_spr_idx"] = self.file.read_int()
    element["ui_disabled_spr_idx"] = self.file.read_int()
    element["ui_hover_spr_idx"] = self.file.read_int()
    element["ui_focus_spr_idx"] = self.file.read_int()

    element["unknowns"] = [self.file.read_int() for _ in range(5)]

    if version >= 3:
      element["v3_unknown"] = self.file.read_int()
    if version >= 4:
      element["v4_unknown"] = self.file.read_int()
    if version >= 5:
      element["v5_unknown"] = self.file.read_int()
    if version >= 7:
      element["v7_unknown"] = self.file.read_int()

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
      element["v3_block"] = [self.file.read_int() for _ in range(6)]

    sublabel = self.file.read_string(100)
    element["sublabel"] = sublabel

    element["sub_element_size"] = self.file.read_int()

    return element

  def _read_element_wrapper(self, version: int) -> Dict[str, Any]:
    if self.file is None:
      raise Exception("File was not initialized properly")

    element = self._read_element(version)

    if version >= 6:
      spr = self.file.read_string(100)
      element["spr_file"] = spr

    # Children come AFTER spr_file in the byte stream. Reading them here
    # (not in _read_element) keeps spr_file aligned to the right offset.
    element["sub_elements"] = []
    for _ in range(element["sub_element_size"]):
      element["sub_elements"].append(self._read_element_wrapper(version))

    return element

  def _decode_type(self, element_type: int) -> Union[str, int]:
    return _ELEMENT_TYPE_NAMES.get(element_type, element_type)
