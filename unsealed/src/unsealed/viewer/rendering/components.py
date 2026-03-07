"""
Single-responsibility GPU components for the ECS render registry.

Each component holds one concern: buffer handles, material/primitive data,
the local transform, or the CPU-side bounding box for picking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from numpy.typing import NDArray

from .types import _GpuPrimitive


@dataclass
class GpuBufferComp:
    """VAO, VBO, and optional per-instance data for one mesh entity."""

    vao: int
    vbo: int
    instance_vbo: int = 0
    instance_count: int = 1
    inst_mats_cpu: Optional[NDArray] = None  # shape (N, 4, 4) float32


@dataclass
class MaterialComp:
    """All primitives (index buffers + textures) for one mesh entity."""

    primitives: List[_GpuPrimitive] = field(default_factory=list)


@dataclass
class TransformComp:
    """Local model matrix and skinning flag for one mesh entity."""

    model_matrix: NDArray  # (4, 4) float32, row-major
    is_skinned: bool = False


@dataclass
class BoundsComp:
    """Local-space AABB for CPU ray picking."""

    aabb_min: NDArray  # (3,) float32
    aabb_max: NDArray  # (3,) float32
