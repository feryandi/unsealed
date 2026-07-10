"""Generic reflection over decoded assets for the inspector tree.

Any decoded value is classified as a branch (object / list / dict) or a
leaf (scalar / bytes / short primitive list). Branches expand lazily so
huge collections (e.g. a mesh's vertices) don't build until opened.
"""

import numbers
from dataclasses import dataclass
from typing import Any

from PySide6.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem

# Cap children per branch so a giant list can't freeze the UI.
MAX_CHILDREN = 1000
# Auto-expand nested objects to this depth (lists/dicts stay closed).
AUTO_EXPAND_DEPTH = 3
# Truncate long string values shown inline in the tree.
INLINE_CHARS = 120

# -- value classification ---------------------------------------------


def is_scalar(value: Any) -> bool:
  # numbers.Number covers numpy scalars (np.float64, np.int64) too.
  return value is None or isinstance(value, (str, bool, numbers.Number))


def _is_object(value: Any) -> bool:
  return hasattr(value, "__dict__")


def _public_vars(value: Any) -> list[tuple[str, Any]]:
  return [(k, v) for k, v in vars(value).items() if not k.startswith("_")]


def is_inline_list(value: Any) -> bool:
  """A short, all-scalar list shows its value inline (e.g. a vec3)."""
  return (
    isinstance(value, (list, tuple))
    and 0 < len(value) <= 8
    and all(is_scalar(x) for x in value)
  )


def is_branch(value: Any) -> bool:
  if is_scalar(value) or isinstance(value, (bytes, bytearray)):
    return False
  if is_inline_list(value):
    return False
  if isinstance(value, (list, tuple, dict)):
    return len(value) > 0
  if _is_object(value):
    return len(_public_vars(value)) > 0
  return False


# -- labels -----------------------------------------------------------


def _fmt_scalar(value: Any) -> str:
  if isinstance(value, str):
    return value
  if isinstance(value, bool):
    return str(value)
  if isinstance(value, numbers.Integral):
    return str(int(value))
  if isinstance(value, numbers.Real):  # strips the np.float64(...) wrapper
    return repr(float(value))
  return repr(value)


def _truncate(text: str, limit: int = INLINE_CHARS) -> str:
  text = text.replace("\n", " ")
  return text if len(text) <= limit else text[: limit - 1] + "…"


def type_label(value: Any) -> str:
  if value is None:
    return "None"
  if isinstance(value, (list, tuple)):
    if value and _is_object(value[0]):
      return f"{type(value[0]).__name__}[{len(value)}]"
    return f"{type(value).__name__}[{len(value)}]"
  if isinstance(value, dict):
    return f"dict[{len(value)}]"
  return type(value).__name__


def value_summary(value: Any) -> str:
  if value is None:
    return "None"
  if isinstance(value, str):
    return _truncate(value)
  if isinstance(value, (bytes, bytearray)):
    return f"<{len(value)} bytes>"
  if isinstance(value, numbers.Number):
    return _fmt_scalar(value)
  if isinstance(value, (list, tuple)):
    if is_inline_list(value):
      return "[" + ", ".join(_fmt_scalar(x) for x in value) + "]"
    return f"[{len(value)} items]"
  if isinstance(value, dict):
    return f"{{{len(value)} keys}}"
  if _is_object(value):
    for key in ("name", "bitmap", "shader_name"):
      found = getattr(value, key, None)
      if isinstance(found, str) and found:
        return found
    return ""
  return _truncate(str(value))


# -- nodes ------------------------------------------------------------


@dataclass
class Node:
  name: str
  value: Any
  path: str


def child_nodes(node: Node) -> list[Node]:
  value = node.value
  items: list[Node] = []
  if isinstance(value, (list, tuple)):
    items = [Node(f"[{i}]", v, f"{node.path}[{i}]") for i, v in enumerate(value)]
  elif isinstance(value, dict):
    items = [Node(str(k), v, f"{node.path}[{k!r}]") for k, v in value.items()]
  elif _is_object(value):
    items = [Node(k, v, f"{node.path}.{k}") for k, v in _public_vars(value)]

  if len(items) > MAX_CHILDREN:
    hidden = len(items) - MAX_CHILDREN
    items = items[:MAX_CHILDREN]
    note = f"{hidden} more items (truncated)"
    items.append(Node("…", note, f"{node.path}[…]"))
  return items


class NodeItem(QTreeWidgetItem):
  """A tree row bound to a Node, lazily expanded on first open."""

  def __init__(self, node: Node, depth: int) -> None:
    super().__init__()
    self.node = node
    self.depth = depth
    self.loaded = not is_branch(node.value)
    self.setText(0, node.name)
    self.setText(1, type_label(node.value))
    self.setText(2, value_summary(node.value))
    if not self.loaded:
      # Placeholder so the expand arrow shows before children exist.
      self.addChild(QTreeWidgetItem())

  def is_object_branch(self) -> bool:
    return is_branch(self.node.value) and _is_object(self.node.value)


class AssetTree(QTreeWidget):
  """Name / Type / Value tree that reflects a decoded asset lazily."""

  def __init__(self, root_node: Node) -> None:
    super().__init__()
    self.setObjectName("assetTree")
    self.setColumnCount(3)
    self.setHeaderLabels(["Name", "Type", "Value"])
    self.setUniformRowHeights(True)
    self.setAllColumnsShowFocus(True)
    header = self.header()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    self.setColumnWidth(0, 280)
    self.setColumnWidth(1, 140)

    self.itemExpanded.connect(self._on_expanded)

    root = NodeItem(root_node, depth=0)
    self.addTopLevelItem(root)
    root.setExpanded(True)

  def _on_expanded(self, item: QTreeWidgetItem) -> None:
    if not isinstance(item, NodeItem) or item.loaded:
      return
    item.takeChildren()  # drop the placeholder
    item.loaded = True
    for child in child_nodes(item.node):
      child_item = NodeItem(child, item.depth + 1)
      item.addChild(child_item)
      if child_item.is_object_branch() and child_item.depth < AUTO_EXPAND_DEPTH:
        child_item.setExpanded(True)
