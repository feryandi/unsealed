"""Local store of recovered .spak fallback passwords.

Private-server archive keys are NOT committed to the codebase. They live
in a per-user file plus the ``UNSEALED_SPAK_KEYS`` env var, and tried as
a fallback when the version-derived key fails -- each verified by CRC
before use (see ``SpakArchive._resolve_key``). The recovery tool
writes discovered keys here, so the reader and viewer pick them up with
nothing sensitive in git.

File location (first that applies):
- ``$UNSEALED_CONFIG_DIR/spak_keys.txt``
- Windows: ``%LOCALAPPDATA%/unsealed/spak_keys.txt``
- else: ``$XDG_CONFIG_HOME/unsealed/spak_keys.txt`` (or ``~/.config``)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

# A recovered ZipCrypto key: either a password (bytes) or, when only the
# internal keys are known (known-plaintext attack -- the password is too
# long to brute-force), the three 32-bit keys.
KeyTriple = Tuple[int, int, int]

_HEADER = "# Unsealed recovered .spak keys (one per line). Local only; do not commit.\n"


def store_path() -> Path:
  override = os.environ.get("UNSEALED_CONFIG_DIR")
  if override:
    root = Path(override)
  elif os.name == "nt":
    root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "unsealed"
  else:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    root = (Path(xdg) if xdg else Path.home() / ".config") / "unsealed"
  return root / "spak_keys.txt"


def load_keys() -> List[bytes]:
  """Fallback keys from the env var then store file, de-duplicated."""
  raw: List[bytes] = []
  for tok in os.environ.get("UNSEALED_SPAK_KEYS", "").replace(",", " ").split():
    raw.append(tok.encode())
  path = store_path()
  if path.is_file():
    for line in path.read_text(encoding="utf-8").splitlines():
      line = line.split("#", 1)[0].strip()  # allow "key  # label"
      if line and not line.startswith("keys:"):  # 'keys:' = a key triple
        raw.append(line.encode())
  seen, out = set(), []
  for k in raw:
    if k and k not in seen:
      seen.add(k)
      out.append(k)
  return out


def load_key_triples() -> List[KeyTriple]:
  """Recovered key triples (``keys:k0,k1,k2`` lines), de-duped."""
  out: List[KeyTriple] = []
  seen = set()
  path = store_path()
  if path.is_file():
    for line in path.read_text(encoding="utf-8").splitlines():
      line = line.split("#", 1)[0].strip()
      if not line.startswith("keys:"):
        continue
      try:
        k0, k1, k2 = (int(x, 16) for x in line[len("keys:") :].split(","))
      except ValueError:
        continue
      triple = (k0, k1, k2)
      if triple not in seen:
        seen.add(triple)
        out.append(triple)
  return out


def save_key(key: bytes, label: str = "") -> Path:
  """Append ``key`` to the store (no-op if present); returns path."""
  path = store_path()
  if key in set(load_keys()):
    return path
  path.parent.mkdir(parents=True, exist_ok=True)
  new_file = not path.exists() or path.stat().st_size == 0
  line = key.decode("latin1")
  if label:
    line = f"{line}  # {label}"
  with path.open("a", encoding="utf-8") as f:
    if new_file:
      f.write(_HEADER)
    f.write(line + "\n")
  return path


def save_key_triple(keys: KeyTriple, label: str = "") -> Path:
  """Append recovered internal keys (no-op if present); returns path."""
  path = store_path()
  if tuple(keys) in set(load_key_triples()):
    return path
  path.parent.mkdir(parents=True, exist_ok=True)
  new_file = not path.exists() or path.stat().st_size == 0
  k0, k1, k2 = keys
  line = f"keys:{k0:08x},{k1:08x},{k2:08x}"
  if label:
    line = f"{line}  # {label}"
  with path.open("a", encoding="utf-8") as f:
    if new_file:
      f.write(_HEADER)
    f.write(line + "\n")
  return path
