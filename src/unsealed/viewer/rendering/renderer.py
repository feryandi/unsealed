"""
OpenGL renderer — ECS + deferred rendering with mode-driven RenderExtensions.

load_scene() uploads a ViewerScene to GPU, populates RenderRegistry, and
swaps in the RenderExtensions that the scene's Mode supplies.

render(RenderContext) orchestrates, in this fixed order:
  1. G-Buffer pass        — opaque geometry → albedo + normal MRT
  2. Lighting pass        — fullscreen deferred Blinn-Phong quad
  3. Depth blit           — G-Buffer depth → default FBO
  4. BACKGROUND phase     — mode extensions (e.g. sky, 2-D image)
  5. FORWARD_OPAQUE phase — mode extensions (e.g. terrain)
  6. FORWARD_Q3 phase     — mode extensions + core Q3 multi-stage pass
  7. TRANSPARENT phase    — mode extensions + core alpha-blend pass
  8. OVERLAY phase        — mode extensions + core wireframe / selection
"""

from __future__ import annotations

import ctypes
from typing import Iterable, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray
from OpenGL.GL import (
  GL_ARRAY_BUFFER,
  GL_BLEND,
  GL_COLOR_BUFFER_BIT,
  GL_DEPTH_BUFFER_BIT,
  GL_CULL_FACE,
  GL_DEPTH_TEST,
  GL_FALSE,
  GL_FLOAT,
  GL_MULTISAMPLE,
  GL_ONE_MINUS_SRC_ALPHA,
  GL_SRC_ALPHA,
  GL_STATIC_DRAW,
  GL_ELEMENT_ARRAY_BUFFER,
  GL_TRUE,
  glBindBuffer,
  glBindVertexArray,
  glBlendFunc,
  glBufferData,
  glClear,
  glClearColor,
  glDeleteProgram,
  glDepthMask,
  glDisable,
  glEnable,
  glEnableVertexAttribArray,
  glGenBuffers,
  glGenVertexArrays,
  glVertexAttribDivisor,
  glVertexAttribPointer,
)

from ..scenes import ViewerScene
from ..scenes.scene import _STRIDE_PLAIN, _STRIDE_SKINNED
from .components import BoundsComp, GpuBufferComp, MaterialComp, TransformComp
from .extension import RenderExtension, RenderPhase
from .math_utils import ray_aabb_in_world, unproject_ray
from .passes import (
  ForwardPass,
  GBufferPass,
  LightingPass,
  OverlayPass,
  Q3StagePass,
)
from .registry import RenderRegistry
from .shaders import (
  _GBUFFER_FRAG,
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
  _upload_rgba,
)
from .types import (
  DrawCommand,
  RenderContext,
  ShaderVariant,
  _GpuPrimitive,
  _IDENTITY_BONE_FLAT,
  _MAX_BONES,
  _Q3GpuStage,
)


class Renderer:
  """
  Owns all OpenGL objects.  Call load_scene() to upload a ViewerScene to
  the GPU, then render(RenderContext) each frame.
  """

  def __init__(self) -> None:
    # Forward programs
    self._mesh_prog: int = 0
    self._skin_prog: int = 0
    self._inst_prog: int = 0
    self._wire_prog: int = 0
    self._sel_prog: int = 0
    self._sel_inst_prog: int = 0
    self._q3_prog: int = 0

    # ECS component registry
    self._registry = RenderRegistry()

    # Render passes
    self._gbuffer = GBufferPass()
    self._lighting = LightingPass()
    self._overlay: Optional[OverlayPass] = None
    self._forward: Optional[ForwardPass] = None
    self._q3: Optional[Q3StagePass] = None

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

    # G-Buffer and lighting passes
    self._gbuffer.init(_MESH_VERT, _SKIN_VERT, _INST_VERT, _GBUFFER_FRAG)
    self._lighting.init()

    # Sub-passes that share forward programs (no extra compile needed)
    self._overlay = OverlayPass(self._wire_prog, self._sel_prog, self._sel_inst_prog)
    self._forward = ForwardPass(self._mesh_prog, self._skin_prog, self._inst_prog)

    self._q3_prog = _compile_prog(_Q3STAGE_VERT, _Q3STAGE_FRAG)
    self._q3 = Q3StagePass(self._q3_prog)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glEnable(GL_MULTISAMPLE)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glClearColor(0.14, 0.14, 0.17, 1.0)

  def register_extensions(self, extensions: Iterable[RenderExtension]) -> None:
    """Register mode-supplied RenderExtensions.

    The host (AppWorld) walks every registered Mode, collects the union of
    their `render_extensions()`, dedupes, and hands the result here so the
    renderer can compile their shaders once and own their lifecycle without
    importing the modes package itself.
    """
    for ext in extensions:
      self._all_extensions.append(ext)
      ext.init()

  def cleanup(self) -> None:
    self._registry.free()
    for ext in self._all_extensions:
      ext.dispose()
    self._all_extensions = []
    self._active_extensions = []
    self._gbuffer.cleanup()
    self._lighting.cleanup()
    for prog in (
      self._mesh_prog,
      self._skin_prog,
      self._inst_prog,
      self._wire_prog,
      self._sel_prog,
      self._sel_inst_prog,
      self._q3_prog,
    ):
      if prog:
        glDeleteProgram(prog)

  # ── scene loading ─────────────────────────────────────────────────────────

  def load_scene(
    self,
    scene: ViewerScene,
    active_extensions: Iterable[RenderExtension] = (),
  ) -> None:
    """Upload a ViewerScene to GPU memory. Replaces any previously loaded scene.

    Caller passes the active mode's RenderExtensions; this preserves the
    Renderer's invariant of not importing the modes package. Extensions
    must already be registered via `register_extensions()`.
    """
    self._registry.free()
    # Drop per-scene state from the previously-active extensions before
    # rebinding _active_extensions to the new mode's set.
    for ext in self._active_extensions:
      ext.free_scene()

    self._active_extensions = list(active_extensions)
    for ext in self._active_extensions:
      ext.upload(scene)

    for eid, mesh in enumerate(getattr(scene, "meshes", ())):  # type: ignore[union-attr,attr-defined]
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
            anim_ids = [_upload_rgba(f[0], f[1], f[2]) for f in vs.anim_frames]
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

    aspect = ctx.width / max(ctx.height, 1)
    view = ctx.camera.view_matrix()
    proj = ctx.camera.projection_matrix(aspect, ctx.width, ctx.height)

    _mirror_x = np.diag(np.array([-1.0, 1.0, 1.0, 1.0], dtype=np.float32))
    proj = _mirror_x @ proj

    has_meshes = bool(self._registry.buffers)

    if has_meshes:
      light_dir = np.array([0.45, -0.85, 0.35], dtype=np.float32)
      light_dir /= np.linalg.norm(light_dir)

      opaque, transparent, q3_commands = self._build_commands(ctx)

      # 1. G-Buffer pass — opaque geometry
      self._gbuffer.begin(ctx.width, ctx.height)
      self._gbuffer.draw(self._registry, opaque, view, proj)
      self._gbuffer.end()

      # 2. Deferred lighting fullscreen quad
      self._lighting.render(
        self._gbuffer.albedo_tex, self._gbuffer.normal_tex, light_dir
      )

      # 3. Blit G-Buffer depth → default FBO
      self._gbuffer.blit_depth(ctx.width, ctx.height)
    else:
      light_dir = None
      transparent = []
      q3_commands = []

    # 4. BACKGROUND phase — sky / 2-D image / environment
    self._run_phase(RenderPhase.BACKGROUND, ctx, view, proj)

    # 5. FORWARD_OPAQUE phase — terrain / other forward opaque
    self._run_phase(RenderPhase.FORWARD_OPAQUE, ctx, view, proj)

    if not has_meshes:
      return

    # 6. FORWARD_Q3 phase — extensions + core Q3 multi-stage pass
    self._run_phase(RenderPhase.FORWARD_Q3, ctx, view, proj)
    if q3_commands and ctx.q3_enabled and self._q3 is not None:
      self._q3.render(self._registry, q3_commands, ctx, view, proj)

    # 7. TRANSPARENT phase — extensions + core alpha-blend pass
    self._run_phase(RenderPhase.TRANSPARENT, ctx, view, proj)
    if transparent and self._forward is not None:
      self._forward.render(self._registry, transparent, view, proj, light_dir)

    glDepthMask(GL_TRUE)

    # 8. OVERLAY phase — extensions + core wireframe / selection
    self._run_phase(RenderPhase.OVERLAY, ctx, view, proj)
    if self._overlay is not None:
      if ctx.wireframe:
        self._overlay.render_wireframe(self._registry, view, proj)
      if (
        ctx.selected_mesh_idx is not None
        and ctx.selected_mesh_idx in self._registry.buffers
      ):
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

    ray_origin, ray_dir = unproject_ray(mx, my, width, height, view, proj)

    best_t = float("inf")
    best_idx: Optional[int] = None

    for eid in self._registry.entity_ids():
      buf = self._registry.buffers[eid]
      xform = self._registry.transforms[eid]
      bnds = self._registry.bounds[eid]

      if buf.inst_mats_cpu is not None:
        for k in range(buf.instance_count):
          world = buf.inst_mats_cpu[k] @ xform.model_matrix
          t = ray_aabb_in_world(
            ray_origin, ray_dir, bnds.aabb_min, bnds.aabb_max, world
          )
          if t is not None and 0.0 < t < best_t:
            best_t = t
            best_idx = eid
      else:
        t = ray_aabb_in_world(
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
          draw_params.append((xform.model_matrix, None, 0, ShaderVariant.INSTANCED))
        elif xform.is_skinned:
          # Standalone bone animation
          if bones is not None:
            bc = min(len(bones), _MAX_BONES)
            bf = np.array([m.flatten() for m in bones[:bc]], dtype=np.float32).flatten()
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
                q3.append(
                  DrawCommand(
                    entity_id=eid,
                    variant=ShaderVariant.PLAIN,
                    model_matrix=inst_model,
                    primitive_idx=prim_idx,
                    instance_count=1,
                    bone_matrices_flat=None,
                    bone_count=0,
                  )
                )
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
