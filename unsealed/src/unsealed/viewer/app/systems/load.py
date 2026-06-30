"""LoadSystem — file loading and open-dialog logic."""

from __future__ import annotations

import tkinter as tk
import traceback
from pathlib import Path, PurePosixPath
from tkinter import filedialog
from typing import TYPE_CHECKING, Dict, Optional

import pygame

from ...modes import MODES, ImageScene, MenScene, SprScene
from ....vfs import DiskSource, Resource
from ....vfs.spak_source import SpakSource
from ..context import ViewerContext

if TYPE_CHECKING:
    from ..world import AppWorld

_TITLE = "Unsealed — 3D Viewer"

# Extensions the viewer can open, gathered from every registered Mode.
_VIEWABLE_EXTS = frozenset(ext for m in MODES for ext in m.extensions)


class LoadSystem:
    def __init__(self) -> None:
        # Resolved .spak path -> its mounted source. Reusing the mount keeps
        # the decrypted-bytes cache warm when an archive is reopened.
        self._sources: Dict[Path, SpakSource] = {}
        self._active: Optional[SpakSource] = None

    def load(self, path: Path, world: "AppWorld") -> None:
        """Synchronous load (startup / injection). UI loads go async via
        world.request_load → decode_ctx (off-thread) + finalize (main)."""
        if path.suffix.lower() == ".spak":
            self.open_spak(path, world)
            return
        try:
            res = Resource.for_disk_file(path)
            self.finalize(self.decode_ctx(res, world), res, world)
        except Exception as e:
            print(f"[viewer] error: {e}")
            traceback.print_exc()

    def decode_ctx(self, res: Resource, world: "AppWorld") -> ViewerContext:
        """CPU-only: load shaders + decode the resource into a ViewerContext.

        No GL calls here, so it is safe to run on a background thread. The
        shader cache is keyed by the source (a disk dir or a mounted .spak)
        so it is reused across files from the same source.
        """
        from ...shader import load_shaders

        key = res.source.root if isinstance(res.source, DiskSource) else res.source
        if key != world._shader_dir:
            world.shader_cache = load_shaders(res.source)
            world._shader_dir = key
        return ViewerContext.load(
            res, world.window.width, world.window.height, world.shader_cache
        )

    def finalize(self, ctx: ViewerContext, res: Resource, world: "AppWorld") -> None:
        """Main-thread: upload the decoded scene to the GPU + wire state."""
        world.scene.context = ctx
        world.scene.current_path = res
        world.render.renderer.load_scene(ctx.scene, ctx.mode.render_extensions())
        world.scene.selected_mesh_idx = None
        world.scene.selected_shader = None
        if not isinstance(ctx.scene, (ImageScene, SprScene, MenScene)):
            world._anim_sys.load(world.scene.anim, ctx.scene)
        pygame.display.set_caption(f"{_TITLE} — {res.name}")

    def open_dialog(self, world: "AppWorld") -> None:
        self._release_input(world)
        path = self._ask_file(
            "Open Game File",
            [
                ("Game files", "*.ms1 *.act *.map *.tex *.te1 *.spr *.men *.spak"),
                ("Seal Mesh", "*.ms1"),
                ("Actor File", "*.act"),
                ("Map File", "*.map"),
                ("Texture File", "*.tex *.te1"),
                ("Sprite Atlas", "*.spr"),
                ("Menu File", "*.men"),
                ("Packed Archive", "*.spak"),
                ("All files", "*.*"),
            ],
        )
        if path is not None:
            world.request_load(path)

    def open_spak(self, path: Path, world: "AppWorld") -> None:
        """Mount a .spak and show its browser — instant, nothing decrypted yet."""
        spak = world.spak
        spak.error = None
        try:
            source = self._mount_spak(path)
        except Exception as e:
            print(f"[viewer] spak error: {e}")
            traceback.print_exc()
            self._active = None
            spak.active = True
            spak.archive_name = path.name
            spak.entries = []
            spak.error = str(e)
            return

        self._active = source
        spak.active = True
        spak.archive_name = path.name
        spak.entries = sorted(
            PurePosixPath(n)
            for n in source.primary_names()
            if PurePosixPath(n).suffix.lower() in _VIEWABLE_EXTS
        )
        spak.filter_text = ""

    def active_spak_source(self) -> Optional[SpakSource]:
        """The mounted source for the currently-browsed .spak (or None)."""
        return self._active

    def _mount_spak(self, path: Path) -> SpakSource:
        key = path.resolve()
        source = self._sources.get(key)
        if source is None:
            source = SpakSource(path)
            self._sources[key] = source
        return source

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
