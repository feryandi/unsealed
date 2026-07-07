"""Cross-mode HUD panels.

`draw_unknowns_window(scene)` renders an imgui tree of `scene.unknowns`,
the per-decoder dict of fields the decoder read but doesn't have a
high-level name for yet. Used by every mode that loads a file with
non-trivial unknown bytes (model, map, men, …).
"""

from __future__ import annotations

from typing import Any

from imgui_bundle import imgui


_MAX_BYTES_PREVIEW = 32
_MAX_LIST_PREVIEW = 8


def draw_unknowns_window(scene) -> None:
  """Render a collapsible 'Unknown Fields' window from scene.unknowns.

  Does nothing if the scene carries no unknowns. Safe to call every frame
  from a mode's draw_hud.
  """
  unknowns = getattr(scene, "unknowns", None)
  if not unknowns:
    return

  imgui.set_next_window_pos((10, 300), imgui.Cond_.first_use_ever.value)
  imgui.set_next_window_size((360, 380), imgui.Cond_.first_use_ever.value)
  imgui.set_next_window_collapsed(True, imgui.Cond_.first_use_ever.value)
  imgui.begin("Unknown Fields")

  total = sum(len(v) for v in unknowns.values() if isinstance(v, dict))
  imgui.text_disabled(f"{len(unknowns)} decoders · {total} fields")
  imgui.separator()

  for src, fields in unknowns.items():
    if not isinstance(fields, dict) or not fields:
      continue
    if imgui.tree_node(f"{src} ({len(fields)})"):
      for key, value in fields.items():
        _draw_field(key, value)
      imgui.tree_pop()

  imgui.end()


def _draw_field(key: str, value: Any) -> None:
  """One row in the tree: either a leaf imgui.text or a nested tree node."""
  if isinstance(value, dict):
    if imgui.tree_node(f"{key} ({len(value)})"):
      for k, v in value.items():
        _draw_field(str(k), v)
      imgui.tree_pop()
    return

  if isinstance(value, list):
    n = len(value)
    if n == 0:
      imgui.text(f"{key}: []")
      return
    if imgui.tree_node(f"{key}  [{n}]"):
      for i, item in enumerate(value[:_MAX_LIST_PREVIEW]):
        _draw_field(f"[{i}]", item)
      if n > _MAX_LIST_PREVIEW:
        imgui.text_disabled(f"… +{n - _MAX_LIST_PREVIEW} more")
      imgui.tree_pop()
    return

  if isinstance(value, (bytes, bytearray)):
    hexed = value[:_MAX_BYTES_PREVIEW].hex(" ")
    suffix = "" if len(value) <= _MAX_BYTES_PREVIEW else f" … (+{len(value) - _MAX_BYTES_PREVIEW}B)"
    imgui.text(f"{key}: <{len(value)}B> {hexed}{suffix}")
    return

  if isinstance(value, float):
    imgui.text(f"{key}: {value:.6g}")
    return

  imgui.text(f"{key}: {value!r}")
