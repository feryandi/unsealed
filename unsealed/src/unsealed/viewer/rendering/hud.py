"""
HUD text panel renderer.

Renders one or more HudPanel objects as screen-space quads using pygame surfaces
uploaded to GL textures each frame.  Panels may contain:
  - text lines  (existing behaviour)
  - a horizontal row of HudButton widgets
  - a vertical clickable list of HudButton items

Returns all rendered HudButton objects with their screen-space rects filled in
so that the input system can do CPU hit-testing without touching the GPU.
"""
from __future__ import annotations

import ctypes
from typing import List, Tuple

import numpy as np
from OpenGL.GL import *  # noqa: F401, F403

from ..hud_types import HudButton, HudPanel
from .shaders import _compile_prog, _HUD_VERT, _HUD_FRAG

# ── layout constants ──────────────────────────────────────────────────────────
_PAD = 10          # panel outer padding (px)
_LINE_H = 18       # text line height (px)
_BTN_H = 26        # button row height (px)
_BTN_PAD_X = 8     # horizontal padding inside each button
_BTN_GAP = 6       # gap between adjacent buttons
_LIST_ITEM_H = 20  # height of each clickable list row
_SECTION_GAP = 8   # vertical gap between different content sections

# ── colours ───────────────────────────────────────────────────────────────────
_BG          = (18,  18,  22,  200)
_TEXT_NORMAL = (215, 215, 230)
_TEXT_HL     = (255, 220,  80)   # highlighted line / active list item
_TEXT_HOVER  = (255, 255, 255)

_BTN_BG      = ( 30,  30,  45, 210)
_BTN_BG_HOV  = ( 55,  70, 105, 230)
_BTN_BORDER  = ( 80,  80, 110)
_BTN_BOR_HOV = (160, 190, 255)
_BTN_TEXT    = (200, 200, 220)
_BTN_TEXT_HOV = (255, 255, 255)

_LIST_HOV_BG = (40, 42, 62, 180)


class HudRenderer:
  """Manages the HUD shader + VAO/VBO and renders text panels."""

  def __init__(self) -> None:
    self._prog: int = 0
    self._vao: int = 0
    self._vbo: int = 0

  def init(self) -> None:
    self._prog = _compile_prog(_HUD_VERT, _HUD_FRAG)
    self._vao = glGenVertexArrays(1)
    self._vbo = glGenBuffers(1)

  def render(
    self,
    panels: List[HudPanel],
    font: object,
    width: int,
    height: int,
    mouse_pos: Tuple[int, int] = (-1, -1),
  ) -> List[HudButton]:
    """Render all panels; return every HudButton with its screen rect filled."""
    all_buttons: List[HudButton] = []
    for panel in panels:
      if panel.lines or panel.buttons or panel.list_items:
        all_buttons.extend(self._render_panel(panel, font, width, height, mouse_pos))
    return all_buttons

  def cleanup(self) -> None:
    if self._prog:
      glDeleteProgram(self._prog)
      self._prog = 0
    if self._vao:
      glDeleteVertexArrays(1, [self._vao])
      self._vao = 0
    if self._vbo:
      glDeleteBuffers(1, [self._vbo])
      self._vbo = 0

  # ── internal ─────────────────────────────────────────────────────────────────

  def _render_panel(
    self,
    panel: HudPanel,
    font: object,
    width: int,
    height: int,
    mouse_pos: Tuple[int, int],
  ) -> List[HudButton]:
    import pygame

    mx, my = mouse_pos

    # ── measure content ───────────────────────────────────────────────────────

    # Text lines
    text_w = max(
      (font.size(l)[0] for l in panel.lines if l),  # type: ignore[attr-defined]
      default=0,
    )

    # Button row: measure each button individually
    btn_texts = [
      f"{b.icon} {b.label}" if b.icon else b.label for b in panel.buttons
    ]
    btn_widths = [
      font.size(t)[0] + 2 * _BTN_PAD_X  # type: ignore[attr-defined]
      for t in btn_texts
    ]
    btn_row_w = (
      sum(btn_widths) + _BTN_GAP * max(0, len(btn_widths) - 1)
      if btn_widths else 0
    )

    # List items
    list_texts = [
      f"{b.icon} {b.label}" if b.icon else b.label for b in panel.list_items
    ]
    list_w = max(
      (font.size(t)[0] for t in list_texts),  # type: ignore[attr-defined]
      default=0,
    ) + _PAD  # extra right indent

    content_w = max(text_w, btn_row_w, list_w)
    total_w = content_w + 2 * _PAD

    # ── measure height ────────────────────────────────────────────────────────
    text_h    = len(panel.lines)      * _LINE_H      if panel.lines      else 0
    btn_row_h = _BTN_H                               if panel.buttons    else 0
    list_h    = len(panel.list_items) * _LIST_ITEM_H if panel.list_items else 0

    gap1 = _SECTION_GAP if (panel.lines and panel.buttons)    else 0
    gap2 = _SECTION_GAP if ((panel.lines or panel.buttons) and panel.list_items) else 0

    total_h = 2 * _PAD + text_h + gap1 + btn_row_h + gap2 + list_h

    # ── screen position (top-left of panel, y=0 at top) ──────────────────────
    px = panel.x if panel.x >= 0 else width  + panel.x - total_w
    py = panel.y if panel.y >= 0 else height + panel.y - total_h

    # Store screen-space bounds so InputSystem can hit-test scroll events.
    panel.rect = (px, py, total_w, total_h)

    # ── draw to pygame surface ────────────────────────────────────────────────
    surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    surf.fill(_BG)

    cursor_y = _PAD

    # Text lines
    for i, line in enumerate(panel.lines):
      if line:
        color = _TEXT_HL if i == panel.highlight_idx else _TEXT_NORMAL
        ts = font.render(line, True, color)  # type: ignore[attr-defined]
        surf.blit(ts, (_PAD, cursor_y))
      cursor_y += _LINE_H

    cursor_y += gap1

    # Button row
    active_buttons: List[HudButton] = []
    bx = _PAD
    for btn, bw, txt in zip(panel.buttons, btn_widths, btn_texts):
      scr_x = px + bx
      scr_y = py + cursor_y
      btn.rect = (scr_x, scr_y, bw, _BTN_H)
      hovered = scr_x <= mx < scr_x + bw and scr_y <= my < scr_y + _BTN_H

      bg     = _BTN_BG_HOV  if hovered else _BTN_BG
      border = _BTN_BOR_HOV if hovered else _BTN_BORDER
      fg     = _BTN_TEXT_HOV if hovered else _BTN_TEXT

      pygame.draw.rect(surf, bg, (bx, cursor_y, bw, _BTN_H), border_radius=3)
      pygame.draw.rect(surf, border, (bx, cursor_y, bw, _BTN_H), 1, border_radius=3)
      ts = font.render(txt, True, fg)  # type: ignore[attr-defined]
      tw, th = ts.get_size()
      surf.blit(ts, (bx + (bw - tw) // 2, cursor_y + (_BTN_H - th) // 2))

      bx += bw + _BTN_GAP
      active_buttons.append(btn)

    if panel.buttons:
      cursor_y += _BTN_H

    cursor_y += gap2

    # List items
    item_w = total_w - 2 * _PAD
    for i, (item, txt) in enumerate(zip(panel.list_items, list_texts)):
      scr_x = px + _PAD
      scr_y = py + cursor_y
      item.rect = (scr_x, scr_y, item_w, _LIST_ITEM_H)
      hovered = scr_x <= mx < scr_x + item_w and scr_y <= my < scr_y + _LIST_ITEM_H

      is_active = i == panel.list_highlight_idx
      fg = _TEXT_HL if is_active else (_TEXT_HOVER if hovered else _TEXT_NORMAL)

      if hovered and not is_active:
        pygame.draw.rect(surf, _LIST_HOV_BG, (_PAD, cursor_y, item_w, _LIST_ITEM_H))

      prefix = "▶ " if is_active else "  "
      ts = font.render(prefix + txt, True, fg)  # type: ignore[attr-defined]
      surf.blit(ts, (_PAD, cursor_y + (_LIST_ITEM_H - ts.get_height()) // 2))

      cursor_y += _LIST_ITEM_H
      active_buttons.append(item)

    # ── upload to GPU ─────────────────────────────────────────────────────────
    # No flip needed: GL expects first row at texture bottom (v=0), but pygame
    # surface rows start at the top.  We compensate by swapping the UV v-coords
    # in the quad (v=0 → panel top, v=1 → panel bottom) so the image maps correctly.
    raw = pygame.image.tostring(surf, "RGBA")

    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexImage2D(
      GL_TEXTURE_2D, 0, GL_RGBA, total_w, total_h, 0, GL_RGBA, GL_UNSIGNED_BYTE, raw
    )
    glBindTexture(GL_TEXTURE_2D, 0)

    # NDC quad (py=0 is window top, NDC y=+1 is window top)
    x0 = px / width  * 2.0 - 1.0
    x1 = (px + total_w) / width  * 2.0 - 1.0
    y1 = 1.0 - py / height * 2.0           # NDC top of panel
    y0 = 1.0 - (py + total_h) / height * 2.0  # NDC bottom of panel
    # UV: v=0 → panel top (pygame row 0 → GL first row = texture bottom);
    #     v=1 → panel bottom.  This compensates for pygame vs GL y-axis difference
    #     without needing pygame.transform.flip.
    verts = np.array(
      [
        x0, y0, 0.0, 1.0,
        x1, y0, 1.0, 1.0,
        x1, y1, 1.0, 0.0,
        x0, y0, 0.0, 1.0,
        x1, y1, 1.0, 0.0,
        x0, y1, 0.0, 0.0,
      ],
      dtype=np.float32,
    )

    glBindVertexArray(self._vao)
    glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_DYNAMIC_DRAW)
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))
    glEnableVertexAttribArray(1)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

    glDisable(GL_DEPTH_TEST)
    glUseProgram(self._prog)
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, tex)
    glUniform1i(glGetUniformLocation(self._prog, "uTex"), 0)
    glDrawArrays(GL_TRIANGLES, 0, 6)
    glBindVertexArray(0)
    glBindTexture(GL_TEXTURE_2D, 0)
    glUseProgram(0)
    glEnable(GL_DEPTH_TEST)

    glDeleteTextures(1, [tex])

    return active_buttons
