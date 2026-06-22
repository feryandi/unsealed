"""AppWorld — component registry and host for Mode plugins.

State-mutating helpers (animation, picking, mode-specific toggles) are
public so that Mode.draw_hud can call them directly when the user clicks
an imgui widget. There's no action-dispatch layer — immediate-mode UI
mutates state inline.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

from ..modes import MODES, MapScene, MenScene, ModeContext, ModelScene, SprScene
from ..modes.map.camera import MapCamera
from ..rendering.imgui_renderer import ImGuiRenderer
from .components import (
    InputComponent,
    RenderComponent,
    SceneComponent,
    SpakComponent,
    WindowComponent,
)
from .systems import AnimationSystem, InputSystem, LoadSystem, UpdateSystem

if TYPE_CHECKING:
    pass


class AppWorld:
    def __init__(self) -> None:
        self.window = WindowComponent()
        self.inp = InputComponent()
        self.render = RenderComponent()
        self.scene = SceneComponent()
        self.spak = SpakComponent()

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
        self._load_sys.load(path, self)

    def open_dialog(self) -> None:
        self._load_sys.open_dialog(self)

    def open_spak_entry(self, rel: Path) -> None:
        """Load a file from the currently-browsed .spak extraction."""
        if self.spak.root is None:
            return
        self.load(self.spak.root / rel)

    def close_spak(self) -> None:
        self.spak.active = False

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
