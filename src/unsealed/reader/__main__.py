import argparse
import os
import sys
from pathlib import Path
import traceback

from unsealed.reader.commands import recover_key
from unsealed.reader.pipelines.main_pipeline import MainPipeline


def _reattach_parent_console() -> None:
  """Make CLI output visible from a frozen windowed build.

  The GUI bundle is built windowless (no console) for a clean desktop
  app, but the same exe also runs the `decode`/`recover-key` subcommands
  — whose output would otherwise vanish. When invoked WITH arguments
  (i.e. a subcommand) from a terminal, reattach to that parent console
  and rebind stdout/stderr so the output shows. A no-arg launch (the
  GUI) stays windowless. No-op unless this is a frozen Windows build.
  """
  if not getattr(sys, "frozen", False) or os.name != "nt" or len(sys.argv) <= 1:
    return
  try:
    import ctypes

    if not ctypes.windll.kernel32.AttachConsole(-1):  # ATTACH_PARENT_PROCESS
      return
    sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
    sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
  except Exception:
    pass  # best-effort: never let console plumbing crash the command


def _resolve_output_dir(output: str | None, root_path: str) -> Path | None:
  """Resolve the -o value to an absolute dir, creating it if given."""
  if not output:
    return None
  output_dir = Path(output) if os.path.isabs(output) else Path(root_path) / output
  os.makedirs(output_dir, exist_ok=True)
  return output_dir


def run_decode(paths: list[str], output_dir: Path | None) -> int:
  """Decode each path via its pipeline; return an exit code."""
  root_path = os.getcwd()
  pipeline = MainPipeline()
  failures = 0
  for name in paths:
    filepath = Path(name) if os.path.isabs(name) else Path(root_path) / name
    out = output_dir or filepath.parent
    try:
      pipeline.run(filepath, out)
      print(f"OK: {filepath} -> {out}")
    except Exception as e:
      failures += 1
      traceback.print_exc()
      print(f"ERROR: {filepath}: {e}")
  return 1 if failures else 0


def run() -> None:
  """Entry point: GUI by default, else a decode/recover-key command."""
  _reattach_parent_console()

  parser = argparse.ArgumentParser(
    prog="unsealed-reader",
    description="Unsealed - Seal Online file decoder/encoder",
  )
  parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="Output directory path (default: same as input file directory)",
  )

  # Subcommands are optional: no command -> GUI.
  sub = parser.add_subparsers(dest="command")

  decode = sub.add_parser(
    "decode",
    help="Decode one or more game files without GUI (non-interactive)",
    description=(
      "Decode each FILE via its matching pipeline, without the GUI or the "
      "REPL. Output goes to -o, or next to each input file if -o is omitted."
    ),
  )
  decode.add_argument(
    "paths",
    metavar="FILE",
    nargs="+",
    help="game file(s) to decode (.ms1, .act, .map, .spak, .edt, …)",
  )
  decode.add_argument(
    "-o",
    "--output",
    type=str,
    default=argparse.SUPPRESS,  # don't clobber a top-level -o when omitted
    help="output directory (default: each input file's directory)",
  )

  recover = sub.add_parser(
    "recover-key",
    help="Recover a private-server .spak decryption key from client memory",
    description=recover_key.__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  recover_key.add_arguments(recover)

  args = parser.parse_args()

  if args.command == "recover-key":
    raise SystemExit(recover_key.run(args))

  output_dir = _resolve_output_dir(getattr(args, "output", None), os.getcwd())

  if args.command == "decode":
    raise SystemExit(run_decode(args.paths, output_dir))

  # Lazily import so the non-GUI subcommands never pull in Qt.
  from unsealed.reader.gui import run_gui

  raise SystemExit(run_gui(output_dir))


if __name__ == "__main__":
  run()
