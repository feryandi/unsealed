"""
GL state context manager — save/restore named GL slots.

Usage:
    with gl_state(blend_func=(GL_SRC_ALPHA, GL_ONE), depth_mask=False):
        _draw_transparent_stuff()
    # blend_func and depth_mask are automatically restored here, even on exception

Phase 3.2: Where a ModernGL context is available, state reads use the mgl
context object (mgl.blend_func, mgl.depth_mask, etc.) instead of raw
glGetIntegerv / glGetBooleanv queries.  Falls back to raw GL queries if the
mgl context is not yet initialised.

Slots supported:
    blend_func      : (src, dst) tuple passed to glBlendFunc
    depth_mask      : bool passed to glDepthMask
    cull_face       : (enable: bool, face: int | None) — enable/disable culling + set face
    depth_func      : int passed to glDepthFunc
    polygon_mode    : int passed to glPolygonMode(GL_FRONT_AND_BACK, mode)
    depth_test      : bool — enable/disable GL_DEPTH_TEST
    blend           : bool — enable/disable GL_BLEND
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional, Tuple

from OpenGL.GL import (
    GL_BACK,
    GL_BLEND,
    GL_BLEND_DST_ALPHA,
    GL_BLEND_SRC_ALPHA,
    GL_CULL_FACE,
    GL_DEPTH_FUNC,
    GL_DEPTH_TEST,
    GL_DEPTH_WRITEMASK,
    GL_FILL,
    GL_FRONT_AND_BACK,
    GL_POLYGON_MODE,
    glBlendFunc,
    glCullFace,
    glDepthFunc,
    glDepthMask,
    glDisable,
    glEnable,
    glGetBooleanv,
    glGetIntegerv,
    glIsEnabled,
    glPolygonMode,
)


@contextmanager
def gl_state(
    blend_func: Optional[Tuple[int, int]] = None,
    depth_mask: Optional[bool] = None,
    cull_face: Optional[Tuple[bool, Optional[int]]] = None,
    depth_func: Optional[int] = None,
    polygon_mode: Optional[int] = None,
    depth_test: Optional[bool] = None,
    blend: Optional[bool] = None,
) -> Generator[None, None, None]:
    """
    Context manager that saves and restores the requested GL state slots.

    Args:
        blend_func   : (src_factor, dst_factor) — passed to glBlendFunc on entry.
        depth_mask   : True/False — passed to glDepthMask on entry.
        cull_face    : (enable, face) — enable/disable GL_CULL_FACE; set glCullFace(face)
                       if enable is True.  face=None leaves it unchanged.
        depth_func   : GL_LESS / GL_LEQUAL / etc — passed to glDepthFunc on entry.
        polygon_mode : GL_LINE / GL_FILL — passed to glPolygonMode(GL_FRONT_AND_BACK, ...).
        depth_test   : True/False — enable/disable GL_DEPTH_TEST.
        blend        : True/False — enable/disable GL_BLEND.
    """
    # Try to use the ModernGL context for cheaper state queries
    from .shaders import _mgl_ctx

    # ── save ──────────────────────────────────────────────────────────────────
    saved_blend_func: Optional[Tuple[int, int]] = None
    if blend_func is not None:
        if _mgl_ctx is not None:
            saved_blend_func = (int(_mgl_ctx.blend_func[0]), int(_mgl_ctx.blend_func[1]))
        else:
            src = int(glGetIntegerv(GL_BLEND_SRC_ALPHA))
            dst = int(glGetIntegerv(GL_BLEND_DST_ALPHA))
            saved_blend_func = (src, dst)
        glBlendFunc(*blend_func)

    saved_depth_mask: Optional[bool] = None
    if depth_mask is not None:
        if _mgl_ctx is not None:
            saved_depth_mask = bool(_mgl_ctx.depth_mask)
        else:
            saved_depth_mask = bool(glGetBooleanv(GL_DEPTH_WRITEMASK))
        glDepthMask(depth_mask)

    saved_cull_enabled: Optional[bool] = None
    saved_cull_face: Optional[int] = None
    if cull_face is not None:
        enable, face = cull_face
        saved_cull_enabled = bool(glIsEnabled(GL_CULL_FACE))
        from OpenGL.GL import GL_CULL_FACE_MODE
        saved_cull_face = int(glGetIntegerv(GL_CULL_FACE_MODE))
        if enable:
            glEnable(GL_CULL_FACE)
            if face is not None:
                glCullFace(face)
        else:
            glDisable(GL_CULL_FACE)

    saved_depth_func: Optional[int] = None
    if depth_func is not None:
        if _mgl_ctx is not None:
            saved_depth_func = int(_mgl_ctx.depth_func)
        else:
            saved_depth_func = int(glGetIntegerv(GL_DEPTH_FUNC))
        glDepthFunc(depth_func)

    saved_polygon_mode: Optional[int] = None
    if polygon_mode is not None:
        modes = glGetIntegerv(GL_POLYGON_MODE)
        saved_polygon_mode = int(modes[0]) if hasattr(modes, '__len__') else int(modes)
        glPolygonMode(GL_FRONT_AND_BACK, polygon_mode)

    saved_depth_test: Optional[bool] = None
    if depth_test is not None:
        if _mgl_ctx is not None:
            saved_depth_test = _mgl_ctx.depth_test
        else:
            saved_depth_test = bool(glIsEnabled(GL_DEPTH_TEST))
        if depth_test:
            glEnable(GL_DEPTH_TEST)
        else:
            glDisable(GL_DEPTH_TEST)

    saved_blend: Optional[bool] = None
    if blend is not None:
        if _mgl_ctx is not None:
            saved_blend = _mgl_ctx.blend
        else:
            saved_blend = bool(glIsEnabled(GL_BLEND))
        if blend:
            glEnable(GL_BLEND)
        else:
            glDisable(GL_BLEND)

    # ── yield ─────────────────────────────────────────────────────────────────
    try:
        yield
    finally:
        # ── restore ───────────────────────────────────────────────────────────
        if saved_blend_func is not None:
            glBlendFunc(*saved_blend_func)

        if saved_depth_mask is not None:
            glDepthMask(saved_depth_mask)

        if saved_cull_enabled is not None:
            if saved_cull_enabled:
                glEnable(GL_CULL_FACE)
                if saved_cull_face is not None:
                    glCullFace(saved_cull_face)
            else:
                glDisable(GL_CULL_FACE)

        if saved_depth_func is not None:
            glDepthFunc(saved_depth_func)

        if saved_polygon_mode is not None:
            glPolygonMode(GL_FRONT_AND_BACK, saved_polygon_mode)

        if saved_depth_test is not None:
            if saved_depth_test:
                glEnable(GL_DEPTH_TEST)
            else:
                glDisable(GL_DEPTH_TEST)

        if saved_blend is not None:
            if saved_blend:
                glEnable(GL_BLEND)
            else:
                glDisable(GL_BLEND)
