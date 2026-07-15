"""Seal Online ``.spak`` archive plumbing.

Groups the ZipCrypto archive reader (``archive``), the key store
(``keystore``), and the offline known-plaintext key recovery
(``plaintext`` + embedded ``anchors``) in the leaf ``utils`` package,
so the ``formats`` decoder and the ``vfs`` mount path can both build
on it without inverting the layering. Importing the package pulls in
``archive`` and its light ``keystore`` dep; ``plaintext`` (which
reaches for the bundled bkcrack) loads lazily on first use.
"""

from .archive import KeyMaterial as KeyMaterial
from .archive import SpakArchive as SpakArchive
from .archive import SpakPasswordError as SpakPasswordError
