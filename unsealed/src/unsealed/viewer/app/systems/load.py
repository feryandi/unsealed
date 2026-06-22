"""LoadSystem — file loading and open-dialog logic."""

from __future__ import annotations

import atexit
import shutil
import tempfile
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING, Dict, Optional

import pygame

from ...modes import MODES, ImageScene, MenScene, SprScene
from ..context import ViewerContext

if TYPE_CHECKING:
    from ..world import AppWorld

_TITLE = "Unsealed — 3D Viewer"

# Extensions the viewer can open, gathered from every registered Mode.
_VIEWABLE_EXTS = frozenset(ext for m in MODES for ext in m.extensions)


class LoadSystem:
    def __init__(self) -> None:
        # Resolved .spak path -> temp dir it was extracted into. Lets us
        # skip re-extracting an archive the user reopens this session.
        self._spak_roots: Dict[Path, Path] = {}

    def load(self, path: Path, world: "AppWorld") -> None:
        if path.suffix.lower() == ".spak":
            self.open_spak(path, world)
            return
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
            world.scene.selected_shader = None
            if not isinstance(ctx.scene, (ImageScene, SprScene, MenScene)):
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
            self.load(path, world)

    def open_spak(self, path: Path, world: "AppWorld") -> None:
        """Extract a .spak (once per session); open the file browser."""
        spak = world.spak
        spak.error = None
        try:
            root = self._extract_spak(path)
        except Exception as e:
            print(f"[viewer] spak error: {e}")
            traceback.print_exc()
            spak.active = True
            spak.archive_name = path.name
            spak.root = None
            spak.entries = []
            spak.error = str(e)
            return

        entries = sorted(
            p.relative_to(root)
            for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in _VIEWABLE_EXTS
        )
        spak.active = True
        spak.archive_name = path.name
        spak.root = root
        spak.entries = entries
        spak.filter_text = ""

    def _extract_spak(self, path: Path) -> Path:
        """Extract every entry to a temp dir, preserving sub-paths."""
        key = path.resolve()
        cached = self._spak_roots.get(key)
        if cached is not None and cached.exists():
            return cached

        from ....formats.spak.decoder import SpakDecoder

        directory = SpakDecoder(path).decode()
        root = Path(tempfile.mkdtemp(prefix="unsealed_spak_"))
        atexit.register(shutil.rmtree, root, ignore_errors=True)
        for blob in directory.list:
            name = blob.name or ""
            if blob.extension:
                name = f"{name}.{blob.extension}"
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob.value or b"")
        self._spak_roots[key] = root
        return root

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
