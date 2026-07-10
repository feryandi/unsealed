"""`unsealed-reader recover-key` -- recover a private-server .spak key.

Private Seal Online servers repack their archives with a fixed password
and an empty zip comment, so it can't be derived. The password is a
plain constant that only appears in cleartext once the client's packed
``AutoUpdate.exe`` unpacks itself in memory. This subcommand obtains a
full memory dump (scan an existing one, attach to a running pid, or
launch ``AutoUpdate.exe`` and dump it), finds the key by testing every
string against a real ``.spak`` (CRC-verified), then writes it to the
local key store so the reader and viewer decrypt that server
automatically -- nothing sensitive committed to source.

``--exe``/``--process``/``--pid`` create a dump and so need an elevated
shell if the target is elevated (``AutoUpdate.exe`` usually is).
``--dump`` doesn't. ``--install`` auto-picks a .spak as the CRC oracle;
or pass ``--spak`` directly.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional, Tuple

from ..assets import spak_keystore
from ..utils import spak_recover


def add_arguments(parser: argparse.ArgumentParser) -> None:
  """Register the recover-key flags on ``parser`` (a subparser)."""
  src = parser.add_mutually_exclusive_group(required=True)
  src.add_argument("--dump", help="scan this existing .DMP")
  src.add_argument("--exe", help="launch this AutoUpdate.exe, then dump it")
  src.add_argument("--pid", type=int, help="dump an already-running pid")
  src.add_argument("--process", help="dump a running process by exe name")
  parser.add_argument("--install", help="game dir to auto-pick a .spak oracle from")
  parser.add_argument("--spak", help="use this specific .spak as the oracle")
  parser.add_argument(
    "--wait",
    type=float,
    default=8.0,
    help="seconds to wait after launch before dumping (--exe)",
  )
  parser.add_argument(
    "--no-save",
    action="store_true",
    help="don't write the recovered key to the local key store",
  )
  parser.add_argument(
    "--keep-dump",
    action="store_true",
    help="don't delete a dump this command created",
  )


def _find_oracle(
  install: Optional[str], spak: Optional[str]
) -> Tuple[spak_recover.Verify, str]:
  """Build a CRC verifier from --spak or a .spak under --install."""
  if spak:
    return spak_recover.make_verifier(Path(spak)), Path(spak).name
  root = Path(install)
  for p in sorted(root.rglob("*.[sS][pP][aA][kK]"), key=lambda p: p.stat().st_size):
    try:
      return spak_recover.make_verifier(p), p.name
    except Exception:
      continue  # not a usable oracle (no encrypted entries / unreadable)
  raise SystemExit(f"no .spak with encrypted entries found under {root}")


def run(args: argparse.Namespace) -> int:
  """Execute recover-key from parsed ``args``; returns an exit code."""
  if not args.install and not args.spak:
    raise SystemExit("recover-key: need --install <game dir> or --spak <file>")
  verify, oracle_name = _find_oracle(args.install, args.spak)
  label = Path(args.install).name if args.install else ""

  created: Optional[Path] = None
  launched_pid: Optional[int] = None
  try:
    if args.dump:
      dump = Path(args.dump)
    else:
      if args.exe:
        exe = Path(args.exe)
        print(f"[*] launching {exe.name}; waiting {args.wait:.0f}s to unpack ...")
        launched_pid = pid = spak_recover.launch(exe, args.wait)
      elif args.process:
        pid = spak_recover.find_pid(args.process)
        if not pid:
          raise SystemExit(f"process {args.process!r} not found (is it running?)")
      else:
        pid = args.pid
      dump = Path(os.environ.get("TEMP", ".")) / f"spakdump_{pid}.dmp"
      print(f"[*] dumping pid {pid} -> {dump}")
      spak_recover.create_full_dump(pid, dump)
      created = dump

    print(f"[*] scanning {dump.name} (oracle {oracle_name}) ...")
    key = spak_recover.scan_dump(dump, verify)
  finally:
    if launched_pid:
      spak_recover.kill(launched_pid)
    if created and not args.keep_dump and created.exists():
      try:
        created.unlink()
      except OSError:
        pass

  if key is None:
    print(
      "\n[!] no key found. Dump while the client is unpacked/at login, "
      "or capture a full dump (Task Manager -> Create dump file)."
    )
    return 1

  print("\n" + "=" * 54)
  print(f"  PASSWORD: {key.decode('latin1')!r}")
  if args.no_save:
    print(f"  (not saved; add to key store: {spak_keystore.store_path()})")
  else:
    path = spak_keystore.save_key(key, label=label)
    print(f"  saved to {path} -- archives from this server now load automatically")
  print("=" * 54)
  return 0
