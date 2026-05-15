from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from .animation import AnimationComponent

if TYPE_CHECKING:
    from ..context import ViewerContext


@dataclass
class SceneComponent:
    context: Optional["ViewerContext"] = None
    anim: AnimationComponent = field(default_factory=AnimationComponent)
    current_path: Optional[Path] = None
    selected_mesh_idx: Optional[int] = None
    # Shader-detail viewer state: which shader to display.
    # `selected_shader` holds a Q3Shader instance (typed Any to avoid pulling
    # the shader package into the components layer).
    selected_shader: Optional[Any] = None
