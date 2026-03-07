"""
RenderRegistry — entity-keyed component store for the renderer.

Each integer entity_id corresponds to one ViewerMesh in the scene
(the mesh list index).  Components are stored in four parallel dicts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable

from OpenGL.GL import (
    glDeleteBuffers,
    glDeleteTextures,
    glDeleteVertexArrays,
)

from .components import BoundsComp, GpuBufferComp, MaterialComp, TransformComp


@dataclass
class RenderRegistry:
    buffers: Dict[int, GpuBufferComp] = field(default_factory=dict)
    materials: Dict[int, MaterialComp] = field(default_factory=dict)
    transforms: Dict[int, TransformComp] = field(default_factory=dict)
    bounds: Dict[int, BoundsComp] = field(default_factory=dict)

    def add(
        self,
        eid: int,
        buf: GpuBufferComp,
        mat: MaterialComp,
        xform: TransformComp,
        bnds: BoundsComp,
    ) -> None:
        self.buffers[eid] = buf
        self.materials[eid] = mat
        self.transforms[eid] = xform
        self.bounds[eid] = bnds

    def entity_ids(self) -> Iterable[int]:
        return list(self.buffers.keys())

    def free(self) -> None:
        """Delete all GL objects and reset all component dicts."""
        for buf in self.buffers.values():
            if buf.instance_vbo:
                glDeleteBuffers(1, [buf.instance_vbo])
            glDeleteBuffers(1, [buf.vbo])
            glDeleteVertexArrays(1, [buf.vao])
        for mat in self.materials.values():
            for prim in mat.primitives:
                glDeleteBuffers(1, [prim.ebo])
                if prim.texture_id is not None:
                    glDeleteTextures(1, [prim.texture_id])
                for stage in prim.q3_stages:
                    if stage.tex_id is not None:
                        glDeleteTextures(1, [stage.tex_id])
                    for tid in stage.anim_tex_ids:
                        glDeleteTextures(1, [tid])
        self.buffers.clear()
        self.materials.clear()
        self.transforms.clear()
        self.bounds.clear()
