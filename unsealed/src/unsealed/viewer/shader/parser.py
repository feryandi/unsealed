"""
Stateless parser for Quake 3 / Seal Online .shader text files.

A .shader file contains one or more named shader blocks:

    textures/some/name
    {
        cull none
        {
            map textures/some/base.tga
            blendFunc blend
            tcMod scroll 0.1 0.2
            tcMod rotate 45
        }
        {
            map $lightmap
            blendFunc filter
        }
    }

Usage::

    from unsealed.viewer.shader import load_shaders
    shaders = load_shaders(Path("path/to/game/dir"))
    if "field_crystal" in shaders:
        stages = shaders["field_crystal"].stages
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ── GL blend factor constants (OpenGL numeric values stored as plain ints) ─────

_GL_ZERO = 0
_GL_ONE = 1
_GL_SRC_COLOR = 0x0300
_GL_ONE_MINUS_SRC_COLOR = 0x0301
_GL_SRC_ALPHA = 0x0302
_GL_ONE_MINUS_SRC_ALPHA = 0x0303
_GL_DST_ALPHA = 0x0304
_GL_ONE_MINUS_DST_ALPHA = 0x0305
_GL_DST_COLOR = 0x0306
_GL_ONE_MINUS_DST_COLOR = 0x0307


_GL_NAME_MAP: Dict[str, int] = {
  "gl_zero": _GL_ZERO,
  "gl_one": _GL_ONE,
  "gl_src_color": _GL_SRC_COLOR,
  "gl_one_minus_src_color": _GL_ONE_MINUS_SRC_COLOR,
  "gl_src_alpha": _GL_SRC_ALPHA,
  "gl_one_minus_src_alpha": _GL_ONE_MINUS_SRC_ALPHA,
  "gl_dst_alpha": _GL_DST_ALPHA,
  "gl_one_minus_dst_alpha": _GL_ONE_MINUS_DST_ALPHA,
  "gl_dst_color": _GL_DST_COLOR,
  "gl_one_minus_dst_color": _GL_ONE_MINUS_DST_COLOR,
}


def _parse_blend_factor(token: str) -> int:
  return _GL_NAME_MAP.get(token.lower(), _GL_ONE)


# ── Data model ─────────────────────────────────────────────────────────────────


@dataclass
class Q3ShaderStage:
  """One stage (sub-block) of a Q3 shader."""

  # Texture path as written in the file; None for special tokens ($lightmap, etc.)
  map_texture: Optional[str] = None
  # animmap: fps + ordered list of texture paths (mutually exclusive with map_texture)
  anim_fps: float = 0.0
  anim_textures: List[str] = field(default_factory=list)
  blend_src: int = _GL_ONE
  blend_dst: int = _GL_ZERO
  # List of ("rotate"|"scroll"|"scale", (floats...))
  tc_mods: List[Tuple[str, Tuple[float, ...]]] = field(default_factory=list)
  tc_gen_env: bool = False
  depth_write: bool = True


@dataclass
class Q3Shader:
  """One named Q3 shader (top-level block)."""

  name: str
  # GL_BACK (0x0405) | GL_FRONT (0x0404) | None (two-sided / cull disable)
  cull_mode: Optional[int] = 0x0405  # GL_BACK default
  # True when the shader has `deformVertexes autosprite` / `autosprite2`
  is_autosprite: bool = False
  stages: List[Q3ShaderStage] = field(default_factory=list)
  raw: str = ""  # original shader text (for debugging / display)


# ── Tokenizer ──────────────────────────────────────────────────────────────────


def _tokenize(text: str) -> List[str]:
  """Strip comments and split into tokens (words + braces)."""
  # Remove // line comments
  text = re.sub(r"//[^\n]*", "", text)
  # Treat { and } as separate tokens
  text = text.replace("{", " { ").replace("}", " } ")
  return text.split()


# ── blendFunc parsing ─────────────────────────────────────────────────────────


_BLEND_ALIASES: Dict[str, Tuple[int, int]] = {
  "blend": (_GL_SRC_ALPHA, _GL_ONE_MINUS_SRC_ALPHA),
  "add": (_GL_ONE, _GL_ONE),
  "filter": (_GL_DST_COLOR, _GL_ZERO),
}


def _parse_blendfunc(tokens: List[str], pos: int) -> Tuple[int, int, int]:
  """
  Parse blendFunc starting at tokens[pos].
  Returns (src, dst, new_pos).
  Handles:
    blendFunc blend|add|filter
    blendFunc gl_src gl_dst
  """
  if pos >= len(tokens):
    return _GL_ONE, _GL_ZERO, pos

  first = tokens[pos].lower()
  if first in _BLEND_ALIASES:
    src, dst = _BLEND_ALIASES[first]
    return src, dst, pos + 1

  # Two explicit GL tokens
  src = _parse_blend_factor(first)
  pos += 1
  if pos < len(tokens) and tokens[pos].lower().startswith("gl_"):
    dst = _parse_blend_factor(tokens[pos])
    pos += 1
  else:
    dst = _GL_ZERO
  return src, dst, pos


# ── Stage parser ───────────────────────────────────────────────────────────────


def _parse_stage(tokens: List[str], start: int) -> Tuple[Q3ShaderStage, int]:
  """
  Parse a stage block starting after the opening '{' (tokens[start] is the first
  token inside the block).  Returns (stage, position_after_closing_brace).
  """
  stage = Q3ShaderStage()
  pos = start
  while pos < len(tokens):
    tok = tokens[pos].lower()

    if tok == "}":
      return stage, pos + 1

    elif tok in ("map", "clampmap"):
      pos += 1
      if pos < len(tokens):
        val = tokens[pos]
        if not val.startswith("$"):
          stage.map_texture = val
        pos += 1

    elif tok == "animmap":
      pos += 1
      if pos < len(tokens):
        try:
          stage.anim_fps = float(tokens[pos])
          pos += 1
        except ValueError:
          pass
      while pos < len(tokens):
        val = tokens[pos]
        if val in ("{", "}"):
          break
        # Stop at any known stage keyword — animmap texture list is
        # terminated by the end of the line, but our tokenizer strips
        # newlines.  A token without '.' or '/' is not a file path.
        if "." not in val and "/" not in val and not val.startswith("$"):
          break
        if not val.startswith("$"):
          stage.anim_textures.append(val)
        pos += 1

    elif tok == "blendfunc":
      pos += 1
      src, dst, pos = _parse_blendfunc(tokens, pos)
      stage.blend_src = src
      stage.blend_dst = dst

    elif tok == "tcmod":
      pos += 1
      if pos < len(tokens):
        mod_type = tokens[pos].lower()
        pos += 1
        floats: List[float] = []
        while pos < len(tokens):
          try:
            floats.append(float(tokens[pos]))
            pos += 1
          except ValueError:
            break
        stage.tc_mods.append((mod_type, tuple(floats)))

    elif tok == "tcgen":
      pos += 1
      if pos < len(tokens) and tokens[pos].lower() == "environment":
        stage.tc_gen_env = True
        pos += 1
      else:
        pos += 1  # skip unknown tcGen type

    elif tok == "depthwrite":
      stage.depth_write = True
      pos += 1

    else:
      pos += 1  # skip unknown keyword / extra token on line

  return stage, pos


# ── Shader parser ──────────────────────────────────────────────────────────────

_GL_FRONT = 0x0404
_GL_BACK = 0x0405


def _parse_shader(tokens: List[str], start: int, name: str) -> Tuple[Q3Shader, int]:
  """
  Parse a shader body starting after the opening '{'.
  Returns (shader, position_after_closing_brace).
  """
  shader = Q3Shader(name=name)
  pos = start
  while pos < len(tokens):
    tok = tokens[pos].lower()

    if tok == "}":
      return shader, pos + 1

    elif tok == "cull":
      pos += 1
      if pos < len(tokens):
        cull_val = tokens[pos].lower()
        if cull_val in ("none", "twosided", "disable"):
          shader.cull_mode = None
        elif cull_val == "front":
          shader.cull_mode = _GL_FRONT
        else:
          shader.cull_mode = _GL_BACK
        pos += 1

    elif tok == "deformvertexes":
      pos += 1
      if pos < len(tokens):
        dv = tokens[pos].lower()
        if dv in ("autosprite", "autosprite2"):
          shader.is_autosprite = True
        pos += 1

    elif tok == "{":
      # Inner stage block
      stage, pos = _parse_stage(tokens, pos + 1)
      shader.stages.append(stage)

    else:
      pos += 1  # skip top-level keywords we don't need (sort, etc.)

  return shader, pos


# ── Public API ─────────────────────────────────────────────────────────────────


def _split_shader_blocks(text: str) -> List[Tuple[str, int, int]]:
  """Locate each top-level shader block in *text* by character offset.

  Returns a list of `(name, block_start, block_end)` triples where
  `text[block_start:block_end]` is the exact `{ … }` body (inclusive of both
  braces, and including the name token that precedes it via name_start).
  The walker tracks `//` line comments and brace depth without tokenizing,
  so it can record true character offsets for `shader.raw` reconstruction.

  We index the name position too via a parallel list returned by the caller —
  here we keep the tuple small and let the caller widen the slice to include
  the name.
  """
  out: List[Tuple[str, int, int, int]] = []
  i, n = 0, len(text)
  while i < n:
    # Skip whitespace + line comments between top-level tokens.
    while i < n:
      ch = text[i]
      if ch.isspace():
        i += 1
      elif ch == "/" and i + 1 < n and text[i + 1] == "/":
        while i < n and text[i] != "\n":
          i += 1
      else:
        break
    if i >= n:
      break

    # Stray brace at top level — skip.
    if text[i] in "{}":
      i += 1
      continue

    # Read the shader name token (until whitespace or brace).
    name_start = i
    while i < n and not text[i].isspace() and text[i] not in "{}":
      i += 1
    name = text[name_start:i]
    if not name:
      continue

    # Skip whitespace + comments until the opening '{'.
    while i < n:
      ch = text[i]
      if ch.isspace():
        i += 1
      elif ch == "/" and i + 1 < n and text[i + 1] == "/":
        while i < n and text[i] != "\n":
          i += 1
      else:
        break
    if i >= n or text[i] != "{":
      # Bare token at top level (no body) — ignore and keep scanning.
      continue

    # Brace-match the body, respecting line comments.
    block_start = i
    depth = 0
    while i < n:
      ch = text[i]
      if ch == "/" and i + 1 < n and text[i + 1] == "/":
        while i < n and text[i] != "\n":
          i += 1
        continue
      if ch == "{":
        depth += 1
      elif ch == "}":
        depth -= 1
        if depth == 0:
          i += 1
          out.append((name, name_start, block_start, i))
          break
      i += 1

  # Caller wants (name, name_start, block_end). Strip the redundant
  # block_start since it's `name_start + len(name) + whitespace`.
  return [(name, name_start, block_end) for (name, name_start, _, block_end) in out]


def parse_shader_text(text: str) -> Dict[str, Q3Shader]:
  """
  Parse the contents of a single .shader file.
  Returns {lowercase_stem_name: Q3Shader}.

  Each shader's `.raw` is set to the exact source substring covering its
  `name { … }` block — useful for the in-viewer raw-text inspector.
  """
  shaders: Dict[str, Q3Shader] = {}
  for name, name_start, block_end in _split_shader_blocks(text):
    block_text = text[name_start:block_end]
    # Re-tokenize only this block so the existing _parse_shader can consume it.
    body_tokens = _tokenize(block_text)
    # body_tokens looks like: [name_token, '{', …, '}']. Locate the first '{'.
    try:
      brace_pos = body_tokens.index("{")
    except ValueError:
      continue
    shader, _ = _parse_shader(body_tokens, brace_pos + 1, name)
    shader.raw = block_text.replace(
      "\t", "    "
    )  # normalize tabs to spaces for consistent display
    key = Path(name).stem.lower()
    shaders[key] = shader
  return shaders


def load_shaders(directory: Path) -> Dict[str, Q3Shader]:
  """
  Glob all *.shader files in *directory* (non-recursive), parse them, and
  merge into a single {lowercase_stem_name: Q3Shader} dict.
  """
  result: Dict[str, Q3Shader] = {}
  for shader_file in directory.glob("*.shader"):
    try:
      text = shader_file.read_text(encoding="utf-8", errors="replace")
      result.update(parse_shader_text(text))
    except OSError:
      pass
  return result
