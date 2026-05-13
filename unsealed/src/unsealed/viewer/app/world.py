"""AppWorld — component registry and host for Mode plugins."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from ..hud_types import HudAction
from ..modes import MODES, MapScene, ModeContext, ModelScene
from ..modes.map.camera import MapCamera
from .components import InputComponent, RenderComponent, SceneComponent, WindowComponent
from .systems import AnimationSystem, HudSystem, InputSystem, LoadSystem, UpdateSystem

if TYPE_CHECKING:
    from ..hud_types import HudPanel


class AppWorld:
    def __init__(self) -> None:
        self.window = WindowComponent()
        self.inp = InputComponent()
        self.render = RenderComponent()
        self.scene = SceneComponent()

        # Shader cache: filled once per unique directory, reused across loads
        self.shader_cache: Dict[str, Any] = {}
        self._shader_dir: Optional[Path] = None

        self._anim_sys = AnimationSystem()
        self._input_sys = InputSystem()
        self._hud_sys = HudSystem()
        self._load_sys = LoadSystem()
        self._update_sys = UpdateSystem()

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
            shader_scroll=self.scene.shader_scroll,
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

    def dispatch_action(self, action: str, data: object = None) -> None:
        """Dispatch a HUD button action by name."""
        match action:
            case HudAction.OPEN:
                self.open_dialog()
            case HudAction.PLAY:
                self.anim_toggle_play()
            case HudAction.STOP:
                self.anim_stop()
            case HudAction.SELECT_ANIM:
                if isinstance(data, int):
                    self.anim_select(data)
            case HudAction.TOGGLE_Q3:
                self.render.q3_enabled = not self.render.q3_enabled
            case HudAction.SELECT_SHADER:
                self._select_shader(data)
            case HudAction.SCROLL_SHADER:
                if isinstance(data, int) and self.scene.selected_shader is not None:
                    self.scene.shader_scroll = max(0, self.scene.shader_scroll + data)
            case HudAction.CLOSE_SHADER:
                self.scene.selected_shader = None
                self.scene.shader_scroll = 0
            case _:
                pass

    def _select_shader(self, shader: object) -> None:
        """Toggle the shader-detail panel for `shader`. Same shader clicked twice closes it."""
        if shader is None:
            return
        current = self.scene.selected_shader
        if current is not None and current is shader:
            self.scene.selected_shader = None
            self.scene.shader_scroll = 0
        else:
            self.scene.selected_shader = shader
            self.scene.shader_scroll = 0

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
        self._load_sys.load(path, self)

    def open_dialog(self) -> None:
        self._load_sys.open_dialog(self)

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

    def build_hud_panels(self) -> "List[HudPanel]":
        return self._hud_sys.build(self)
