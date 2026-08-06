"""Tests for the module manifest and its loader, isolated to a pytest
tmp_path for file-reading tests so nothing touches the real project
directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.infrastructure.modules.manifest import (
    ModuleManifest,
    ModuleManifestEntry,
    ModuleManifestError,
    ModuleManifestLoader,
)


class TestModuleManifestFromDict:
    def test_parses_entries_with_explicit_fields(self) -> None:
        manifest = ModuleManifest.from_dict(
            {
                "modules": [
                    {"name": "sale_deed", "import_path": "app.modules.sale_deed", "enabled": False}
                ]
            }
        )

        assert manifest.entries == (
            ModuleManifestEntry(
                name="sale_deed", import_path="app.modules.sale_deed", enabled=False
            ),
        )

    def test_enabled_defaults_to_true_when_omitted(self) -> None:
        manifest = ModuleManifest.from_dict(
            {"modules": [{"name": "sale_deed", "import_path": "app.modules.sale_deed"}]}
        )

        assert manifest.entries[0].enabled is True

    def test_empty_modules_list_produces_no_entries(self) -> None:
        manifest = ModuleManifest.from_dict({"modules": []})

        assert manifest.entries == ()

    def test_missing_modules_key_produces_no_entries(self) -> None:
        manifest = ModuleManifest.from_dict({})

        assert manifest.entries == ()

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ModuleManifestError, match="missing required field"):
            ModuleManifest.from_dict({"modules": [{"name": "sale_deed"}]})


class TestModuleManifestLoaderLoadFromFile:
    def test_loads_a_valid_manifest_file(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "modules.json"
        manifest_path.write_text(
            json.dumps({"modules": [{"name": "a", "import_path": "app.modules.a"}]}),
            encoding="utf-8",
        )
        loader = ModuleManifestLoader()

        manifest = loader.load_from_file(manifest_path)

        assert manifest.entries == (ModuleManifestEntry(name="a", import_path="app.modules.a"),)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        loader = ModuleManifestLoader()

        with pytest.raises(ModuleManifestError, match="Could not read manifest file"):
            loader.load_from_file(tmp_path / "does-not-exist.json")

    def test_malformed_json_raises(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "modules.json"
        manifest_path.write_text("{not valid json", encoding="utf-8")
        loader = ModuleManifestLoader()

        with pytest.raises(ModuleManifestError, match="not valid JSON"):
            loader.load_from_file(manifest_path)


class TestModuleManifestLoaderImportEnabled:
    def test_imports_only_enabled_entries_in_order(self) -> None:
        imported: list[str] = []
        loader = ModuleManifestLoader(importer=imported.append)
        manifest = ModuleManifest(
            entries=(
                ModuleManifestEntry(name="a", import_path="pkg.a", enabled=True),
                ModuleManifestEntry(name="b", import_path="pkg.b", enabled=False),
                ModuleManifestEntry(name="c", import_path="pkg.c", enabled=True),
            )
        )

        result = loader.import_enabled(manifest)

        assert result == ["a", "c"]
        assert imported == ["pkg.a", "pkg.c"]

    def test_import_failure_raises_and_stops(self) -> None:
        def failing_importer(import_path: str) -> None:
            raise ImportError(f"No module named {import_path!r}")

        loader = ModuleManifestLoader(importer=failing_importer)
        manifest = ModuleManifest(
            entries=(ModuleManifestEntry(name="missing", import_path="no.such.module"),)
        )

        with pytest.raises(ModuleManifestError, match="Failed to import module 'missing'"):
            loader.import_enabled(manifest)

    def test_default_importer_imports_a_real_module(self) -> None:
        loader = ModuleManifestLoader()
        manifest = ModuleManifest(
            entries=(ModuleManifestEntry(name="stdlib", import_path="dataclasses"),)
        )

        result = loader.import_enabled(manifest)

        assert result == ["stdlib"]

    def test_default_importer_wraps_a_real_import_error(self) -> None:
        loader = ModuleManifestLoader()
        manifest = ModuleManifest(
            entries=(
                ModuleManifestEntry(
                    name="missing", import_path="no_such_package.definitely_missing"
                ),
            )
        )

        with pytest.raises(ModuleManifestError, match="Failed to import module 'missing'"):
            loader.import_enabled(manifest)
