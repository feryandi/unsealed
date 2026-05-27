from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Type, Pattern, TypeVar, Generic

from ..core.asset import Asset

T = TypeVar("T", bound=Asset)


def collect_unknowns(obj: Any, prefix: str = "") -> Dict[str, Dict[str, Any]]:
  """Recursively walk a decoder or format wrapper and collect every nested `unknown` dict.

  Looks at the object's own `.unknown` plus any instance attribute that itself
  has `.unknown` (or is a list of such objects). Keys are dotted paths so the
  result is a single flat dict suitable for display in a tree-style UI.
  """
  out: Dict[str, Dict[str, Any]] = {}
  if not hasattr(obj, "__dict__"):
    return out

  own = getattr(obj, "unknown", None)
  if isinstance(own, dict) and own:
    out[prefix or type(obj).__name__] = own

  for name, value in vars(obj).items():
    if name.startswith("_") or name == "unknown" or name == "file":
      continue
    sub_prefix = f"{prefix}.{name}" if prefix else name
    if hasattr(value, "unknown"):
      out.update(collect_unknowns(value, sub_prefix))
    elif isinstance(value, list) and value and hasattr(value[0], "unknown"):
      for i, v in enumerate(value):
        out.update(collect_unknowns(v, f"{sub_prefix}[{i}]"))
  return out


class BaseFormat(ABC, Generic[T]):
  """Base class for all file formats"""

  @property
  @abstractmethod
  def extensions(self) -> Pattern[str]:
    """File extensions this format handles"""
    pass

  @property
  @abstractmethod
  def asset_type(self) -> Type[T]:
    """The Asset type this format produces/consumes"""
    pass

  def decode(self, path: Path) -> T:
    """Decode file to intermediate representation"""
    if not self.__can_decode(path):
      raise Exception(
        f"Cannot decode file with extension {path.suffix} with format for {self.extensions}"
      )
    if not path.is_file():
      raise FileNotFoundError(f"File not found: {path}")
    return self.decoder(path)

  def __can_decode(self, path: Path) -> bool:
    if not path.is_file():
      return False
    return bool(self.extensions.search(path.name))

  @abstractmethod
  def decoder(self, path: Path) -> T:
    """Decode file to intermediate representation"""
    pass

  def encode(self, asset: T, path: Path) -> None:
    """Encode intermediate representation to file"""
    if not self.__can_encode(asset):
      raise Exception(
        f"Cannot encode asset of type {type(asset)} with format for {self.asset_type}"
      )
    return self.encoder(asset, path)

  def __can_encode(self, asset: Asset) -> bool:
    return isinstance(asset, self.asset_type)

  @abstractmethod
  def encoder(self, asset: T, path: Path) -> None:
    """Encode intermediate representation to file"""
    pass
