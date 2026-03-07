"""AppWorld — component registry and Protocol interface for scenes."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from ..camera import MapCamera
from ..rendering import HudAction
from ..scene import MapScene, ModelScene
from .components import InputComponent, RenderComponent, SceneComponent, WindowComponent
from .systems import AnimationSystem, HudSystem, InputSystem, LoadSystem, UpdateSystem

if TYPE_CHECKING:
    from .components.animation import AnimationComponent
    from ..camera import Camera
    from ..rendering import HudPanel


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

    # ── Protocol interface (used by scenes/ configs) ──────────────────────────

    @property
    def _camera(self) -> "Camera":
        return self.scene.context.camera  # type: ignore[union-attr]

    @property
    def _btn(self) -> List[bool]:
        return self.inp.btn

    @property
    def _lmb_down_pos(self) -> Optional[tuple[int, int]]:
        return self.inp.lmb_down_pos

    @_lmb_down_pos.setter
    def _lmb_down_pos(self, value: Optional[tuple[int, int]]) -> None:
        self.inp.lmb_down_pos = value

    @property
    def _wireframe(self) -> bool:
        return self.render.wireframe

    @_wireframe.setter
    def _wireframe(self, value: bool) -> None:
        self.render.wireframe = value

    @property
    def _anim(self) -> "AnimationComponent":
        return self.scene.anim

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
            case _:
                pass

    @property
    def _width(self) -> int:
        return self.window.width

    @property
    def _height(self) -> int:
        return self.window.height

    def _set_capture(self, on: bool) -> None:
        self._input_sys.set_capture(self.inp, on)

    def _open_dialog(self) -> None:
        self._load_sys.open_dialog(self)

    def _do_pick(self, mx: int, my: int) -> None:
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

    def process_events(self) -> None:
        self._input_sys.process(self)

    def update(self, dt: float) -> None:
        self._update_sys.update(self, dt)

    def load(self, path: Path) -> None:
        self._load_sys.load(path, self)

    def open_dialog(self) -> None:
        self._load_sys.open_dialog(self)

    def build_hud_panels(self) -> "List[HudPanel]":
        return self._hud_sys.build(self.scene, self.render.q3_enabled)
