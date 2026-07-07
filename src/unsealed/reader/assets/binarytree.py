from typing import Optional


class BinaryTree:
  def __init__(self) -> None:
    self.root: Optional[BinaryTreeNode] = None

  def __repr__(self) -> str:
    return f"<BinaryTree root:{self.root}>"


class BinaryTreeNode:
  def __init__(self, value: int) -> None:
    self.value: int = value
    self.left: Optional[BinaryTreeNode] = None
    self.right: Optional[BinaryTreeNode] = None

  def __repr__(self) -> str:
    return f"<BinaryTreeNode \
      value:{self.value} left:{self.left} right:{self.right}>"
