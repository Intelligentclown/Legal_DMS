"""Module manifest: a declarative list of which `AppModule`-providing
packages to import at startup, read from a JSON file.

Closes a gap `ModuleRegistry`'s own docstring leaves open: "a future module
only needs to register itself; the core app never needs editing again to
pick it up" -- true once a module is *imported* (registration is expected to
happen as an import side effect, following that existing convention), but
something still has to know which packages to import in the first place.
`ModuleManifestLoader` is that something.

Deliberately not wired into `main.py`'s startup and not registered in the DI
container: no real manifest file exists yet (zero business modules), and
this loader's whole job -- reading a file, importing packages -- has real
failure modes (missing file, malformed JSON, missing package) that
shouldn't be added to the live startup path without a real manifest for it
to point at. Proven by its own tests only, same posture Stage 1 took with
the CRUD router factory. See ADR-0014.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


class ModuleManifestError(Exception):
    """Raised when a manifest file can't be read/parsed, an entry is
    missing a required field, or an entry's module fails to import."""


@dataclass(frozen=True, slots=True)
class ModuleManifestEntry:
    name: str
    import_path: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    entries: tuple[ModuleManifestEntry, ...] = ()

    @classmethod
    def from_dict(cls, data: dict) -> ModuleManifest:
        entries = []
        for index, raw in enumerate(data.get("modules", [])):
            try:
                entries.append(
                    ModuleManifestEntry(
                        name=raw["name"],
                        import_path=raw["import_path"],
                        enabled=raw.get("enabled", True),
                    )
                )
            except KeyError as exc:
                raise ModuleManifestError(
                    f"Manifest entry {index} is missing required field {exc}"
                ) from exc
        return cls(entries=tuple(entries))


class ModuleManifestLoader:
    """Reads a `ModuleManifest` from a JSON file and imports its enabled
    entries. Registration itself happens as each imported module's own
    import-time side effect (calling `registry.register(...)`) -- this
    loader only knows how to find and import the right packages.
    """

    def __init__(self, importer: Callable[[str], ModuleType] = importlib.import_module) -> None:
        self._importer = importer

    def load_from_file(self, path: str | Path) -> ModuleManifest:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise ModuleManifestError(f"Could not read manifest file {path!r}: {exc}") from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ModuleManifestError(f"Manifest file {path!r} is not valid JSON: {exc}") from exc

        return ModuleManifest.from_dict(data)

    def import_enabled(self, manifest: ModuleManifest) -> list[str]:
        """Import every enabled entry's module, in manifest order. Returns
        the names actually imported. Raises `ModuleManifestError` (wrapping
        the original `ImportError`) on the first import failure, rather
        than importing the rest and reporting partial success."""
        imported: list[str] = []
        for entry in manifest.entries:
            if not entry.enabled:
                continue
            try:
                self._importer(entry.import_path)
            except ImportError as exc:
                raise ModuleManifestError(
                    f"Failed to import module {entry.name!r} from {entry.import_path!r}: {exc}"
                ) from exc
            imported.append(entry.name)
        return imported
