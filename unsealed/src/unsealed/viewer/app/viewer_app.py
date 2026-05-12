"""Main viewer application — thin pygame shell."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pygame

from ..modes.image.camera import ImageCamera
from ..modes.map.camera import MapCamera
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
        world.window.font = pygame.font.SysFont(
            "malgunsl,malgun gothic,gulim,dotum,noto sans cjk kr,consolas,arial",
            14,
        )
        world.window.width = self.WIDTH
        world.window.height = self.HEIGHT

        if self._initial_file is not None:
            world.load(self._initial_file)

        world.window.running = True
        clock = pygame.time.Clock()
        _time = 0.0

        while world.window.running:
            dt = clock.tick(60) / 1000.0
            _time += dt
            world.process_events()
            world.update(dt)

            win = world.window
            scene = world.scene
            rend = world.render
            cam: OrbitCamera | ImageCamera | MapCamera
            if scene.context is not None:
                cam = scene.context.camera  # type: ignore[assignment]
            else:
                cam = OrbitCamera()
            rend.renderer.render(
                RenderContext(
                    camera=cam,
                    width=win.width,
                    height=win.height,
                    wireframe=rend.wireframe,
                    bone_matrices=scene.anim.bone_matrices,
                    map_bone_matrices=scene.anim.map_bone_matrices,
                    map_node_matrices={
                        **scene.anim.map_node_matrices,
                        **scene.anim.node_matrices,
                    },
                    selected_mesh_idx=scene.selected_mesh_idx,
                    time=_time,
                    q3_enabled=rend.q3_enabled,
                )
            )
            world.render.hud_buttons = rend.renderer.render_hud(
                world.build_hud_panels(),
                win.font,
                win.width,
                win.height,
                pygame.mouse.get_pos(),
            )
            pygame.display.flip()

        world._set_capture(False)
        world.render.renderer.cleanup()
        pygame.quit()
