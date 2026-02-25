from pathlib import Path
from typing import Dict, List, Optional

from ...assets.animation import Animation, Keyframe
from ...assets.binarytree import BinaryTree, BinaryTreeNode
from ...utils.file import File


class SealAnimationDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    self.nodes: int = 0
    try:
      with open(path, "rb") as dat:
        self.file: File = File(dat.read())
    except Exception:
      raise Exception("Unable to open mesh file")

  def decode(self) -> List[Animation]:
    animations = []
    start_frame = self.file.read_int()
    end_frame = self.file.read_int()
    fps = self.file.read_float()
    ticks_per_frame = self.file.read_float()

    _source_filename = self.file.read_string(256)

    _ = self.file.read_int()  # Same as number of nodes
    _ = self.file.read_int()  # Usually same as or more than end_frame
    _ = self.file.read_int()  # Usually 0
    _ = self.file.read_int()  # Usually same as end_frame

    self.nodes = self.file.read_int()

    for i in range(self.nodes):
      name = self.file.read_string(256)
      node = Animation(self.path, start_frame, end_frame, fps, ticks_per_frame, name)

      self.__decode_position(node)
      self.__decode_rotation(node)
      self.__decode_scale(node)

      animations.append(node)
    return animations

  def __decode_position(self, node: Animation) -> None:
    size = self.file.read_int()
    hash_table = []

    for j in range(size):
      time = self.file.read_int()
      x = self.file.read_float()
      y = self.file.read_float()
      z = self.file.read_float()
      position = [x, y, z]
      keyframe = Keyframe(time, position)
      node.transforms.append(keyframe)

      left_child_frame = self.file.read_int()
      right_child_frame = self.file.read_int()
      hash_table.append(
        {
          "left": left_child_frame if left_child_frame != 0xFFFFFFFE else None,
          "right": right_child_frame if right_child_frame != 0xFFFFFFFE else None,
        }
      )
    if size != 0:
      root_frame = self.file.read_int()
      node.btree = self.__decode_hash_table(hash_table, root_frame)

  def __decode_rotation(self, node: Animation) -> None:
    size = self.file.read_int()
    hash_table = []

    for j in range(size):
      time = self.file.read_int()
      x = self.file.read_float()
      y = self.file.read_float()
      z = self.file.read_float()
      w = self.file.read_float()
      rotation = [x, y, z, w]
      keyframe = Keyframe(time, rotation)
      node.rotations.append(keyframe)

      # Redundant axis-angle encoding
      # axis = [qx, qy, qz] / sin(angle/2)
      # angle = 2 * arccos(w)
      _axis_x = self.file.read_float()
      _axis_y = self.file.read_float()
      _axis_z = self.file.read_float()
      _angle = self.file.read_float()

      left_child_frame = self.file.read_int()
      right_child_frame = self.file.read_int()
      hash_table.append(
        {
          "left": left_child_frame if left_child_frame != 0xFFFFFFFE else None,
          "right": right_child_frame if right_child_frame != 0xFFFFFFFE else None,
        }
      )
    if size != 0:
      root_frame = self.file.read_int()
      node.btree = self.__decode_hash_table(hash_table, root_frame)

  def __decode_scale(self, node: Animation) -> None:
    size = self.file.read_int()
    hash_table = []

    for j in range(size):
      time = self.file.read_int()
      x = self.file.read_float()
      y = self.file.read_float()
      z = self.file.read_float()
      scale = [x, y, z]
      keyframe = Keyframe(time, scale)
      node.scales.append(keyframe)

      _x = self.file.read_float()  # Usually 0.0
      _y = self.file.read_float()  # Usually 0.0
      _z = self.file.read_float()  # Usually 0.0
      _w = self.file.read_float()  # Usually 0.0

      left_child_frame = self.file.read_int()
      right_child_frame = self.file.read_int()
      hash_table.append(
        {
          "left": left_child_frame if left_child_frame != 0xFFFFFFFE else None,
          "right": right_child_frame if right_child_frame != 0xFFFFFFFE else None,
        }
      )
    if size != 0:
      root_frame = self.file.read_int()
      node.btree = self.__decode_hash_table(hash_table, root_frame)

  def __decode_hash_table(
    self, hash_table: List[Dict[str, Optional[int]]], root_frame: int
  ) -> BinaryTree:
    bt = BinaryTree()
    bt.root = BinaryTreeNode(root_frame)

    def dfs(node: BinaryTreeNode):
      if node.value is None:
        return
      h: Dict[str, Optional[int]] = hash_table[node.value]

      left_value = h.get("left")
      if left_value is not None:
        node.left = BinaryTreeNode(left_value)
        dfs(node.left)

      right_value = h.get("right")
      if right_value is not None:
        node.right = BinaryTreeNode(right_value)
        dfs(node.right)

    dfs(bt.root)
    return bt
