"""
ImGui HUD — replaces the custom HudRenderer + panel system.

Call render_hud(world, width, height) once per frame after imgui.new_frame().
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from imgui_bundle import imgui

from ..modes.image.scene import ImageScene
from ..modes.map.scene import MapScene
from ..modes.model.scene import ModelScene

if TYPE_CHECKING:
    from .context import ViewerContext
    from .world import AppWorld

_FLAGS = (
    imgui.WindowFlags_.no_move
    | imgui.WindowFlags_.no_collapse
    | imgui.WindowFlags_.always_auto_resize
    | imgui.WindowFlags_.no_saved_settings
)


def render_hud(world: "AppWorld", width: int, height: int) -> None:
    """Draw all HUD panels for the current frame."""
    ctx = world.scene.context
    if ctx is None:
        _welcome(world)
        return
    scene = ctx.scene
    if isinstance(scene, ModelScene):
        _model_panel(world, ctx, scene, width, height)
    elif isinstance(scene, MapScene):
        _map_panel(world, ctx, scene, width, height)
    elif isinstance(scene, ImageScene):
        _image_panel(world, ctx, scene, width, height)


# ── Welcome (no file loaded) ──────────────────────────────────────────────────


def _welcome(world: "AppWorld") -> None:
    imgui.set_next_window_pos((10.0, 10.0), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.85)
    imgui.begin("Unsealed 3D Viewer", flags=_FLAGS)
    if imgui.button("Open File"):
        world.open_dialog()
    imgui.end()


# ── Model / Actor scene ───────────────────────────────────────────────────────

_MODEL_CONTROLS = [
    "RMB drag   Orbit (mouse locked)",
    "LMB drag   Orbit (mouse free)",
    "MMB drag   Pan",
    "Scroll     Zoom",
    "W          Toggle wireframe",
    "O          Open file",
    "Esc        Quit",
]

_ANIM_CONTROLS = [
    "Space      Play / Pause",
    "Backspace  Stop",
    "Up/Down    Change animation",
    "Left/Right Scrub (paused)",
]


def _model_panel(
    world: "AppWorld",
    ctx: "ViewerContext",
    scene: "ModelScene",
    width: int,
    height: int,
) -> None:
    anim = world.scene.anim.standalone
    q3_enabled = world.render.q3_enabled

    # ── top-left: file info + controls ───────────────────────────────────────
    imgui.set_next_window_pos((10.0, 10.0), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.85)
    imgui.begin("Model", flags=_FLAGS)

    imgui.text(f"File       {ctx.path.name}")
    imgui.text(f"Meshes     {len(scene.mesh_names)}")
    imgui.text(f"Triangles  {scene.tri_count:,}")
    if scene.animation_groups:
        imgui.text(f"Animations {len(scene.animation_groups)}")
    imgui.separator()

    if imgui.button("Open File"):
        world.open_dialog()
    imgui.same_line()
    shader_label = "Shader: ON" if q3_enabled else "Shader: OFF"
    if imgui.button(shader_label):
        world.toggle_q3()

    imgui.separator()
    imgui.text_disabled("Controls")
    for line in _MODEL_CONTROLS:
        imgui.text_disabled(line)
    if scene.animation_groups:
        imgui.spacing()
        for line in _ANIM_CONTROLS:
            imgui.text_disabled(line)

    imgui.end()

    # ── top-right: animation list ─────────────────────────────────────────────
    if anim.enabled and scene.animation_groups:
        imgui.set_next_window_pos(
            (float(width) - 10.0, 10.0), imgui.Cond_.always, (1.0, 0.0)
        )
        imgui.set_next_window_bg_alpha(0.85)
        imgui.set_next_window_size((220.0, 0.0), imgui.Cond_.always)
        imgui.begin("Animations", flags=_FLAGS)
        for i, g in enumerate(scene.animation_groups):
            selected = i == anim.group_idx
            sel, clicked = imgui.selectable(g.name, selected)
            if clicked:
                world.anim_select(i)
        imgui.end()

        # ── bottom-left: playback controls ────────────────────────────────────
        imgui.set_next_window_pos(
            (10.0, float(height) - 10.0), imgui.Cond_.always, (0.0, 1.0)
        )
        imgui.set_next_window_bg_alpha(0.85)
        imgui.begin("Playback", flags=_FLAGS)

        group = scene.animation_groups[anim.group_idx]
        imgui.text(f"[{group.name}]  {anim.time:.2f} / {group.duration:.2f}s")

        if imgui.button("||" if anim.playing else "> Play"):
            world.anim_toggle_play()
        imgui.same_line()
        if imgui.button("Stop"):
            world.anim_stop()

        # Scrub slider (only when paused)
        if not anim.playing and group.duration > 0.0:
            changed, new_t = imgui.slider_float(
                "##scrub", anim.time, 0.0, group.duration, "%.2f s"
            )
            if changed:
                world.anim_scrub(new_t - anim.time)

        imgui.end()


# ── Map scene ─────────────────────────────────────────────────────────────────

_MAP_CONTROLS = [
    "LMB drag            Pan",
    "MMB drag            Pan (grab)",
    "RMB drag L/R        Yaw",
    "RMB drag U/D        Pitch",
    "WASD / Arrows       Pan",
    "Scroll              Zoom",
    "LMB click           Select object",
    "O                   Open file",
    "Esc                 Quit",
]


def _map_panel(
    world: "AppWorld",
    ctx: "ViewerContext",
    scene: "MapScene",
    width: int,
    height: int,
) -> None:
    q3_enabled = world.render.q3_enabled
    tex_count = len([t for t in scene.terrain_textures if t is not None])

    # ── top-left: map info ────────────────────────────────────────────────────
    imgui.set_next_window_pos((10.0, 10.0), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.85)
    imgui.begin("Map", flags=_FLAGS)

    imgui.text(f"File      {ctx.path.name}")
    imgui.text(f"Objects   {len(scene.meshes)}")
    imgui.text(f"Textures  {tex_count}/12")
    imgui.separator()

    if imgui.button("Open File"):
        world.open_dialog()
    imgui.same_line()
    shader_label = "Shader: ON" if q3_enabled else "Shader: OFF"
    if imgui.button(shader_label):
        world.toggle_q3()

    imgui.separator()
    imgui.text_disabled("Controls")
    for line in _MAP_CONTROLS:
        imgui.text_disabled(line)

    imgui.end()

    # ── top-right: selected object detail ─────────────────────────────────────
    sel_idx = world.scene.selected_mesh_idx
    if sel_idx is not None and 0 <= sel_idx < len(scene.meshes):
        mesh = scene.meshes[sel_idx]
        from ..rendering.types import LAYOUT_PLAIN, LAYOUT_SKINNED
        stride = (LAYOUT_SKINNED.stride if mesh.is_skinned else LAYOUT_PLAIN.stride) // 4
        vertex_count = len(mesh.vertex_data) // stride
        tri_count = sum(len(p.indices) // 3 for p in mesh.primitives)
        instance_count = len(mesh.instance_matrices) if mesh.instance_matrices is not None else 1
        file_label = mesh.source_file if mesh.source_file else mesh.name

        imgui.set_next_window_pos(
            (float(width) - 10.0, 10.0), imgui.Cond_.always, (1.0, 0.0)
        )
        imgui.set_next_window_bg_alpha(0.85)
        imgui.begin("Selected Object", flags=_FLAGS)

        imgui.text("[ Selected Object ]")
        imgui.text(f"  File       {file_label}")
        imgui.text(f"  Mesh       {mesh.name}")
        imgui.text(f"  Vertices   {vertex_count:,}")
        imgui.text(f"  Triangles  {tri_count:,}")
        imgui.text(f"  Instances  {instance_count}")
        if mesh.animation_groups:
            anim_type = "Skinned" if mesh.is_skinned else "Node-anim"
            imgui.text(f"  Animated   {anim_type}")
            for ag in mesh.animation_groups:
                imgui.text(f"    * {ag.name}  ({ag.duration:.2f}s)")
        else:
            imgui.text("  Animated   No")
        imgui.separator()
        imgui.text_disabled("Click same object to deselect")

        imgui.end()


# ── Image scene ───────────────────────────────────────────────────────────────

_IMAGE_CONTROLS = [
    "Drag    Pan",
    "Scroll  Zoom",
    "R / F   Fit image",
    "O       Open file",
    "Esc     Quit",
]


def _image_panel(
    world: "AppWorld",
    ctx: "ViewerContext",
    scene: "ImageScene",
    width: int,
    height: int,
) -> None:
    from ..camera import ImageCamera
    from typing import cast
    cam = cast(ImageCamera, ctx.camera)

    imgui.set_next_window_pos((10.0, 10.0), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.85)
    imgui.begin("Image", flags=_FLAGS)

    imgui.text(f"File  {ctx.path.name}")
    imgui.text(f"Size  {scene.image_w} x {scene.image_h} px")
    imgui.text(f"Zoom  {int(cam.zoom * 100)}%")
    imgui.separator()

    if imgui.button("Open File"):
        world.open_dialog()

    imgui.separator()
    imgui.text_disabled("Controls")
    for line in _IMAGE_CONTROLS:
        imgui.text_disabled(line)

    imgui.end()
