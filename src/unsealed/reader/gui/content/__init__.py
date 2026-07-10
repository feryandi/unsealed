"""Content-area infrastructure: format registry + generic asset tree.

Importing this package registers all format handlers as a side effect.
"""

from . import handlers  # noqa: F401  (self-registers handlers)
from .registry import ContentContext, FormatHandler, for_resource, register
from .tree import AssetTree, Node

__all__ = [
  "AssetTree",
  "ContentContext",
  "FormatHandler",
  "Node",
  "for_resource",
  "register",
]
