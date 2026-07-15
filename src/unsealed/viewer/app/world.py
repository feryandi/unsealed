"""AppWorld — component registry and host for Mode plugins.

State-mutating helpers (animation, picking, mode-specific toggles) are
public so that Mode.draw_hud can call them directly when the user clicks
an imgui widget. There's no action-dispatch layer — immediate-mode UI
mutates state inline.
"""

from __future__ import annotations

import threading
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple, cast

from ..modes import MODES, MapScene, MenScene, ModeContext, ModelScene, SprScene
from ..modes.map.camera import MapCamera
from ..rendering.imgui_renderer import ImGuiRenderer
from .components import (
    InputComponent,
    RenderComponent,
    SceneComponent,
    SpakComponent,
    StatusComponent,
    WindowComponent,
)
from .systems import AnimationSystem, InputSystem, LoadSystem, UpdateSystem

if TYPE_CHECKING:
    from .context import ViewerContext


class AppWorld:
    def __init__(self) -> None:
        self.window = WindowComponent()
        self.inp = InputComponent()
        self.render = RenderComponent()
        self.scene = SceneComponent()
        self.spak = SpakComponent()
        self.status = StatusComponent()

        # Background-load plumbing. The heavy CPU work (decode + .spak
        # materialization) runs on a worker thread so the UI keeps drawing
        # the loading spinner; the GL upload is finalized on the main thread
        # in `poll_load`. One load in flight at a time.
        self._bg_thread: Optional[threading.Thread] = None
        self._bg_result: Optional[Tuple["ViewerContext", Path]] = None
        self._bg_error: Optional[Exception] = None

        # .spak mount worker: opening an archive resolves keys for it and
        # every sibling (cracking a private-server key can take ~10s), which
        # is too slow to run inline — it froze the UI. Runs off-thread with
        # status + progress updates.
        self._spak_path: Optional[Path] = None
        self._spak_thread: Optional[threading.Thread] = None
        self._spak_mount_result: Any = None  # SpakSource or Exception

        # Shader cache: filled once per unique directory, reused across loads
        self.shader_cache: Dict[str, Any] = {}
        self._shader_dir: Optional[Path] = None

        self._anim_sys = AnimationSystem()
        self._input_sys = InputSystem()
        self._load_sys = LoadSystem()
        self._update_sys = UpdateSystem()

        # ImGui owner. `viewer_app.run()` calls `imgui.init(w, h)` after
        # pygame.display.set_mode; from then on InputSystem feeds events
        # into it and Mode.draw_hud emits widgets between new_frame/render.
        self.imgui = ImGuiRenderer()

    # ── ModeContext factory ────────────────────────────────────────────────────

    def mode_context(self) -> ModeContext:
        """Build a fresh ModeContext snapshot for a Mode call."""
        ctx = self.scene.context
        camera = ctx.camera if ctx is not None else None
        return ModeContext(
            camera=camera,  # type: ignore[arg-type]
            width=self.window.width,
            height=self.window.height,
            buttons=self.inp.btn,
            lmb_down_pos=self.inp.lmb_down_pos,
            scene_context=ctx,
            anim=self.scene.anim,
            selected_mesh_idx=self.scene.selected_mesh_idx,
            q3_enabled=self.render.q3_enabled,
            wireframe=self.render.wireframe,
            selected_shader=self.scene.selected_shader,
            _app=self,
        )

    # ── animation helpers ─────────────────────────────────────────────────────

    def anim_toggle_play(self) -> None:
        self._anim_sys.toggle_play(self.scene.anim)

    def anim_stop(self) -> None:
        self._anim_sys.stop(self.scene.anim)

    def anim_select(self, idx: int) -> None:
        ctx = self.scene.context
        if ctx is not None and isinstance(ctx.scene, ModelScene):
            self._anim_sys.select(self.scene.anim, ctx.scene, idx)

    def anim_scrub(self, delta: float) -> None:
        ctx = self.scene.context
        if ctx is not None and isinstance(ctx.scene, ModelScene):
            self._anim_sys.scrub(self.scene.anim, ctx.scene, delta)

    def reload_animation(self, scene: object) -> None:
        """Rebuild animation state after the scene's entities have changed
        (e.g. model injection into a map)."""
        self._anim_sys.load(self.scene.anim, scene)

    # ── mode-specific state helpers (called inline from draw_hud) ─────────────

    def toggle_q3(self) -> None:
        self.render.q3_enabled = not self.render.q3_enabled

    def select_shader(self, shader: object) -> None:
        """Toggle the shader-detail view for `shader`. Selecting the same
        shader twice closes it."""
        if shader is None:
            return
        if self.scene.selected_shader is shader:
            self.scene.selected_shader = None
        else:
            self.scene.selected_shader = shader

    def close_shader(self) -> None:
        self.scene.selected_shader = None

    def select_spr_entry(self, atlas_idx: int, sprite_idx: int) -> None:
        """Update SPR selection. `sprite_idx == FULL_ATLAS_IDX (-1)` selects
        the whole atlas; otherwise it must be one of the cropped-sprite
        indices the .spr declared for that atlas."""
        ctx = self.scene.context
        if ctx is None or not isinstance(ctx.scene, SprScene):
            return
        scene = ctx.scene
        if not (0 <= atlas_idx < len(scene.atlases)):
            return
        scene.selected_atlas = atlas_idx
        atlas_name = scene.atlases[atlas_idx].name
        if (atlas_name, sprite_idx) in scene.sprite_refs:
            scene.selected_sprite = sprite_idx

    def close_men_detail(self) -> None:
        ctx = self.scene.context
        if ctx is None or not isinstance(ctx.scene, MenScene):
            return
        ctx.scene.selected_element_idx = None

    def select_men_element(self, idx: Optional[int]) -> None:
        """Set or clear the selected men element."""
        ctx = self.scene.context
        if ctx is None or not isinstance(ctx.scene, MenScene):
            return
        scene = ctx.scene
        if idx is None or not (0 <= idx < len(scene.elements)):
            scene.selected_element_idx = None
        else:
            scene.selected_element_idx = idx

    def set_men_state(self, elem_idx: int, state: str) -> None:
        ctx = self.scene.context
        if ctx is None or not isinstance(ctx.scene, MenScene):
            return
        elements = ctx.scene.elements
        if not (0 <= elem_idx < len(elements)):
            return
        el = elements[elem_idx]
        if state in el.state_refs:
            el.active_state = state

    def toggle_men_hide(self, elem_idx: int) -> None:
        ctx = self.scene.context
        if ctx is None or not isinstance(ctx.scene, MenScene):
            return
        scene = ctx.scene
        if not (0 <= elem_idx < len(scene.elements)):
            return
        scene.elements[elem_idx].hidden = not scene.elements[elem_idx].hidden
        scene.recompute_hidden_set()

    # ── input / picking helpers ───────────────────────────────────────────────

    def set_capture(self, on: bool) -> None:
        self._input_sys.set_capture(self.inp, on)

    def pick_at(self, mx: int, my: int) -> None:
        """Ray-cast pick at screen position (mx, my) and update selection."""
        ctx = self.scene.context
        if ctx is None or not isinstance(ctx.scene, MapScene):
            return
        cam = cast(MapCamera, ctx.camera)  # MapScene always uses MapCamera
        aspect = self.window.width / max(self.window.height, 1)
        view = cam.view_matrix()
        proj = cam.projection_matrix(aspect, self.window.width, self.window.height)
        hit = self.render.renderer.pick(mx, my, self.window.width, self.window.height, view, proj)
        self.scene.selected_mesh_idx = None if hit == self.scene.selected_mesh_idx else hit

    # ── system dispatch ────────────────────────────────────────────────────────

    def register_render_extensions(self) -> None:
        """Hand the renderer the union of RenderExtensions from every registered Mode.

        Called after `Renderer.init()` so the renderer can compile their
        shaders once and own their lifecycle without importing modes/.
        """
        extensions = []
        seen: set = set()
        for mode in MODES:
            for ext in mode.render_extensions():
                if id(ext) in seen:
                    continue
                seen.add(id(ext))
                extensions.append(ext)
        self.render.renderer.register_extensions(extensions)

    def process_events(self) -> None:
        self._input_sys.process(self)

    def update(self, dt: float) -> None:
        self._update_sys.update(self, dt)

    def load(self, path: Path) -> None:
        """Synchronous load (startup / scripting)."""
        self._load_sys.load(path, self)

    def open_dialog(self) -> None:
        self._load_sys.open_dialog(self)

    def open_spak_entry(self, rel: Path) -> None:
        """Load a browsed .spak entry — decrypted on demand from the source."""
        source = self._load_sys.active_spak_source()
        if source is None:
            return
        from unsealed.reader.vfs import Resource

        res = Resource(source, str(rel).replace("\\", "/"))

        def work() -> Tuple["ViewerContext", "Resource"]:
            return self._load_sys.decode_ctx(res, self), res

        self._start_load(work, f"Loading {res.name}…")

    def close_spak(self) -> None:
        self.spak.active = False

    # ── .spak key recovery ──────────────────────────────────────────────────────

    def retry_spak(self) -> None:
        """Re-mount the current .spak (e.g. after opening a sibling that
        cracked the shared key)."""
        if self._spak_path is not None:
            self.open_spak_async(self._spak_path)

    # ── background loading ──────────────────────────────────────────────────────

    def request_load(self, path: Path) -> None:
        """Load a file asynchronously (off-thread decode, on-thread GL upload).

        A .spak is mounted on a worker thread too (resolving its keys can
        be slow); entries are still decrypted only when opened later."""
        if path.suffix.lower() == ".spak":
            self.open_spak_async(path)
            return
        from unsealed.reader.vfs import Resource

        res = Resource.for_disk_file(path)
        self._start_load(
            lambda: (self._load_sys.decode_ctx(res, self), res),
            f"Loading {path.name}…",
        )

    def open_spak_async(self, path: Path) -> None:
        """Mount a .spak on a worker thread, reporting progress on the status bar.

        Resolving the archive's key (deriving it, trying stored keys, or
        cracking a private-server key with the bundled known-plaintext
        attack) can take a while; doing it inline froze the whole viewer.
        """
        if self.status.loading or self._spak_thread is not None:
            return
        self._load_sys.reset_spak(self, path)
        self.spak.active = False  # hide any prior browser while mounting
        self.status.loading = True
        self.status.message = f"Mounting {path.name}…"
        self._spak_mount_result = None
        self._spak_thread = threading.Thread(
            target=self._run_spak_mount, args=(path,), daemon=True
        )
        self._spak_thread.start()

    def _run_spak_mount(self, path: Path) -> None:
        from unsealed.reader.utils.spak import SpakPasswordError

        def on_status(msg: str) -> None:
            self.status.message = msg

        def on_progress(fraction: float, label: str) -> None:
            self.spak.progress = fraction
            self.spak.recover_status = label

        try:
            self._spak_mount_result = self._load_sys.mount(path, on_status, on_progress)
        except SpakPasswordError as e:
            self._spak_mount_result = e  # expected outcome, not a crash
        except Exception as e:
            self._spak_mount_result = e
            traceback.print_exc()

    def poll_spak_mount(self) -> None:
        """Finalize a finished .spak mount on the main thread."""
        if self._spak_thread is None or self._spak_thread.is_alive():
            return
        self._spak_thread = None
        result = self._spak_mount_result
        self._spak_mount_result = None
        self.status.loading = False
        self.spak.progress = None
        self.spak.recover_status = None
        path = self._spak_path
        if path is None:
            return
        self._load_sys.finish_spak(self, path, result)
        if self.spak.needs_key:
            self.status.message = f"{path.name}: needs a decryption key"
        elif self.spak.error:
            self.status.message = f"Error: {self.spak.error}"
        else:
            self.status.message = path.name

    def _start_load(
        self, work: Callable[[], Tuple["ViewerContext", Path]], message: str
    ) -> None:
        if self.status.loading:
            return  # one load at a time
        self.status.loading = True
        self.status.message = message
        self._bg_result = None
        self._bg_error = None
        self._bg_thread = threading.Thread(
            target=self._run_load, args=(work,), daemon=True
        )
        self._bg_thread.start()

    def _run_load(
        self, work: Callable[[], Tuple["ViewerContext", Path]]
    ) -> None:
        try:
            self._bg_result = work()
        except Exception as e:  # surfaced on the main thread in poll_load
            self._bg_error = e
            traceback.print_exc()

    def poll_load(self) -> None:
        """Finalize a finished background load on the main thread (GL upload)."""
        if not self.status.loading:
            return
        if self._bg_thread is not None and self._bg_thread.is_alive():
            return
        self._bg_thread = None
        result, error = self._bg_result, self._bg_error
        self._bg_result = self._bg_error = None
        self.status.loading = False

        if error is not None:
            self.status.message = f"Error: {error}"
            return
        if result is not None:
            ctx, path = result
            try:
                self._load_sys.finalize(ctx, path, self)
                self.status.message = path.name
            except Exception as e:
                print(f"[viewer] finalize error: {e}")
                traceback.print_exc()
                self.status.message = f"Error: {e}"

    def open_inject_dialog(self) -> None:
        """Pick a model file and ask the active Mode to inject it."""
        path = self._load_sys.ask_model_file(self)
        if path is None:
            return
        ctx = self.scene.context
        if ctx is None:
            return
        inject = getattr(ctx.mode, "inject_model", None)
        if inject is None:
            print(f"[viewer] active mode {ctx.mode.name!r} does not support inject_model")
            return
        inject(path, self.mode_context())
