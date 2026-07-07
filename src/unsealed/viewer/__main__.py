import sys
from pathlib import Path


def main() -> None:
  initial_file: Path | None = None
  if len(sys.argv) > 1:
    initial_file = Path(sys.argv[1])

  missing = []
  try:
    import pygame  # noqa: F401
  except ImportError:
    missing.append("pygame")
  try:
    import OpenGL  # noqa: F401
  except ImportError:
    missing.append("PyOpenGL PyOpenGL_accelerate")

  if missing:
    print("Missing required packages. Install with:")
    print(f"  pip install {' '.join(missing)}")
    sys.exit(1)

  from unsealed.viewer.app import ViewerApp

  app = ViewerApp(initial_file)
  app.run()


if __name__ == "__main__":
  main()
