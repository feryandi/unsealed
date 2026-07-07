from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Type, Pattern, TypeVar, Generic, Union

from ..core.asset import Asset
from ..vfs import Resource

T = TypeVar("T", bound=Asset)


def collect_unknowns(obj: Any, prefix: str = "") -> Dict[str, Dict[str, Any]]:
  """Walk a decoder/format, collecting every nested `unknown` dict.

  Looks at the object's own `.unknown` plus any instance attribute that
  itself has `.unknown` (or is a list of such objects). Keys are dotted
  paths so the result is a single flat dict for a tree-style UI.
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

  def decode(self, target: Union[Path, Resource]) -> T:
    """Decode a file (disk Path or vfs Resource) to its asset.

    A Path is wrapped in a DiskSource-backed Resource so disk callers
    (the CLI) keep working while archive callers pass a Resource.
    """
    res = target if isinstance(target, Resource) else Resource.for_disk_file(target)
    if not self.extensions.search(res.name):
      raise Exception(
        f"Cannot decode file with extension {res.suffix} "
        f"with format for {self.extensions}"
      )
    if not res.exists():
      raise FileNotFoundError(f"File not found: {res.logical_name}")
    return self.decoder(res)

  @abstractmethod
  def decoder(self, res: Resource) -> T:
    """Decode a Resource to its intermediate representation"""
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
