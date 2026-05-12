"""
OpenGL renderer — ECS + deferred rendering with mode-driven RenderExtensions.

load_scene() uploads a ViewerScene to GPU, populates RenderRegistry, and asks
the scene's Mode for the RenderExtensions it wants run this frame.

render(RenderContext) orchestrates, in this fixed order:
  1. G-Buffer pass        — opaque geometry → albedo + normal MRT
  2. Lighting pass        — fullscreen deferred Blinn-Phong quad
  3. Depth blit           — G-Buffer depth → default FBO
  4. BACKGROUND phase     — mode extensions (e.g. sky)
  5. FORWARD_OPAQUE phase — mode extensions (e.g. terrain)
  6. FORWARD_Q3 phase     — mode extensions + core Q3 multi-stage pass
  7. TRANSPARENT phase    — mode extensions + core alpha-blend pass
  8. OVERLAY phase        — mode extensions + core wireframe / selection
"""

from __future__ import annotations

import ctypes
from typing import Dict, List, Optional, Tuple

from ..modes.base import RenderExtension, RenderPhase

import numpy as np
from numpy.typing import NDArray

from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_BACK,
    GL_CULL_FACE,
    GL_DEPTH_TEST,
    GL_FRONT,
    GL_DYNAMIC_DRAW,
    GL_ELEMENT_ARRAY_BUFFER,
    GL_FALSE,
    GL_FLOAT,
    GL_MULTISAMPLE,
    GL_ONE,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_SRC_ALPHA,
    GL_STATIC_DRAW,
    GL_TEXTURE0,
    GL_TEXTURE_2D,
    GL_TRIANGLES,
    GL_TRUE,
    GL_UNSIGNED_SHORT,
    glActiveTexture,
    glBindBuffer,
    glBindTexture,
    glBindVertexArray,
    glBlendFunc,
    glBufferData,
    glClear,
    glClearColor,
    glCullFace,
    glDeleteBuffers,
    glDeleteProgram,
    glDeleteTextures,
    glDeleteVertexArrays,
    glDepthMask,
    glDisable,
    glDrawArrays,
    glDrawElements,
    glDrawElementsInstanced,
    glEnable,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenVertexArrays,
    glGetUniformLocation,
    glUniform1i,
    glUniform4f,
    glUniformMatrix3fv,
    glUniformMatrix4fv,
    glUseProgram,
    glVertexAttribDivisor,
    glVertexAttribPointer,
)

from ..modes.image.camera import ImageCamera
from ..modes.image.scene import ImageScene
from ..modes.model.camera import OrbitCamera
from ..scenes import ViewerScene
from .components import BoundsComp, GpuBufferComp, MaterialComp, TransformComp
from .hud import HudRenderer
from .passes import GBufferPass, LightingPass, OverlayPass
from .registry import RenderRegistry
from .shaders import (
    _GBUFFER_FRAG,
    _IMG_FRAG,
    _IMG_VERT,
    _INST_VERT,
    _MESH_FRAG,
    _MESH_VERT,
    _Q3STAGE_FRAG,
    _Q3STAGE_VERT,
    _SEL_FRAG,
    _SEL_INST_VERT,
    _SEL_VERT,
    _SKIN_VERT,
    _WIRE_FRAG,
    _WIRE_VERT,
    _compile_prog,
    _u_mat4,
    _u_vec3,
    _upload_rgba,
)
from .types import (
    DrawCommand,
    HudPanel,
    RenderContext,
    ShaderVariant,
    _GpuPrimitive,
    _Q3GpuStage,
    _IDENTITY_BONE_FLAT,
    _MAX_BONES,
    _STRIDE_PLAIN,
    _STRIDE_SKINNED,
)


def _bind_primitive_material(prog: int, prim: _GpuPrimitive) -> None:
    """Bind texture/colour and set depth mask + blend for a forward draw."""
    glUniform1i(
        glGetUniformLocation(prog, "uHasTexture"), int(prim.texture_id is not None)
    )
    glDepthMask(GL_TRUE)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    if prim.texture_id is not None:
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, prim.texture_id)
        glUniform1i(glGetUniformLocation(prog, "uTexture"), 0)
    else:
        glBindTexture(GL_TEXTURE_2D, 0)
    c = prim.base_color
    glUniform4f(glGetUniformLocation(prog, "uBaseColor"), c[0], c[1], c[2], c[3])


class Renderer:
    """
    Owns all OpenGL objects.  Call load_scene() to upload a ViewerScene to
    the GPU, then render(RenderContext) each frame.
    """

    def __init__(self) -> None:
        # Forward programs — mesh.frag.glsl (used for transparent pass + image)
        self._mesh_prog: int = 0
        self._skin_prog: int = 0
        self._inst_prog: int = 0
        self._wire_prog: int = 0
        self._sel_prog: int = 0
        self._sel_inst_prog: int = 0
        self._img_prog: int = 0
        self._img_vao: int = 0
        self._img_vbo: int = 0
        # Q3 shader stage program
        self._q3_prog: int = 0

        # ECS component registry
        self._registry = RenderRegistry()

        # 2-D image viewer state
        self._is_2d: bool = False
        self._image_tex_id: Optional[int] = None
        self._image_w: int = 0
        self._image_h: int = 0

        # Render passes
        self._gbuffer = GBufferPass()
        self._lighting = LightingPass()
        self._overlay: Optional[OverlayPass] = None
        self._hud = HudRenderer()

        # Mode-supplied render extensions. _all_extensions is the union across
        # all modes (init+dispose lifecycle); _active_extensions is the subset
        # for the currently-loaded scene (upload/render/free_scene lifecycle).
        self._all_extensions: List[RenderExtension] = []
        self._active_extensions: List[RenderExtension] = []

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def init(self) -> None:
        # Forward programs (mesh.frag.glsl)
        self._mesh_prog = _compile_prog(_MESH_VERT, _MESH_FRAG)
        self._skin_prog = _compile_prog(_SKIN_VERT, _MESH_FRAG)
        self._inst_prog = _compile_prog(_INST_VERT, _MESH_FRAG)
        self._wire_prog = _compile_prog(_WIRE_VERT, _WIRE_FRAG)
        self._sel_prog = _compile_prog(_SEL_VERT, _SEL_FRAG)
        self._sel_inst_prog = _compile_prog(_SEL_INST_VERT, _SEL_FRAG)
        self._img_prog = _compile_prog(_IMG_VERT, _IMG_FRAG)

        self._img_vao = glGenVertexArrays(1)
        self._img_vbo = glGenBuffers(1)

        # G-Buffer and lighting passes
        self._gbuffer.init(_MESH_VERT, _SKIN_VERT, _INST_VERT, _GBUFFER_FRAG)
        self._lighting.init()

        # Overlay pass shares forward programs (no extra compile)
        self._overlay = OverlayPass(self._wire_prog, self._sel_prog, self._sel_inst_prog)

        self._q3_prog = _compile_prog(_Q3STAGE_VERT, _Q3STAGE_FRAG)

        self._hud.init()

        # Eagerly init render extensions from every registered Mode so terrain
        # /sky shaders compile once at startup, not on first map load.
        from ..modes import MODES
        seen: set = set()
        for mode in MODES:
            for ext in mode.render_extensions():
                if id(ext) in seen:
                    continue
                seen.add(id(ext))
                self._all_extensions.append(ext)
                ext.init()

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glEnable(GL_MULTISAMPLE)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.14, 0.14, 0.17, 1.0)

    def cleanup(self) -> None:
        self._registry.free()
        self._free_image()
        for ext in self._all_extensions:
            ext.dispose()
        self._all_extensions = []
        self._active_extensions = []
        self._hud.cleanup()
        self._gbuffer.cleanup()
        self._lighting.cleanup()
        for prog in (
            self._mesh_prog,
            self._skin_prog,
            self._inst_prog,
            self._wire_prog,
            self._sel_prog,
            self._sel_inst_prog,
            self._img_prog,
            self._q3_prog,
        ):
            if prog:
                glDeleteProgram(prog)
        if self._img_vao:
            glDeleteVertexArrays(1, [self._img_vao])
        if self._img_vbo:
            glDeleteBuffers(1, [self._img_vbo])

    # ── scene loading ─────────────────────────────────────────────────────────

    def load_scene(self, scene: ViewerScene) -> None:
        """Upload a ViewerScene to GPU memory. Replaces any previously loaded scene."""
        self._registry.free()
        self._free_image()
        # Drop per-scene state from the previously-active extensions before
        # rebinding _active_extensions to the new mode's set.
        for ext in self._active_extensions:
            ext.free_scene()
        self._is_2d = isinstance(scene, ImageScene)

        # Resolve the scene's Mode and snapshot its render extensions.
        from ..modes import for_scene
        try:
            active_mode = for_scene(scene)
        except ValueError:
            active_mode = None
        self._active_extensions = (
            list(active_mode.render_extensions()) if active_mode else []
        )
        for ext in self._active_extensions:
            ext.upload(scene)

        if isinstance(scene, ImageScene):
            if scene.image is not None:
                self._image_tex_id = _upload_rgba(scene.image, scene.image_w, scene.image_h)
            self._image_w = scene.image_w
            self._image_h = scene.image_h
            return

        for eid, mesh in enumerate(scene.meshes):  # type: ignore[union-attr]
            vao = glGenVertexArrays(1)
            vbo = glGenBuffers(1)

            glBindVertexArray(vao)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(
                GL_ARRAY_BUFFER, mesh.vertex_data.nbytes, mesh.vertex_data, GL_STATIC_DRAW
            )

            if mesh.is_skinned:
                stride = _STRIDE_SKINNED
                glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
                glEnableVertexAttribArray(0)
                glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
                glEnableVertexAttribArray(1)
                glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
                glEnableVertexAttribArray(2)
                glVertexAttribPointer(3, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(32))
                glEnableVertexAttribArray(3)
                glVertexAttribPointer(4, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(48))
                glEnableVertexAttribArray(4)
            else:
                stride = _STRIDE_PLAIN
                glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
                glEnableVertexAttribArray(0)
                glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
                glEnableVertexAttribArray(1)
                glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
                glEnableVertexAttribArray(2)

            # ── instance matrix VBO ──────────────────────────────────────────
            instance_vbo = 0
            instance_count = 1
            if mesh.instance_matrices is not None and len(mesh.instance_matrices) > 0:
                instance_count = len(mesh.instance_matrices)
                data = np.ascontiguousarray(
                    mesh.instance_matrices.transpose(0, 2, 1).reshape(-1), dtype=np.float32
                )
                instance_vbo = glGenBuffers(1)
                glBindBuffer(GL_ARRAY_BUFFER, instance_vbo)
                glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)
                inst_stride = 64
                for col in range(4):
                    loc = 5 + col
                    glVertexAttribPointer(
                        loc, 4, GL_FLOAT, GL_FALSE, inst_stride, ctypes.c_void_p(col * 16)
                    )
                    glEnableVertexAttribArray(loc)
                    glVertexAttribDivisor(loc, 1)
                glBindBuffer(GL_ARRAY_BUFFER, 0)

            glBindVertexArray(0)

            # Local AABB for CPU picking
            stride_f = _STRIDE_SKINNED // 4 if mesh.is_skinned else _STRIDE_PLAIN // 4
            positions = mesh.vertex_data.reshape(-1, stride_f)[:, :3]
            aabb_min = positions.min(axis=0).astype(np.float32)
            aabb_max = positions.max(axis=0).astype(np.float32)

            buf_comp = GpuBufferComp(
                vao=vao,
                vbo=vbo,
                instance_vbo=instance_vbo,
                instance_count=instance_count,
                inst_mats_cpu=mesh.instance_matrices,
            )
            xform_comp = TransformComp(
                model_matrix=mesh.model_matrix,
                is_skinned=mesh.is_skinned,
            )
            bnds_comp = BoundsComp(aabb_min=aabb_min, aabb_max=aabb_max)
            mat_comp = MaterialComp()

            for prim in mesh.primitives:
                ebo = glGenBuffers(1)
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
                glBufferData(
                    GL_ELEMENT_ARRAY_BUFFER, prim.indices.nbytes, prim.indices, GL_STATIC_DRAW
                )
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

                tex_id: Optional[int] = None
                if prim.image is not None:
                    tex_id = _upload_rgba(prim.image, prim.image_w, prim.image_h)

                gpu_prim = _GpuPrimitive(
                    ebo=ebo,
                    index_count=len(prim.indices),
                    texture_id=tex_id,
                    base_color=prim.base_color,
                    two_sided=prim.two_sided,
                    is_billboard=prim.is_billboard,
                )

                if prim.q3_stages:
                    for vs in prim.q3_stages:
                        tid: Optional[int] = None
                        if vs.image is not None:
                            tid = _upload_rgba(vs.image, vs.image_w, vs.image_h)
                        anim_ids = [
                            _upload_rgba(f[0], f[1], f[2]) for f in vs.anim_frames
                        ]
                        gpu_prim.q3_stages.append(
                            _Q3GpuStage(
                                tex_id=tid,
                                blend_src=vs.blend_src,
                                blend_dst=vs.blend_dst,
                                tc_mods=vs.tc_mods,
                                tc_gen_env=vs.tc_gen_env,
                                anim_tex_ids=anim_ids,
                                anim_fps=vs.anim_fps,
                            )
                        )

                mat_comp.primitives.append(gpu_prim)

            self._registry.add(eid, buf_comp, mat_comp, xform_comp, bnds_comp)

    # ── per-frame rendering ───────────────────────────────────────────────────

    def render(self, ctx: RenderContext) -> None:
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_TRUE)
        glDisable(GL_CULL_FACE)

        glClear(int(GL_COLOR_BUFFER_BIT) | int(GL_DEPTH_BUFFER_BIT))

        if self._is_2d:
            if isinstance(ctx.camera, ImageCamera):
                self._render_image(ctx.camera, ctx.width, ctx.height)
            return

        aspect = ctx.width / max(ctx.height, 1)
        view = ctx.camera.view_matrix()
        proj = ctx.camera.projection_matrix(aspect, ctx.width, ctx.height)

        _mirror_x = np.diag(np.array([-1.0, 1.0, 1.0, 1.0], dtype=np.float32))
        proj = _mirror_x @ proj

        light_dir = np.array([0.45, -0.85, 0.35], dtype=np.float32)
        light_dir /= np.linalg.norm(light_dir)

        has_meshes = bool(self._registry.buffers)

        if has_meshes:
            opaque, transparent, q3_commands = self._build_commands(ctx)

            # 1. G-Buffer pass — opaque geometry
            self._gbuffer.begin(ctx.width, ctx.height)
            self._gbuffer.draw(self._registry, opaque, view, proj)
            self._gbuffer.end()

            # 2. Deferred lighting fullscreen quad
            self._lighting.render(self._gbuffer.albedo_tex, self._gbuffer.normal_tex, light_dir)

            # 3. Blit G-Buffer depth → default FBO
            self._gbuffer.blit_depth(ctx.width, ctx.height)
        else:
            transparent = []
            q3_commands = []

        # 4. BACKGROUND phase — sky / environment
        self._run_phase(RenderPhase.BACKGROUND, ctx, view, proj)

        # 5. FORWARD_OPAQUE phase — terrain / other forward opaque
        self._run_phase(RenderPhase.FORWARD_OPAQUE, ctx, view, proj)

        if not has_meshes:
            return

        # 6. FORWARD_Q3 phase — extensions + core Q3 multi-stage pass
        self._run_phase(RenderPhase.FORWARD_Q3, ctx, view, proj)
        if q3_commands and ctx.q3_enabled:
            self._draw_q3_stages(q3_commands, ctx, view, proj)

        # 7. TRANSPARENT phase — extensions + core alpha-blend pass
        self._run_phase(RenderPhase.TRANSPARENT, ctx, view, proj)
        if transparent:
            self._draw_forward(transparent, ctx, view, proj, light_dir)

        glDepthMask(GL_TRUE)

        # 8. OVERLAY phase — extensions + core wireframe / selection
        self._run_phase(RenderPhase.OVERLAY, ctx, view, proj)
        if self._overlay is not None:
            if ctx.wireframe:
                self._overlay.render_wireframe(self._registry, view, proj)
            if ctx.selected_mesh_idx is not None and ctx.selected_mesh_idx in self._registry.buffers:
                self._overlay.render_selection(
                    self._registry, ctx.selected_mesh_idx, view, proj
                )

    def _run_phase(
        self,
        phase: RenderPhase,
        ctx: RenderContext,
        view: NDArray,
        proj: NDArray,
    ) -> None:
        """Call render(ctx, view, proj) on every active extension with this phase."""
        for ext in self._active_extensions:
            if ext.phase == phase:
                ext.render(ctx, view, proj)

    def render_hud(
        self,
        panels: List[HudPanel],
        font: object,
        width: int,
        height: int,
        mouse_pos: tuple = (-1, -1),
    ) -> list:
        """Render HUD panels; return all HudButton objects with screen rects filled."""
        return self._hud.render(panels, font, width, height, mouse_pos)

    def pick(
        self,
        mx: int,
        my: int,
        width: int,
        height: int,
        view: NDArray,
        proj: NDArray,
    ) -> Optional[int]:
        """CPU ray-cast pick against mesh AABBs. Returns nearest entity_id or None."""
        if not self._registry.buffers:
            return None

        _mirror_x = np.diag(np.array([-1.0, 1.0, 1.0, 1.0], dtype=np.float32))
        proj = _mirror_x @ proj

        ray_origin, ray_dir = _unproject_ray(mx, my, width, height, view, proj)

        best_t = float("inf")
        best_idx: Optional[int] = None

        for eid in self._registry.entity_ids():
            buf = self._registry.buffers[eid]
            xform = self._registry.transforms[eid]
            bnds = self._registry.bounds[eid]

            if buf.inst_mats_cpu is not None:
                for k in range(buf.instance_count):
                    world = buf.inst_mats_cpu[k] @ xform.model_matrix
                    t = _ray_aabb_in_world(
                        ray_origin, ray_dir, bnds.aabb_min, bnds.aabb_max, world
                    )
                    if t is not None and 0.0 < t < best_t:
                        best_t = t
                        best_idx = eid
            else:
                t = _ray_aabb_in_world(
                    ray_origin, ray_dir, bnds.aabb_min, bnds.aabb_max, xform.model_matrix
                )
                if t is not None and 0.0 < t < best_t:
                    best_t = t
                    best_idx = eid

        return best_idx

    # ── private ───────────────────────────────────────────────────────────────

    def _build_commands(
        self, ctx: RenderContext
    ) -> Tuple[List[DrawCommand], List[DrawCommand], List[DrawCommand]]:
        """
        Produce one DrawCommand per (entity, instance, primitive) and classify
        into opaque (G-Buffer), transparent (forward alpha blend), or q3 lists.
        """
        opaque: List[DrawCommand] = []
        transparent: List[DrawCommand] = []
        q3: List[DrawCommand] = []

        for eid in self._registry.entity_ids():
            buf = self._registry.buffers[eid]
            xform = self._registry.transforms[eid]
            mat = self._registry.materials[eid]

            # Gather (model_matrix, bone_flat, bone_count, variant) tuples
            # — one per logical draw call for this entity
            draw_params: List[Tuple[NDArray, Optional[NDArray], int, ShaderVariant]] = []

            bones = ctx.bone_matrices.get(eid)
            node_world = ctx.node_matrices.get(eid)

            if xform.is_skinned and buf.inst_mats_cpu is not None:
                # Animated skinned instances — draw each separately
                if bones is not None:
                    bc = min(len(bones), _MAX_BONES)
                    bf: Optional[NDArray] = np.array(
                        [m.flatten() for m in bones[:bc]], dtype=np.float32
                    ).flatten()
                else:
                    bc = _MAX_BONES
                    bf = _IDENTITY_BONE_FLAT
                for k in range(buf.instance_count):
                    model = buf.inst_mats_cpu[k] @ xform.model_matrix
                    draw_params.append((model, bf, bc, ShaderVariant.SKINNED))

            elif not xform.is_skinned and node_world is not None:
                # Node-transform animated
                if buf.inst_mats_cpu is not None:
                    for k in range(buf.instance_count):
                        model = buf.inst_mats_cpu[k] @ node_world
                        draw_params.append((model, None, 0, ShaderVariant.PLAIN))
                else:
                    draw_params.append((node_world, None, 0, ShaderVariant.PLAIN))

            else:
                # Static — multi-instance GL instancing or single draw
                if buf.instance_count > 1:
                    draw_params.append(
                        (xform.model_matrix, None, 0, ShaderVariant.INSTANCED)
                    )
                elif xform.is_skinned:
                    # Standalone bone animation
                    if bones is not None:
                        bc = min(len(bones), _MAX_BONES)
                        bf = np.array(
                            [m.flatten() for m in bones[:bc]], dtype=np.float32
                        ).flatten()
                    else:
                        bc = _MAX_BONES
                        bf = _IDENTITY_BONE_FLAT
                    model = (
                        buf.inst_mats_cpu[0] @ xform.model_matrix
                        if buf.inst_mats_cpu is not None
                        else xform.model_matrix
                    )
                    draw_params.append((model, bf, bc, ShaderVariant.SKINNED))
                else:
                    model = (
                        buf.inst_mats_cpu[0] @ xform.model_matrix
                        if buf.inst_mats_cpu is not None
                        else xform.model_matrix
                    )
                    draw_params.append((model, None, 0, ShaderVariant.PLAIN))

            # Emit one DrawCommand per primitive per draw_param
            for prim_idx, prim in enumerate(mat.primitives):
                is_q3 = bool(prim.q3_stages)
                is_transparent = not is_q3 and prim.base_color[3] < 1.0
                for model, bf, bc, variant in draw_params:
                    if is_q3 and variant == ShaderVariant.INSTANCED:
                        # Q3 stage shader has no instancing support — expand to one
                        # PLAIN draw per instance with the instance matrix folded in.
                        if buf.inst_mats_cpu is not None:
                            for k in range(buf.instance_count):
                                inst_model = buf.inst_mats_cpu[k] @ xform.model_matrix
                                q3.append(DrawCommand(
                                    entity_id=eid,
                                    variant=ShaderVariant.PLAIN,
                                    model_matrix=inst_model,
                                    primitive_idx=prim_idx,
                                    instance_count=1,
                                    bone_matrices_flat=None,
                                    bone_count=0,
                                ))
                    else:
                        ic = buf.instance_count if variant == ShaderVariant.INSTANCED else 1
                        cmd = DrawCommand(
                            entity_id=eid,
                            variant=variant,
                            model_matrix=model,
                            primitive_idx=prim_idx,
                            instance_count=ic,
                            bone_matrices_flat=bf,
                            bone_count=bc,
                        )
                        if is_q3:
                            q3.append(cmd)
                        elif is_transparent:
                            transparent.append(cmd)
                        else:
                            opaque.append(cmd)

        return opaque, transparent, q3

    def _draw_q3_stages(
        self,
        commands: List[DrawCommand],
        ctx: RenderContext,
        view: NDArray,
        proj: NDArray,
    ) -> None:
        """Forward pass for Q3 multi-stage shader primitives."""
        prog = self._q3_prog
        glUseProgram(prog)
        glEnable(GL_BLEND)
        glDepthMask(GL_FALSE)
        _u_mat4(prog, "uView", view)
        _u_mat4(prog, "uProjection", proj)

        loc_tex_matrix = glGetUniformLocation(prog, "uTexMatrix")
        loc_tc_gen_env = glGetUniformLocation(prog, "uTcGenEnv")
        loc_has_tex    = glGetUniformLocation(prog, "uHasTexture")
        loc_base_color = glGetUniformLocation(prog, "uBaseColor")
        loc_texture    = glGetUniformLocation(prog, "uTexture")

        for cmd in commands:
            buf  = self._registry.buffers[cmd.entity_id]
            mat  = self._registry.materials[cmd.entity_id]
            prim = mat.primitives[cmd.primitive_idx]

            glBindVertexArray(buf.vao)
            model_mat = (
                _spherical_billboard(cmd.model_matrix, view)
                if prim.is_billboard
                else cmd.model_matrix
            )
            _u_mat4(prog, "uModel", model_mat)

            if prim.two_sided:
                glDisable(GL_CULL_FACE)
                # cull disable + additive glow: must remain visible from all angles even
                # when opaque geometry (e.g. lamp body) has already written closer depth.
                glDisable(GL_DEPTH_TEST)
            else:
                # _mirror_x negates clip-space X, reversing all triangle winding.
                # GL_BACK would cull the intended front faces, so use GL_FRONT instead.
                glEnable(GL_CULL_FACE)
                glCullFace(GL_FRONT)
                glEnable(GL_DEPTH_TEST)

            for stage in prim.q3_stages:
                glBlendFunc(stage.blend_src, stage.blend_dst)

                tex_mat = _compute_tex_matrix(stage.tc_mods, ctx.time)
                glUniformMatrix3fv(loc_tex_matrix, 1, GL_FALSE, tex_mat)
                glUniform1i(loc_tc_gen_env, int(stage.tc_gen_env))

                if stage.anim_tex_ids:
                    frame_idx = int(stage.anim_fps * ctx.time) % len(stage.anim_tex_ids)
                    active_tex = stage.anim_tex_ids[frame_idx]
                elif stage.tex_id is not None:
                    active_tex = stage.tex_id
                else:
                    active_tex = None

                if active_tex is not None:
                    glActiveTexture(GL_TEXTURE0)
                    glBindTexture(GL_TEXTURE_2D, active_tex)
                    glUniform1i(loc_has_tex, 1)
                    glUniform1i(loc_texture, 0)
                else:
                    glBindTexture(GL_TEXTURE_2D, 0)
                    glUniform1i(loc_has_tex, 0)

                c = prim.base_color
                glUniform4f(loc_base_color, c[0], c[1], c[2], c[3])

                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, prim.ebo)
                glDrawElements(GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None)

        glDisable(GL_CULL_FACE)
        glCullFace(GL_BACK)  # restore default
        glEnable(GL_DEPTH_TEST)  # restore (may have been disabled for two_sided prims)
        glBindVertexArray(0)
        glDepthMask(GL_TRUE)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glUseProgram(0)

    def _draw_forward(
        self,
        commands: List[DrawCommand],
        ctx: RenderContext,
        view: NDArray,
        proj: NDArray,
        light_dir: NDArray,
    ) -> None:
        """Forward pass for transparent (base_color.a < 1) primitives."""
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)

        _prog_map = {
            ShaderVariant.SKINNED: self._skin_prog,
            ShaderVariant.INSTANCED: self._inst_prog,
        }

        # Upload shared uniforms to all three forward programs
        for prog in (self._mesh_prog, self._skin_prog, self._inst_prog):
            glUseProgram(prog)
            _u_mat4(prog, "uView", view)
            _u_mat4(prog, "uProjection", proj)
            _u_vec3(prog, "uLightDir", light_dir)

        for cmd in commands:
            buf = self._registry.buffers[cmd.entity_id]
            mat = self._registry.materials[cmd.entity_id]
            prim = mat.primitives[cmd.primitive_idx]

            prog = _prog_map.get(cmd.variant, self._mesh_prog)
            glUseProgram(prog)
            _u_mat4(prog, "uModel", cmd.model_matrix)

            if cmd.variant == ShaderVariant.SKINNED:
                loc_b = glGetUniformLocation(prog, "uBoneMatrices[0]")
                if loc_b != -1:
                    if cmd.bone_matrices_flat is not None:
                        glUniformMatrix4fv(loc_b, cmd.bone_count, GL_TRUE, cmd.bone_matrices_flat)
                    else:
                        glUniformMatrix4fv(loc_b, _MAX_BONES, GL_TRUE, _IDENTITY_BONE_FLAT)

            _bind_primitive_material(prog, prim)
            # _bind_primitive_material resets depth mask to GL_TRUE; keep it GL_FALSE
            # so transparent surfaces don't occlude each other during this pass.
            glDepthMask(GL_FALSE)

            glBindVertexArray(buf.vao)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, prim.ebo)
            if cmd.instance_count > 1:
                glDrawElementsInstanced(
                    GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None, cmd.instance_count
                )
            else:
                glDrawElements(GL_TRIANGLES, prim.index_count, GL_UNSIGNED_SHORT, None)

        glBindVertexArray(0)
        glDepthMask(GL_TRUE)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glUseProgram(0)

    def _render_image(self, camera: ImageCamera, width: int, height: int) -> None:
        """Render the 2-D image scene using the image shader."""
        if self._image_tex_id is None:
            return

        aspect = width / max(height, 1)
        proj = camera.projection_matrix(aspect, width, height)
        mvp = proj

        hw = self._image_w * 0.5
        hh = self._image_h * 0.5
        verts = np.array(
            [
                -hw, -hh, 0.0, 0.0, 0.0,
                 hw, -hh, 0.0, 1.0, 0.0,
                 hw,  hh, 0.0, 1.0, 1.0,
                -hw, -hh, 0.0, 0.0, 0.0,
                 hw,  hh, 0.0, 1.0, 1.0,
                -hw,  hh, 0.0, 0.0, 1.0,
            ],
            dtype=np.float32,
        )

        glBindVertexArray(self._img_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self._img_vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_DYNAMIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glDisable(GL_DEPTH_TEST)
        glUseProgram(self._img_prog)
        _u_mat4(self._img_prog, "uMVP", mvp)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self._image_tex_id)
        glUniform1i(glGetUniformLocation(self._img_prog, "uTexture"), 0)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)
        glEnable(GL_DEPTH_TEST)

    def _free_image(self) -> None:
        if self._image_tex_id is not None:
            glDeleteTextures(1, [self._image_tex_id])
            self._image_tex_id = None
        self._is_2d = False
        self._image_w = 0
        self._image_h = 0


# ─── Billboard helper ────────────────────────────────────────────────────────


def _spherical_billboard(model_mat: NDArray, view: NDArray) -> NDArray:
    """
    Replace the rotation of model_mat with the camera's orientation so the
    quad always faces the camera (spherical billboard).
    Position and scale are preserved from model_mat.
    View matrix rows: [right, up, -forward] in world space.
    """
    pos = model_mat[:3, 3]
    scale_x = float(np.linalg.norm(model_mat[:3, 0]))
    scale_y = float(np.linalg.norm(model_mat[:3, 1]))
    scale_z = float(np.linalg.norm(model_mat[:3, 2]))

    right = view[0, :3]
    up    = view[1, :3]
    fwd   = -view[2, :3]

    bb = np.identity(4, dtype=np.float32)
    bb[:3, 0] = right * scale_x
    bb[:3, 1] = up    * scale_y
    bb[:3, 2] = fwd   * scale_z
    bb[:3, 3] = pos
    return bb


# ─── Q3 texture matrix helper ────────────────────────────────────────────────


def _compute_tex_matrix(
    tc_mods: List[Tuple[str, Tuple[float, ...]]], time: float
) -> NDArray:
    """
    Compose a column-major 3×3 UV-transform matrix from a list of tcMod ops.

    Supported ops:
      ("rotate",  (deg_per_sec,))
      ("scroll",  (s_per_sec, t_per_sec))
      ("scale",   (s, t))

    Returns a flat float32 array of 9 values in column-major order
    (suitable for glUniformMatrix3fv with GL_FALSE transpose flag).
    """
    # We accumulate in row-major for readability, then transpose at the end.
    result = np.identity(3, dtype=np.float64)

    for mod_type, params in tc_mods:
        if mod_type == "rotate" and len(params) >= 1:
            angle = np.radians(params[0] * time)
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            # Rotate around UV centre (0.5, 0.5): T(-0.5) R T(0.5)
            t_to   = np.array([[1, 0, -0.5], [0, 1, -0.5], [0, 0, 1]], dtype=np.float64)
            rot    = np.array([[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]], dtype=np.float64)
            t_back = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1]], dtype=np.float64)
            result = t_back @ rot @ t_to @ result

        elif mod_type == "scroll" and len(params) >= 2:
            # Q3 scroll is specified in game UV space (V=0 at top / image convention).
            # The vertex shader flips V into OpenGL UV space before applying this matrix,
            # so the T component must be negated to preserve the intended scroll direction.
            tx, ty = params[0] * time, -params[1] * time
            trans = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], dtype=np.float64)
            result = trans @ result

        elif mod_type == "scale" and len(params) >= 2:
            sx, sy = params[0], params[1]
            scale = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], dtype=np.float64)
            result = scale @ result

    # Transpose to column-major and flatten
    return result.T.astype(np.float32).flatten()


# ─── Ray picking helpers ──────────────────────────────────────────────────────


def _unproject_ray(
    mx: int,
    my: int,
    width: int,
    height: int,
    view: NDArray,
    proj: NDArray,
) -> Tuple[NDArray, NDArray]:
    """Return (ray_origin, ray_dir) in world space from a screen pixel."""
    ndc_x = (2.0 * mx / width) - 1.0
    ndc_y = 1.0 - (2.0 * my / height)

    inv_vp = np.linalg.inv((proj @ view).astype(np.float64))

    near = inv_vp @ np.array([ndc_x, ndc_y, -1.0, 1.0], dtype=np.float64)
    far = inv_vp @ np.array([ndc_x, ndc_y, 1.0, 1.0], dtype=np.float64)
    near /= near[3]
    far /= far[3]

    origin = near[:3].astype(np.float32)
    direc = (far[:3] - near[:3]).astype(np.float32)
    length = np.linalg.norm(direc)
    if length > 1e-8:
        direc /= length
    return origin, direc


def _ray_aabb_intersect(
    origin: NDArray,
    direction: NDArray,
    aabb_min: NDArray,
    aabb_max: NDArray,
) -> Optional[float]:
    """Slab-method ray–AABB test. Returns world-space t or None on miss."""
    t_min = -np.inf
    t_max = np.inf
    for i in range(3):
        if abs(direction[i]) < 1e-8:
            if origin[i] < aabb_min[i] or origin[i] > aabb_max[i]:
                return None
        else:
            t1 = (aabb_min[i] - origin[i]) / direction[i]
            t2 = (aabb_max[i] - origin[i]) / direction[i]
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)
    if t_max < 0.0 or t_min > t_max:
        return None
    return t_min if t_min >= 0.0 else t_max


def _ray_aabb_in_world(
    ray_origin: NDArray,
    ray_dir: NDArray,
    aabb_min: NDArray,
    aabb_max: NDArray,
    world_matrix: NDArray,
) -> Optional[float]:
    """Transform a world-space ray into local space and test against the local AABB."""
    try:
        inv_world = np.linalg.inv(world_matrix.astype(np.float64))
    except np.linalg.LinAlgError:
        return None

    o4 = np.array([*ray_origin, 1.0], dtype=np.float64)
    d4 = np.array([*ray_dir, 0.0], dtype=np.float64)

    local_origin = (inv_world @ o4)[:3].astype(np.float32)
    local_dir = (inv_world @ d4)[:3].astype(np.float32)

    return _ray_aabb_intersect(local_origin, local_dir, aabb_min, aabb_max)
