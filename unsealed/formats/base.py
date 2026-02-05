from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type, Pattern, TypeVar, Generic

from core.asset import Asset

T = TypeVar("T", bound=Asset)


class BaseFormat(ABC, Generic[T]):
  """Base class for all file formats"""

  @property
  @abstractmethod
  def extensions(self) -> Pattern[str]:
    """File extensions this format handles"""
    pass

  @property
  @abstractmethod
  def asset_type(self) -> Type[T]:  # Changed from Type[Asset] to Type[T]
    """The Asset type this format produces/consumes"""
    pass

  def decode(self, path: Path) -> T:  # Changed from Asset to T
    """Decode file to intermediate representation"""
    if not self.__can_decode(path):
      raise Exception(
        f"Cannot decode file with extension {path.suffix} with format for {self.extensions}"
      )
    if not path.is_file():
      raise Exception(f"File not found: {path}")
    return self.decoder(path)

  def __can_decode(self, path: Path) -> bool:
    if not path.is_file():
      return False
    return bool(self.extensions.search(path.name))

  @abstractmethod
  def decoder(self, path: Path) -> T:  # Changed from Asset to T
    """Decode file to intermediate representation"""
    pass

  def encode(self, asset: T, path: Path) -> None:  # Changed from Asset to T
    """Encode intermediate representation to file"""
    if not self.__can_encode(asset):
      raise Exception(
        f"Cannot encode asset of type {type(asset)} with format for {self.asset_type}"
      )
    return self.encoder(asset, path)

  def __can_encode(self, asset: Asset) -> bool:
    return isinstance(asset, self.asset_type)

  @abstractmethod
  def encoder(self, asset: T, path: Path) -> None:  # Changed from Asset to T
    """Encode intermediate representation to file"""
    pass
