from .base import Camera

compute_bounds = Camera.compute_bounds  # re-export for mode pipelines

__all__ = ["Camera", "compute_bounds"]
