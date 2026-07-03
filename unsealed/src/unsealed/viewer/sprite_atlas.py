"""Atlas-aware .spr decode for the viewer.

The viewer doesn't need the Blob asset abstraction the formats/ layer
exposes. Per-sprite bytes copies + per-sprite GL texture uploads were the
two biggest costs on .men/.spr load. This module gives the viewer a
flatter representation:

  - `SpriteAtlas`  : one decoded source atlas (HxWx4 uint8 numpy array)
  - `SpriteRef`    : a sub-rectangle inside a SpriteAtlas
  - `decode_spr_for_viewer(path)` -> (atlases, sprite_refs)

The viewer extensions upload one GL texture per atlas (not one per sprite)
and the renderer computes UVs from each ref's pixel coords. Subsequent
sprite "selection" or "state switch" never touches the GPU.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..assets.blob import Blob
from ..formats.spr.decoder import SealSprDecoder
from ..formats.tex.format import SealTextureFormat
from ..vfs import Resource


_PROFILE = bool(os.environ.get("UNSEALED_PROFILE"))
_MAX_DECODE_WORKERS = min(8, (os.cpu_count() or 4))

# Suffixes the .spr's ref_filename may resolve to on disk. Listed in
# preference order — `.tex` is the common case; `.te1` shows up in some
# variants of the data.
_TEX_SUFFIXES: Tuple[str, ...] = (".tex", ".te1")

# Sentinel sprite index meaning "the whole atlas" (i.e. the full source
# texture, displayed when the user clicks a subdir header in SPR mode).
FULL_ATLAS_IDX: int = -1


@dataclass
class SpriteAtlas:
  """One decoded source atlas referenced by a .spr file.

  `rgba` is the CPU-side decoded pixels, only needed long enough for a
  GL texture upload. Render extensions are expected to set it back to
  None once the upload completes so the buffer can be reclaimed —
  width/height stay around for UV math.
  """

  name: str               # the original `ref_filename` field from the .spr
  width: int              # pixels
  height: int             # pixels
  rgba: Optional[np.ndarray] = None  # HxWx4 uint8; None after GPU upload


@dataclass(frozen=True)
class SpriteRef:
  """Sub-rectangle inside a SpriteAtlas, in pixel coords (origin top-left)."""

  atlas_idx: int
  left: int
  top: int
  right: int
  bottom: int

  @property
  def width(self) -> int:
    return max(0, self.right - self.left)

  @property
  def height(self) -> int:
    return max(0, self.bottom - self.top)


def decode_spr_for_viewer(
  spr_res: Resource,
) -> Tuple[List[SpriteAtlas], Dict[Tuple[str, int], SpriteRef]]:
  """Decode a .spr into atlases + a sprite-ref lookup.

  Returns:
    atlases:     ordered list, deduped by `ref_filename`. Missing atlases
                 (referenced but unresolvable) are skipped.
    sprite_refs: maps (ref_filename, sprite_idx) -> SpriteRef.
                 `sprite_idx >= 0` is the i-th quad declared for that
                 atlas in the .spr (i.e. the i-th cropped sprite).
                 `sprite_idx == FULL_ATLAS_IDX (-1)` references the whole
                 source atlas.

  Decoding is parallel across unique atlases.
  """
  t_total = time.perf_counter()

  t0 = time.perf_counter()
  entries = SealSprDecoder(spr_res.open()).decode()
  t_header = (time.perf_counter() - t0) * 1000

  tex_format = SealTextureFormat()

  # Order-preserving dedupe by filename.
  unique_refs: List[str] = []
  seen: set = set()
  for ref_filename, _quads in entries:
    if ref_filename in seen:
      continue
    seen.add(ref_filename)
    unique_refs.append(ref_filename)

  t0 = time.perf_counter()
  decoded: Dict[str, np.ndarray] = {}
  per_atlas_stats: List[dict] = []
  if unique_refs:
    n_workers = min(_MAX_DECODE_WORKERS, len(unique_refs))
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
      results = pool.map(
        lambda ref: _decode_atlas_to_rgba(spr_res, ref, tex_format),
        unique_refs,
      )
      for ref, (arr, stats) in zip(unique_refs, results):
        if arr is not None:
          decoded[ref] = arr
        per_atlas_stats.append(stats)
  t_decode = (time.perf_counter() - t0) * 1000

  # Materialize the ordered atlas list + name->idx lookup. Skip refs that
  # failed to decode — they simply produce no entries in sprite_refs.
  atlases: List[SpriteAtlas] = []
  idx_by_name: Dict[str, int] = {}
  for ref in unique_refs:
    arr = decoded.get(ref)
    if arr is None:
      continue
    idx_by_name[ref] = len(atlases)
    atlases.append(SpriteAtlas(
      name=ref,
      width=int(arr.shape[1]),
      height=int(arr.shape[0]),
      rgba=arr,
    ))

  # Build sprite_refs from the .spr's quad entries. Bounds-clamp so a
  # malformed quad can't produce a negative or out-of-image rect.
  sprite_refs: Dict[Tuple[str, int], SpriteRef] = {}
  for ref_filename, quads in entries:
    atlas_idx = idx_by_name.get(ref_filename)
    if atlas_idx is None:
      continue
    atlas = atlases[atlas_idx]
    w, h = atlas.width, atlas.height
    # Full-atlas sentinel — lets SPR mode point at the source texture
    # without the "is this a special row" branching the old code had.
    sprite_refs[(ref_filename, FULL_ATLAS_IDX)] = SpriteRef(
      atlas_idx=atlas_idx, left=0, top=0, right=w, bottom=h
    )
    for i, (left, right, top, bottom) in enumerate(quads):
      l = max(0, min(int(left), w))
      r = max(0, min(int(right), w))
      t = max(0, min(int(top), h))
      b = max(0, min(int(bottom), h))
      if r <= l or b <= t:
        continue
      sprite_refs[(ref_filename, i)] = SpriteRef(
        atlas_idx=atlas_idx, left=l, top=t, right=r, bottom=b
      )

  if _PROFILE:
    total = (time.perf_counter() - t_total) * 1000
    print(
      f"[atlas profile] {spr_res.name}: "
      f"header={t_header:6.1f}ms  "
      f"decode_par={t_decode:6.1f}ms  "
      f"total={total:6.1f}ms  "
      f"(atlases={len(atlases)}/{len(unique_refs)} unique, "
      f"sprite_refs={len(sprite_refs)})"
    )
    print("  per-atlas (ms): open  decode  total  | format  size")
    for s in per_atlas_stats:
      if s.get("status") != "decoded":
        print(f"    {s.get('ref', '?'):>32}: {s.get('status', 'MISSING')}")
        continue
      per_total = (s["t_thread_end"] - s["t_thread_start"]) * 1000
      size = s.get("src_size", (0, 0))
      print(
        f"    {s['ref']:>32}  "
        f"{s.get('t_open', 0.0):5.1f}  "
        f"{s.get('t_decode', 0.0):6.1f}  "
        f"{per_total:5.1f}  | "
        f"{s.get('src_format', '?'):>6}  "
        f"{size[0]}x{size[1]}"
      )

  return atlases, sprite_refs


def _decode_atlas_to_rgba(
  spr_res: Resource,
  ref_filename: str,
  tex_format: SealTextureFormat,
) -> Tuple[Optional[np.ndarray], dict]:
  """Resolve `ref_filename` beside `spr_res`, decode the .tex/.te1 to an
  RGBA `np.ndarray` (HxWx4 uint8). Returns `(array, stats)`; on failure
  the array is None and `stats["status"]` describes why.
  """
  t_thread_start = time.perf_counter()
  stats: dict = {
    "ref": ref_filename,
    "status": "decoded",
    "t_thread_start": t_thread_start,
    "t_thread_end": t_thread_start,
    "t_open": 0.0,
    "t_decode": 0.0,
    "src_format": "?",
    "src_size": (0, 0),
  }

  t0 = time.perf_counter()
  tex_res = _resolve_tex_ref(spr_res, ref_filename)
  if tex_res is None:
    stats["status"] = "missing"
    stats["t_thread_end"] = time.perf_counter()
    return None, stats

  try:
    blob: Blob = tex_format.decoder(tex_res)
  except Exception:
    stats["status"] = "open_failed"
    stats["t_open"] = (time.perf_counter() - t0) * 1000
    stats["t_thread_end"] = time.perf_counter()
    return None, stats
  stats["t_open"] = (time.perf_counter() - t0) * 1000
  stats["src_format"] = (blob.extension or "?").upper()

  if not blob.value:
    stats["status"] = "open_failed"
    stats["t_thread_end"] = time.perf_counter()
    return None, stats

  t0 = time.perf_counter()
  try:
    from PIL import Image
    image = Image.open(BytesIO(blob.value))
    if image.mode != "RGBA":
      image = image.convert("RGBA")
    arr = np.asarray(image, dtype=np.uint8).copy()
  except Exception:
    stats["status"] = "open_failed"
    stats["t_decode"] = (time.perf_counter() - t0) * 1000
    stats["t_thread_end"] = time.perf_counter()
    return None, stats
  stats["t_decode"] = (time.perf_counter() - t0) * 1000
  stats["src_size"] = (int(arr.shape[1]), int(arr.shape[0]))

  stats["t_thread_end"] = time.perf_counter()
  return arr, stats


def _resolve_tex_ref(spr_res: Resource, ref_filename: str) -> Optional[Resource]:
  """Resolve a .spr `ref_filename` to a sibling texture Resource.

  `SealTextureFormat` XOR-deobfuscates `.tex`/`.te1` and pulls out the
  embedded image, so prefer those siblings over a literal-name match —
  e.g. if the .spr says `share.tga` and both `share.tga` (raw) and
  `share.tex` (obfuscated) sit beside each other, the `.tex` decodes.
  Falls back to the literal name. Case-insensitivity is handled by the
  source's resolve(), so no manual directory scan is needed.
  """
  if not ref_filename:
    return None

  stem = PurePosixPath(ref_filename.replace("\\", "/")).stem
  for suffix in _TEX_SUFFIXES:
    candidate = spr_res.sibling(f"{stem}{suffix}")
    if candidate.exists():
      return candidate

  literal = spr_res.sibling(ref_filename)
  if literal.exists():
    return literal

  return None
