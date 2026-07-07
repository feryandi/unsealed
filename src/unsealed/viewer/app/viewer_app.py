"""Main viewer application — thin pygame shell."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pygame

from ..camera import Camera
from ..modes.model.camera import OrbitCamera
from ..rendering import RenderContext
from .world import AppWorld


class ViewerApp:
  WIDTH = 1280
  HEIGHT = 720
  TITLE = "Unsealed — 3D Viewer"

  def __init__(self, initial_file: Optional[Path] = None) -> None:
    self._world = AppWorld()
    self._initial_file = initial_file

  def run(self) -> None:
    pygame.init()
    pygame.font.init()

    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(
      pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE
    )
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)

    pygame.display.set_mode(
      (self.WIDTH, self.HEIGHT),
      pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE,
    )
    pygame.display.set_caption(self.TITLE)

    world = self._world
    world.render.renderer.init()
    world.register_render_extensions()
    world.window.width = self.WIDTH
    world.window.height = self.HEIGHT

    # ImGui setup — must come AFTER pygame.display.set_mode (GL context
    # exists) but the imgui renderer is owned by AppWorld so the input
    # system + modes can reach it for `want_capture_*` gating.
    world.imgui.init(self.WIDTH, self.HEIGHT)

    if self._initial_file is not None:
      world.load(self._initial_file)

    world.window.running = True
    clock = pygame.time.Clock()
    _time = 0.0

    while world.window.running:
      dt = clock.tick(60) / 1000.0
      _time += dt
      world.process_events()
      world.poll_load()  # finalize a finished background load (GL on main thread)
      world.update(dt)

      win = world.window
      scene = world.scene
      rend = world.render
      cam: Camera
      if scene.context is not None:
        cam = scene.context.camera
      else:
        cam = OrbitCamera()
      rend.renderer.render(
        RenderContext(
          camera=cam,
          width=win.width,
          height=win.height,
          wireframe=rend.wireframe,
          bone_matrices=scene.anim.bone_matrices,
          node_matrices=scene.anim.node_matrices,
          selected_mesh_idx=scene.selected_mesh_idx,
          time=_time,
          q3_enabled=rend.q3_enabled,
        )
      )

      # HUD pass — fully driven by imgui. Modes (or the welcome fallback)
      # call begin/widget/end inline. State mutations happen via direct
      # calls on AppWorld; no action dispatch.
      world.imgui.new_frame()
      if scene.context is not None:
        scene.context.mode.draw_hud(world)
      else:
        _draw_welcome(world)
      if world.spak.active:
        _draw_spak_browser(world)
      _draw_status_bar(world)
      world.imgui.render()

      pygame.display.flip()

    world.set_capture(False)
    world.imgui.shutdown()
    world.render.renderer.cleanup()
    pygame.quit()


_SPINNER = "|/-\\"
_STATUS_BAR_H = 26


def _draw_status_bar(world: AppWorld) -> None:
  """Sticky one-row bar pinned to the bottom (loading spinner / status)."""
  from imgui_bundle import imgui

  w, h = world.window.width, world.window.height
  imgui.set_next_window_pos((0, h - _STATUS_BAR_H))
  imgui.set_next_window_size((w, _STATUS_BAR_H))
  flags = (
    imgui.WindowFlags_.no_title_bar.value
    | imgui.WindowFlags_.no_resize.value
    | imgui.WindowFlags_.no_move.value
    | imgui.WindowFlags_.no_scrollbar.value
    | imgui.WindowFlags_.no_saved_settings.value
    | imgui.WindowFlags_.no_collapse.value
    | imgui.WindowFlags_.no_nav.value
    | imgui.WindowFlags_.no_bring_to_front_on_focus.value
  )
  imgui.begin("##status_bar", None, flags)
  st = world.status
  if st.loading:
    frame = _SPINNER[(pygame.time.get_ticks() // 120) % len(_SPINNER)]
    imgui.text(f"{frame}  {st.message}")
  else:
    imgui.text(st.message or "Ready")
  imgui.end()


def _draw_welcome(world: AppWorld) -> None:
  """Welcome window shown when no scene is loaded."""
  from imgui_bundle import imgui

  imgui.set_next_window_pos((10, 10), imgui.Cond_.first_use_ever.value)
  imgui.begin("Unsealed Viewer")
  imgui.text("Unsealed 3D Viewer")
  imgui.separator()
  if imgui.button("Open File"):
    world.open_dialog()
  imgui.end()


def _draw_spak_browser(world: AppWorld) -> None:
  """Browser listing the viewable files inside an opened .spak."""
  from imgui_bundle import imgui

  spak = world.spak
  imgui.set_next_window_pos((10, 320), imgui.Cond_.first_use_ever.value)
  imgui.set_next_window_size((300, 380), imgui.Cond_.first_use_ever.value)
  expanded, keep_open = imgui.begin(f"Archive: {spak.archive_name}", True)
  if not keep_open:
    world.close_spak()
  if expanded:
    if spak.error is not None:
      imgui.text_wrapped(f"Failed to open archive:\n{spak.error}")
    elif not spak.entries:
      imgui.text_wrapped("No viewable files in this archive.")
    else:
      imgui.text(f"{len(spak.entries)} viewable file(s)")
      _, spak.filter_text = imgui.input_text("Filter", spak.filter_text)
      imgui.separator()
      needle = spak.filter_text.lower()
      imgui.begin_child("spak_entries")
      for rel in spak.entries:
        label = rel.as_posix()
        if needle and needle not in label.lower():
          continue
        if imgui.selectable(label, False)[0]:
          world.open_spak_entry(rel)
      imgui.end_child()
  imgui.end()
