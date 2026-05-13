"""LoadSystem — file loading and open-dialog logic."""

from __future__ import annotations

import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING, Optional

import pygame

from ...modes import ImageScene
from ..context import ViewerContext

if TYPE_CHECKING:
    from ..world import AppWorld

_TITLE = "Unsealed — 3D Viewer"


class LoadSystem:
    def load(self, path: Path, world: "AppWorld") -> None:
        try:
            if path.parent != world._shader_dir:
                from ...shader import load_shaders
                world.shader_cache = load_shaders(path.parent)
                world._shader_dir = path.parent
            ctx = ViewerContext.load(path, world.window.width, world.window.height,
                                     world.shader_cache)
            world.scene.context = ctx
            world.scene.current_path = path
            world.render.renderer.load_scene(
                ctx.scene, ctx.mode.render_extensions()
            )
            world.scene.selected_mesh_idx = None
            if not isinstance(ctx.scene, ImageScene):
                world._anim_sys.load(world.scene.anim, ctx.scene)
            pygame.display.set_caption(f"{_TITLE} — {path.name}")

        except Exception as e:
            print(f"[viewer] error: {e}")
            traceback.print_exc()

    def open_dialog(self, world: "AppWorld") -> None:
        self._release_input(world)
        path = self._ask_file(
            "Open Game File",
            [
                ("Game files", "*.ms1 *.act *.map *.tex *.te1"),
                ("Seal Mesh", "*.ms1"),
                ("Actor File", "*.act"),
                ("Map File", "*.map"),
                ("Texture File", "*.tex *.te1"),
                ("All files", "*.*"),
            ],
        )
        if path is not None:
            self.load(path, world)

    def ask_model_file(self, world: "AppWorld") -> Optional[Path]:
        """Modal file picker filtered to model files (.ms1 / .act)."""
        self._release_input(world)
        return self._ask_file(
            "Select Model File",
            [
                ("Model files", "*.ms1 *.act"),
                ("Seal Mesh", "*.ms1"),
                ("Actor File", "*.act"),
                ("All files", "*.*"),
            ],
        )

    # ── private ────────────────────────────────────────────────────────────

    @staticmethod
    def _release_input(world: "AppWorld") -> None:
        """Release mouse capture and clear pressed button state before a modal dialog."""
        inp = world.inp
        if inp.captured:
            inp.captured = False
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
        inp.btn = [False, False, False]

    @staticmethod
    def _ask_file(title: str, filetypes: list) -> Optional[Path]:
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path_str = filedialog.askopenfilename(title=title, filetypes=filetypes)
            root.destroy()
            return Path(path_str) if path_str else None
        except Exception as e:
            print(f"[viewer] file dialog error: {e}")
            return None
