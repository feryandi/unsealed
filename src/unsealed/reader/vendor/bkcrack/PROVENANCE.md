# bkcrack (vendored, fetched at build time)

[bkcrack](https://github.com/kimci86/bkcrack) recovers the internal keys of a
traditional PKWARE ZipCrypto archive from known plaintext (the Biham–Kocher
attack). The reader uses it to recover a private-server `.spak` key **without a
memory dump**, and because bkcrack runs on Windows, macOS and Linux this
replaces the old Windows-only, elevation-requiring recovery path.

Why the attack has known plaintext: a private server repacks its archives with
plain `zlib` defaults, so the compressed stream of any entry that also exists in
a readable (official or already-cracked) archive can be regenerated
byte-for-byte and fed to bkcrack. The recovered keys are shared across every
archive of that server.

## Not committed to git

The executables are **fetched at build time, not stored in git** (this repo
keeps binaries out of history). Only this file and `LICENSE.txt` are committed;
the binaries are git-ignored. Download them with:

```
python -m unsealed.reader.vendor.fetch          # this host only
python -m unsealed.reader.vendor.fetch --all     # every platform
```

`fetch.py` is the single source of truth for the version, download URLs, and
per-binary SHA-256 (it verifies the hash before writing). The release workflow
runs it before PyInstaller; the spec bundles the host build.

## Version & license

- **bkcrack 1.8.1** (built 2025-10-25), from
  <https://github.com/kimci86/bkcrack/releases/tag/v1.8.1>.
- Distributed under the **zlib License** (permissive; binary redistribution
  allowed provided the notice is kept). The upstream notice is committed
  verbatim in [`LICENSE.txt`](./LICENSE.txt). The binaries are the unmodified
  upstream release artifacts.

## Binaries (fetched into this directory)

| File | Platform | Upstream asset |
|------|----------|----------------|
| `bkcrack-windows-x86_64.exe` | Windows x64 | `bkcrack-1.8.1-win64.zip` |
| `bkcrack-macos-arm64` | macOS Apple Silicon | `bkcrack-1.8.1-macOS-arm64.tar.gz` |
| `bkcrack-macos-x86_64` | macOS Intel | `bkcrack-1.8.1-macOS-x86_64.tar.gz` |
| `bkcrack-linux-x86_64` | Linux x86-64 | `bkcrack-1.8.1-Linux-x86_64.tar.gz` |
| `bkcrack-linux-aarch64` | Linux ARM64 | `bkcrack-1.8.1-Linux-aarch64.tar.gz` |

SHA-256 values live next to each entry in `fetch.py`.

## Updating the version

1. Bump `BKCRACK_VERSION` and the `_ASSETS` table (asset names + SHA-256) in
   `fetch.py`; refresh `LICENSE.txt` from the new release if it changed.
2. Update the version/date above.
3. `python -m unsealed.reader.vendor.fetch --all --force` to re-verify.
