"""Cross-platform font stacks (Windows / macOS / Linux).

Qt substitutes a missing family, so listing per-OS choices ending in a
generic keyword guarantees a native-looking face on every platform even
when a specific font is absent.
"""

UI_FAMILIES = [
  "Segoe UI",  # Windows
  "SF Pro Text",  # macOS
  "Helvetica Neue",  # macOS fallback
  "Ubuntu",  # Linux (Ubuntu)
  "Cantarell",  # Linux (GNOME)
  "Noto Sans",  # Linux
  "DejaVu Sans",  # Linux fallback
]

MONO_FAMILIES = [
  "Cascadia Code",  # Windows (modern terminal font)
  "Consolas",  # Windows
  "SF Mono",  # macOS
  "Menlo",  # macOS fallback
  "DejaVu Sans Mono",  # Linux
  "Ubuntu Mono",  # Linux
  "Noto Sans Mono",  # Linux
]


def _stack(families: list[str], generic: str) -> str:
  quoted = ", ".join(f'"{name}"' for name in families)
  return f"{quoted}, {generic}"


UI_STACK = _stack(UI_FAMILIES, "sans-serif")
MONO_STACK = _stack(MONO_FAMILIES, "monospace")
