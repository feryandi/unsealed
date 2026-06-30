"""MapMode — viewer mode for .map files (terrain + object instances + sky)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, cast

import numpy as np
from imgui_bundle import imgui

from ....vfs import Resource
from ...scenes import AnimatedEntity, ViewerMesh
from ...scenes.scene import _STRIDE_PLAIN, _STRIDE_SKINNED
from ..base import AnimationPolicy, BaseMode, RenderExtension
from .camera import MapCamera
from .extensions import GridExtension, SkyExtension, TerrainExtension, WalkabilityExtension
from .pipeline import MapViewerPipeline
from .scene import MapScene

if TYPE_CHECKING:
  from ...app.world import AppWorld
  from ...camera import Camera
  from ...scenes import ViewerScene
  from ..context import ModeContext


_MAP_CONTROLS = [
  "LMB click     : Pick cell / object",
  "LMB drag      : Pan",
  "MMB drag      : Pan (grab)",
  "RMB drag L/R  : Yaw",
  "RMB drag U/D  : Pitch (15-75)",
  "WASD / Arrows : Pan",
  "Scroll        : Zoom",
  "G             : Toggle grid",
  "O             : Open file",
  "I             : Inject .ms1",
  "Esc           : Quit",
]


class MapMode(BaseMode):
  name = "map"
  extensions = (".map",)
  scene_type = MapScene
  animation_policy = AnimationPolicy(auto_play_all=True)

  def __init__(self) -> None:
    self._render_extensions: List[RenderExtension] = [
      SkyExtension(),
      TerrainExtension(),
      WalkabilityExtension(),
      GridExtension(),
    ]

  def render_extensions(self) -> "Iterable[RenderExtension]":
    return self._render_extensions

  def decode(self, res: Resource, shader_cache: Optional[dict] = None) -> "ViewerScene":
    return MapViewerPipeline().run(res, shader_cache)

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = MapCamera()
    cam.fit_map()
    if isinstance(scene, MapScene) and scene.terrain_heights is not None:
      cam.set_heightmap(scene.terrain_heights, 512, 512)
    return cam

  def draw_hud(self, world: "AppWorld") -> None:
    from ...app.panels import draw_unknowns_window

    ctx = world.scene.context
    if ctx is None:
      return
    scene = cast(MapScene, ctx.scene)
    self._draw_control_window(world, scene, ctx.path)
    self._draw_rendering_settings_window(world, scene)
    selected_idx = world.scene.selected_mesh_idx
    if selected_idx is not None and 0 <= selected_idx < len(scene.meshes):
      mesh = scene.meshes[selected_idx]
      ent_idx = world.scene.anim.mesh_to_entity.get(selected_idx)
      entity = (
        scene.entities[ent_idx]
        if ent_idx is not None and ent_idx < len(scene.entities)
        else None
      )
      self._draw_object_window(world, mesh, entity)
    if world.scene.selected_shader is not None:
      self._draw_shader_window(world)
    draw_unknowns_window(scene)

  def _draw_control_window(
    self, world: "AppWorld", scene: MapScene, path: Path
  ) -> None:
    tex_count = len([t for t in scene.terrain_textures if t is not None])

    imgui.set_next_window_pos((10, 10), imgui.Cond_.first_use_ever.value)
    imgui.begin("Map")
    imgui.text(f"File     : {path.name}")
    imgui.text(f"Objects  : {len(scene.meshes)}")
    imgui.text(f"Textures : {tex_count}/12")
    imgui.separator()
    if imgui.button("Open File"):
      world.open_dialog()
    imgui.separator()

    cell = scene.selected_grid_cell
    if cell is not None and scene.terrain_heights is not None:
      cx, cz = cell
      h = float(scene.terrain_heights[cz, cx])
      imgui.text(f"Cell     : ({cx}, {cz})")
      imgui.text(f"Height   : {h:.2f}")
      if scene.walkable_data is not None:
        w = int(scene.walkable_data[cz, cx])
        imgui.text(f"Walkable : {'no' if w else 'yes'}")
      imgui.separator()
    else:
      imgui.text_disabled("Click a cell to inspect")
      imgui.separator()

    for line in _MAP_CONTROLS:
      imgui.text_disabled(line)
    imgui.end()

  def _draw_rendering_settings_window(
    self, world: "AppWorld", scene: MapScene
  ) -> None:
    """Toggle buttons for shader / grid / walkability overlays."""
    imgui.set_next_window_pos((10, 220), imgui.Cond_.first_use_ever.value)
    imgui.begin("Rendering Settings")
    shader_label = "Shader: ON" if world.render.q3_enabled else "Shader: OFF"
    if imgui.button(shader_label):
      world.toggle_q3()
    grid_label = "Grid: ON" if scene.grid_enabled else "Grid: OFF"
    if imgui.button(grid_label):
      scene.grid_enabled = not scene.grid_enabled
    walk_available = scene.walkable_data is not None
    walk_label = (
      f"Walkability: {'ON' if scene.walkability_enabled else 'OFF'}"
      if walk_available
      else "Walkability: (no data)"
    )
    if walk_available:
      if imgui.button(walk_label):
        scene.walkability_enabled = not scene.walkability_enabled
    else:
      imgui.text_disabled(walk_label)
    imgui.end()

  def _draw_object_window(
    self,
    world: "AppWorld",
    mesh: ViewerMesh,
    entity: Optional[AnimatedEntity],
  ) -> None:
    stride = (_STRIDE_SKINNED if mesh.is_skinned else _STRIDE_PLAIN) // 4
    vertex_count = len(mesh.vertex_data) // stride
    tri_count = sum(len(p.indices) // 3 for p in mesh.primitives)
    instance_count = (
      len(mesh.instance_matrices) if mesh.instance_matrices is not None else 1
    )
    file_label = (
      entity.source_file if entity is not None and entity.source_file else mesh.name
    )

    win_w = world.window.width
    imgui.set_next_window_pos((win_w - 320, 10), imgui.Cond_.first_use_ever.value)
    imgui.begin("Selected Object")
    imgui.text(f"File      : {file_label}")
    imgui.text(f"Mesh      : {mesh.name}")
    imgui.text(f"Vertices  : {vertex_count:,}")
    imgui.text(f"Triangles : {tri_count:,}")
    imgui.text(f"Instances : {instance_count}")
    if entity is not None and entity.animation_groups:
      anim_type = "Skinned" if mesh.is_skinned else "Node-anim"
      imgui.text(f"Animated  : {anim_type}")
      for ag in entity.animation_groups:
        imgui.text_disabled(f"  - {ag.name}  ({ag.duration:.2f}s)")
    else:
      imgui.text("Animated  : No")

    # Shader list as buttons. Each opens / closes the shader detail window.
    shaders = []
    seen: set = set()
    for p in mesh.primitives:
      s = getattr(p, "shader", None)
      if s is None or id(s) in seen:
        continue
      seen.add(id(s))
      shaders.append(s)
    if shaders:
      imgui.separator()
      imgui.text("Shaders (click for detail):")
      for s in shaders:
        active = (world.scene.selected_shader is s)
        if imgui.selectable(f"{s.name}##sh{id(s)}", active)[0]:
          world.select_shader(s)
    imgui.end()

  def _draw_shader_window(self, world: "AppWorld") -> None:
    shader = world.scene.selected_shader
    if shader is None:
      return
    win_w = world.window.width
    imgui.set_next_window_pos((win_w - 320, 420), imgui.Cond_.first_use_ever.value)
    imgui.set_next_window_size((310, 280), imgui.Cond_.first_use_ever.value)
    opened, keep_open = imgui.begin(f"Shader: {shader.name}", True)
    if not keep_open:
      world.close_shader()
    if opened:
      imgui.begin_child("##shader_text", (0, -28))
      imgui.text_unformatted(shader.raw or "(empty)")
      imgui.end_child()
      if imgui.button("Close"):
        world.close_shader()
    imgui.end()

  def on_key(self, key: int, mctx: "ModeContext") -> None:
    from pygame.locals import K_g, K_i

    if key == K_i:
      mctx.open_inject_dialog()
    elif key == K_g:
      ctx = mctx.scene_context
      if ctx is not None and isinstance(ctx.scene, MapScene):
        ctx.scene.grid_enabled = not ctx.scene.grid_enabled

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
        self._pick_grid_cell(cx, cy, mctx)
      mctx.set_lmb_down(None)

  def _pick_grid_cell(self, mx: int, my: int, mctx: "ModeContext") -> None:
    """Ray-cast against the terrain and store the clicked tile in the scene."""
    ctx = mctx.scene_context
    if ctx is None or not isinstance(ctx.scene, MapScene):
      return
    cam = cast(MapCamera, mctx.camera)
    hit = cam.raycast_terrain_screen(mx, my, mctx.width, mctx.height)
    if hit is None:
      ctx.scene.selected_grid_cell = None
      return
    # Cell (i, j) is centered on integer (i, j); rounding maps a hit at
    # world x into the cell whose center is nearest.
    cell_x = int(np.clip(np.round(hit[0]), 0, 511))
    cell_z = int(np.clip(np.round(hit[2]), 0, 511))
    ctx.scene.selected_grid_cell = (cell_x, cell_z)

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
    from ..model.mode import ModelMode

    ctx = mctx.scene_context
    if ctx is None or not isinstance(ctx.scene, MapScene):
      print("[viewer] inject_model: no map loaded")
      return

    map_scene = ctx.scene
    cam = cast(MapCamera, ctx.camera)

    try:
      model_scene = ModelMode().decode(
        Resource.for_disk_file(path), mctx._app.shader_cache
      )
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
