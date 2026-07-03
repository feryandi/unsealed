"""Pipeline for .men UI files → MenScene.

Decodes the .men through SealMenDecoder and the referenced .spr through
`viewer.sprite_atlas.decode_spr_for_viewer`. Each MenElement gets a
`SpriteRef` per declared state — a sub-rectangle inside one of the
scene's shared atlases. No per-sprite pixel copy and no Blob hop.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from ....formats.men.decoder import SealMenDecoder
from ....vfs import Resource
from ...sprite_atlas import SpriteAtlas, SpriteRef, decode_spr_for_viewer
from .scene import STATE_NAMES, MenElement, MenScene

# Set UNSEALED_PROFILE=1 to print per-stage timings on .men load.
_PROFILE = bool(os.environ.get("UNSEALED_PROFILE"))

_STATE_KEYS: Dict[str, str] = {
  "base": "ui_base_spr_idx",
  "click": "ui_click_spr_idx",
  "disabled": "ui_disabled_spr_idx",
  "hover": "ui_hover_spr_idx",
  "focus": "ui_focus_spr_idx",
}


class MenViewerPipeline:
  """Decode a .men into a MenScene whose pixels live in shared atlases."""

  def run(self, res: Resource) -> MenScene:
    t_total = time.perf_counter()

    t0 = time.perf_counter()
    parsed, men_unknowns = self._decode_men(res)
    t_men = (time.perf_counter() - t0) * 1000

    version = int(parsed.get("version") or 0)
    spr_file_name = parsed.get("spr") or ""

    t0 = time.perf_counter()
    atlases, sprite_refs = self._decode_referenced_spr(res, spr_file_name)
    t_spr = (time.perf_counter() - t0) * 1000

    raw_roots = parsed.get("elements") or []

    t0 = time.perf_counter()
    elements: List[MenElement] = []
    root_indices: List[int] = []
    fallback_atlas_name = atlases[0].name if atlases else None
    self._flatten_tree(
      raw_roots, None, elements, root_indices, sprite_refs, fallback_atlas_name
    )
    t_flatten = (time.perf_counter() - t0) * 1000

    canvas_w, canvas_h = self._compute_canvas(elements)

    if _PROFILE:
      total = (time.perf_counter() - t_total) * 1000
      n_state_refs = sum(len(e.state_refs) for e in elements)
      print(
        f"[men profile] {res.name}: "
        f"decode_men={t_men:6.1f}ms  "
        f"decode_spr={t_spr:6.1f}ms  "
        f"flatten={t_flatten:6.1f}ms  "
        f"total={total:6.1f}ms  "
        f"(elements={len(elements)}, atlases={len(atlases)}, "
        f"state_refs={n_state_refs})"
      )

    return MenScene(
      unknowns=men_unknowns,
      spr_file_name=spr_file_name,
      atlases=atlases,
      elements=elements,
      root_indices=root_indices,
      canvas_w=canvas_w,
      canvas_h=canvas_h,
      version=version,
      selected_element_idx=None,
    )

  # ── tree construction ────────────────────────────────────────────────────

  @staticmethod
  def _flatten_tree(
    raw_list: List[dict],
    parent_idx: Optional[int],
    elements: List[MenElement],
    root_indices: List[int],
    sprite_refs: Dict[Tuple[str, int], SpriteRef],
    fallback_atlas_name: Optional[str],
  ) -> None:
    """Walk the decoder's already-nested element tree in preorder.

    The decoder emits a recursive structure: each element dict carries its
    direct children inline under `sub_elements`. We flatten that into the
    scene's flat `elements` list (the renderer is indexed by position) while
    wiring `parent` / `children` / `subtree_size` on each MenElement.
    """
    for raw in raw_list:
      idx = len(elements)
      el = MenViewerPipeline._build_element(raw, sprite_refs, fallback_atlas_name)
      el.parent = parent_idx
      elements.append(el)
      if parent_idx is None:
        root_indices.append(idx)
      else:
        elements[parent_idx].children.append(idx)
      MenViewerPipeline._flatten_tree(
        raw.get("sub_elements") or [], idx, elements, root_indices,
        sprite_refs, fallback_atlas_name,
      )
      el.subtree_size = len(elements) - idx - 1

  # ── private ─────────────────────────────────────────────────────────────

  @staticmethod
  def _decode_men(res: Resource) -> Tuple[dict, Dict[str, Dict[str, Any]]]:
    """Decode through SealMenDecoder, swallowing its stdout debug prints
    (older decoder paths may still log a few raw ints during parsing)."""
    from ....formats.base import collect_unknowns

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      decoder = SealMenDecoder(res.open())
      raw = decoder.decode()
    unknowns = collect_unknowns(decoder)
    try:
      parsed = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception as e:
      print(f"[men] decode failed: {e}")
      parsed = {}
    return parsed, unknowns

  @staticmethod
  def _decode_referenced_spr(
    men_res: Resource, spr_name: str
  ) -> Tuple[List[SpriteAtlas], Dict[Tuple[str, int], SpriteRef]]:
    """Decode the .spr referenced by the .men's `spr` header field. The
    reference is resolved beside the .men. Returns empty atlas/ref data
    if missing — the .men can still render with empty rects."""
    if not spr_name:
      print(f"[men] no .spr referenced by {men_res.name}")
      return [], {}
    spr_res = men_res.sibling(spr_name)
    if not spr_res.exists():
      print(f"[men] referenced .spr not found: {spr_name}")
      return [], {}
    try:
      return decode_spr_for_viewer(spr_res)
    except Exception as e:
      print(f"[men] spr decode failed: {e}")
      return [], {}

  @staticmethod
  def _build_element(
    raw: dict,
    sprite_refs: Dict[Tuple[str, int], SpriteRef],
    fallback_atlas_name: Optional[str],
  ) -> MenElement:
    rect = raw.get("rectangle") or [0, 0, 0, 0]
    rect_tuple: Tuple[int, int, int, int] = (
      _to_signed32(rect[0]) if len(rect) > 0 else 0,
      _to_signed32(rect[1]) if len(rect) > 1 else 0,
      _to_signed32(rect[2]) if len(rect) > 2 else 0,
      _to_signed32(rect[3]) if len(rect) > 3 else 0,
    )

    spr_file = raw.get("spr_file")
    spr_idx = int(raw.get("spr_idx") or 0)

    # Resolve every UI state sprite the .men declares.
    state_indices: Dict[str, int] = {}
    state_refs: Dict[str, SpriteRef] = {}
    for state in STATE_NAMES:
      key = _STATE_KEYS[state]
      if key not in raw:
        continue
      idx = int(raw.get(key) or 0)
      state_indices[state] = idx
      ref = _lookup_ref(sprite_refs, spr_file, idx, fallback_atlas_name)
      if ref is not None:
        state_refs[state] = ref
    # Always guarantee a "base" entry so something renders by default.
    if "base" not in state_refs:
      base_idx = int(raw.get("ui_base_spr_idx") or spr_idx)
      state_indices["base"] = base_idx
      ref = _lookup_ref(sprite_refs, spr_file, base_idx, fallback_atlas_name)
      if ref is not None:
        state_refs["base"] = ref

    return MenElement(
      label=str(raw.get("label") or ""),
      type=str(raw.get("type") or ""),
      spr_file=spr_file,
      spr_idx=spr_idx,
      rectangle=rect_tuple,
      state_refs=state_refs,
      state_indices=state_indices,
      active_state="base",
      raw=dict(raw),
    )

  @staticmethod
  def _compute_canvas(elements) -> Tuple[int, int]:
    """Canvas size = bounding box of all element rectangles, clamped to ≥ 1.

    Rectangles can hold negative coords (off-canvas elements); we only care
    about the positive extent the UI can possibly occupy. Sub-zero corners
    are clamped via `max(0, …)` before contributing to the bound.
    """
    max_x = 0
    max_y = 0
    for el in elements:
      x1, y1, x2, y2 = el.rectangle
      max_x = max(max_x, x1, x2, 0)
      max_y = max(max_y, y1, y2, 0)
    return max(max_x, 1), max(max_y, 1)


def _lookup_ref(
  sprite_refs: Dict[Tuple[str, int], SpriteRef],
  spr_file: Optional[str],
  spr_idx: int,
  fallback_atlas_name: Optional[str],
) -> Optional[SpriteRef]:
  """Map (spr_file, spr_idx) → SpriteRef. If `spr_file` doesn't resolve,
  retry against the first available atlas — mirrors the legacy
  `_resolve_sprite` fallback that used `subdirs[0]` when the named subdir
  wasn't present."""
  if spr_file is not None:
    ref = sprite_refs.get((spr_file, spr_idx))
    if ref is not None:
      return ref
  if fallback_atlas_name is not None:
    return sprite_refs.get((fallback_atlas_name, spr_idx))
  return None


def _to_signed32(v: int) -> int:
  """Reinterpret an unsigned 32-bit read as signed (handles negatives that
  the decoder reads as ~4.3B values)."""
  v = int(v)
  if v >= 0x80000000:
    v -= 0x100000000
  return v
