"""AppWorld — component registry and Protocol interface for scenes."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from ..modes import MapScene, ModelScene
from ..modes.map.camera import MapCamera
from ..rendering import HudAction
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

    def open_inject_dialog(self) -> None:
        self._load_sys.open_inject_dialog(self)

    def inject_model(self, path: Path) -> None:
        """Inject a .ms1 / .act model into the currently-loaded map at the
        camera's look-at target. No-op if no map is loaded.

        The model becomes one more AnimatedEntity in the map scene — same
        animation/render path as any baked-in object — proving the Phase 3
        entity model supports cross-mode composition.
        """
        import numpy as np

        from ..modes.map.camera import MapCamera
        from ..modes.model.mode import ModelMode
        from ..scenes import AnimatedEntity

        ctx = self.scene.context
        if ctx is None or not isinstance(ctx.scene, MapScene):
            print("[viewer] inject_model: no map loaded")
            return

        map_scene = ctx.scene
        cam = cast(MapCamera, ctx.camera)

        try:
            model_scene = ModelMode().decode(path, self.shader_cache)
        except Exception as e:
            print(f"[viewer] inject_model decode failed: {e}")
            return

        if not model_scene.entities:
            print(f"[viewer] inject_model: {path.name} has no entities")
            return

        src_entity = model_scene.entities[0]

        # Placement: translate to camera target (already terrain-clamped by MapCamera).
        placement = np.identity(4, dtype=np.float32)
        placement[0, 3] = float(cam.target[0])
        placement[1, 3] = float(cam.target[1])
        placement[2, 3] = float(cam.target[2])
        inst_arr = np.array([placement], dtype=np.float32)

        injected_meshes = []
        for mesh in src_entity.meshes:
            mesh.instance_matrices = inst_arr
            map_scene.meshes.append(mesh)
            injected_meshes.append(mesh)

        map_scene.entities.append(
            AnimatedEntity(
                name=path.stem,
                meshes=injected_meshes,
                skeleton=src_entity.skeleton,
                animation_groups=src_entity.animation_groups,
                source_file=path.name,
            )
        )

        # Re-upload scene to GPU and rebuild animation state for new entities.
        self.render.renderer.load_scene(map_scene)
        self._anim_sys.load(self.scene.anim, map_scene)

        print(
            f"[viewer] injected {path.name} at "
            f"({cam.target[0]:.1f}, {cam.target[1]:.1f}, {cam.target[2]:.1f})"
        )

    def build_hud_panels(self) -> "List[HudPanel]":
        return self._hud_sys.build(self.scene, self.render.q3_enabled)
