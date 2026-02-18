from typing import Optional


class BinaryTree:
  def __init__(self):
    self.root: Optional[BinaryTreeNode] = None

  def __repr__(self):
    return f"<BinaryTree root:{self.root}>"


class BinaryTreeNode:
  def __init__(self, value):
    self.value = value
    self.left: Optional[BinaryTreeNode] = None
    self.right: Optional[BinaryTreeNode] = None

  def __repr__(self):
    return f"<BinaryTreeNode \
      value:{self.value} left:{self.left} right:{self.right}>"
