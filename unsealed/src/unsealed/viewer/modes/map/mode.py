"""MapMode — viewer mode for .map files (terrain + object instances + sky)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, cast

import numpy as np

from ..base import AnimationPolicy, BaseMode, RenderExtension
from .camera import MapCamera
from .extensions import SkyExtension, TerrainExtension
from .panels import MapControlPanel, ObjectDetailPanel, ShaderDetailPanel
from .pipeline import MapViewerPipeline
from .scene import MapScene

if TYPE_CHECKING:
  from ...camera import Camera
  from ...hud_types import HudPanel
  from ...scenes import ViewerScene
  from ..context import ModeContext


class MapMode(BaseMode):
  name = "map"
  extensions = (".map",)
  scene_type = MapScene
  animation_policy = AnimationPolicy(auto_play_all=True)

  def __init__(self) -> None:
    self._render_extensions: List[RenderExtension] = [
      SkyExtension(),
      TerrainExtension(),
    ]

  def render_extensions(self) -> "Iterable[RenderExtension]":
    return self._render_extensions

  def decode(self, path: Path, shader_cache: Optional[dict] = None) -> "ViewerScene":
    return MapViewerPipeline().run(path, shader_cache)

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = MapCamera()
    cam.fit_map()
    if isinstance(scene, MapScene) and scene.terrain_heights is not None:
      cam.set_heightmap(scene.terrain_heights, 512, 512)
    return cam

  def build_hud_panels(self, mctx: "ModeContext") -> "List[HudPanel]":
    ctx = mctx.scene_context
    if ctx is None:
      return []
    scene = cast(MapScene, ctx.scene)
    anim = mctx.anim
    selected_idx = mctx.selected_mesh_idx
    panels: "List[HudPanel]" = [MapControlPanel(scene, ctx.path, mctx.q3_enabled)]
    if selected_idx is not None and 0 <= selected_idx < len(scene.meshes):
      mesh = scene.meshes[selected_idx]
      ent_idx = anim.mesh_to_entity.get(selected_idx)
      entity = (
        scene.entities[ent_idx]
        if ent_idx is not None and ent_idx < len(scene.entities)
        else None
      )
      panels.append(ObjectDetailPanel(mesh, entity))
    # Shader-detail viewer stacks under the object panel on the right edge.
    # 20 px gap between the two; ObjectDetailPanel's exact height isn't known
    # here so we use a fixed offset that's a sane stacking distance.
    if mctx.selected_shader is not None:
      panels.append(
        ShaderDetailPanel(
          shader=mctx.selected_shader,
          scroll_offset=mctx.shader_scroll,
          anchor_y=420,
        )
      )
    return panels

  def on_key(self, key: int, mctx: "ModeContext") -> None:
    from pygame.locals import K_i

    if key == K_i:
      mctx.open_inject_dialog()

  def on_mouse_down(
    self, button: int, pos: tuple[int, int], mctx: "ModeContext"
  ) -> None:
    if button == 1:
      mctx.set_lmb_down(pos)

  def on_mouse_up(self, button: int, pos: tuple[int, int], mctx: "ModeContext") -> None:
    if button == 1 and mctx.lmb_down_pos is not None:
      ox, oy = mctx.lmb_down_pos
      cx, cy = pos
      if (cx - ox) ** 2 + (cy - oy) ** 2 <= 25:  # ≤ 5 px radius
        mctx.pick(cx, cy)
      mctx.set_lmb_down(None)

  def on_mouse_motion(self, dx: int, dy: int, mctx: "ModeContext") -> None:
    cam = cast(MapCamera, mctx.camera)
    if mctx.buttons[2]:
      cam.orbit(dx, -dy)
    elif mctx.buttons[0]:
      cam.pan_mouse(dx, -dy)
    elif mctx.buttons[1]:
      cam.pan_mouse(dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, mctx: "ModeContext") -> None:
    cast(MapCamera, mctx.camera).zoom(direction)

  # ── map-specific operations ──────────────────────────────────────────────

  def inject_model(self, path: Path, mctx: "ModeContext") -> None:
    """Inject a .ms1 / .act model into the currently-loaded map at the
    camera's look-at target. No-op if the active scene isn't a MapScene.

    The injected model becomes one more AnimatedEntity in the map scene —
    same animation/render path as any baked-in object.
    """
    from ...scenes import AnimatedEntity
    from ..model.mode import ModelMode

    ctx = mctx.scene_context
    if ctx is None or not isinstance(ctx.scene, MapScene):
      print("[viewer] inject_model: no map loaded")
      return

    map_scene = ctx.scene
    cam = cast(MapCamera, ctx.camera)

    try:
      model_scene = ModelMode().decode(path, mctx._app.shader_cache)
    except Exception as e:
      print(f"[viewer] inject_model decode failed: {e}")
      return

    if not model_scene.entities:  # type: ignore[union-attr]
      print(f"[viewer] inject_model: {path.name} has no entities")
      return

    src_entity = model_scene.entities[0]  # type: ignore[union-attr]

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
    mctx._app.render.renderer.load_scene(map_scene, self.render_extensions())
    mctx._app.reload_animation(map_scene)

    print(
      f"[viewer] injected {path.name} at "
      f"({cam.target[0]:.1f}, {cam.target[1]:.1f}, {cam.target[2]:.1f})"
    )
