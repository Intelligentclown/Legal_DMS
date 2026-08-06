# ADR-0014: Module Manifest Loader

**Status:** Accepted
**Date:** 2026-08-05

## Problem

The project owner requested a "Module Manifest Loader" directly, not part of a numbered stage.
Stage 1's plugin architecture (`infrastructure/modules/registry.py`: `AppModule` protocol +
`ModuleRegistry`) already documents the intended end state in its own docstring: "a future module
only needs to register itself; the core app never needs editing again to pick it up." That's true
*once a module's package has been imported* — the existing convention is that importing a module
package triggers its own `registry.register(...)` call as a side effect — but nothing in the
codebase actually says *which* packages to import, or does the importing. `main.py` calling
`registry.mount_all()` only mounts whatever is already registered; it doesn't discover anything.
This request names and closes that specific, already-implied gap.

## Options Considered

1. **Hardcode imports in `main.py`.** Simplest, but directly contradicts the stated goal ("the
   core app never needs editing again") — every new module would mean editing the composition
   root, exactly what the plugin architecture exists to avoid.
2. **A DB-backed loader reading `plugin_registry`** (the `PluginRegistryEntry` table already in
   Stage 2's schema, whose own doc comment says it "persists state for modules already registered
   via `ModuleRegistry` ... no wiring done yet"). Rejected: writing a repository/service against
   that table is real schema-wiring, which this project's charter explicitly reserves for a
   deliberate future decision ("no repositories, services, or API routes touch it yet... don't
   start Stage N+1 work by guessing") — out of scope for a request that named a loader, not a
   database integration.
3. **A file-based manifest loader**: a JSON file listing `{name, import_path, enabled}` entries;
   `ModuleManifestLoader` reads it and imports each enabled entry's dotted path, letting
   registration happen as that import's own side effect (per the existing convention) rather than
   the loader calling `registry.register(...)` itself. No new dependency (stdlib `json` +
   `importlib`).

## Decision

Option 3. `infrastructure/modules/manifest.py` adds `ModuleManifestEntry` (`name`, `import_path`,
`enabled: bool = True`), `ModuleManifest` (an immutable tuple of entries, with
`from_dict(data: dict)` parsing the `{"modules": [...]}` shape), `ModuleManifestLoader`
(`load_from_file(path)` reads and parses JSON; `import_enabled(manifest)` imports every enabled
entry via an injectable `importer` callable, defaulting to `importlib.import_module`), and
`ModuleManifestError` for every failure mode (unreadable file, malformed JSON, a missing required
field, an import failure — the last wraps the original `ImportError`).

Deliberately **not** wired into `main.py`'s startup and **not** registered in the DI container. No
real manifest file exists yet (zero business modules ship with this change), and this loader's job
— reading a file, importing packages — has real failure modes (`FileNotFoundError`,
`JSONDecodeError`, `ImportError`) that shouldn't be added to the live startup path without a real
manifest for it to point at. Proven entirely by its own tests, the same posture Stage 1 took with
the CRUD router factory ("proven with a test-only entity, never mounted into the real app").

## Reasoning

- Closes exactly the gap named in `ModuleRegistry`'s own docstring, without going further into
  schema-wiring territory (option 2) that this project's charter gates behind explicit approval.
- The loader doesn't call `registry.register(...)` itself — it only imports. This keeps the
  existing "a module registers itself on import" convention as the single source of truth for
  *how* registration happens; the loader's only new responsibility is *which* packages to import
  and *when*, which is what was actually missing.
- Injectable `importer` (defaulting to `importlib.import_module`) makes `import_enabled()`'s
  branching logic (skip disabled, stop and wrap on first failure, preserve order) fully testable
  without needing real importable packages on disk for every test case, while still keeping one
  test against the real default importer to prove the wiring actually works end to end.
- Stopping at the first import failure (rather than importing the rest and reporting partial
  success) matches this project's established "fail loudly rather than silently partially work"
  posture (`InMemoryEventBus`/`InMemoryCommandBus`/`InMemoryQueryBus` all let handler exceptions
  propagate rather than swallowing them).

## Trade-offs

- No real manifest file ships with this change, and nothing calls this loader yet — same
  "framework only, zero consumers" position as every other post-Stage-2 addition. A future module
  author still has to (a) write a manifest file, and (b) call `ModuleManifestLoader().load_from_file(...)`
  /`.import_enabled(...)` from `main.py` themselves — wiring that startup call is a deliberate future
  decision, not made here.
- No manifest schema versioning, no duplicate-name detection across entries (a duplicate `name`
  with different `import_path`s would just import both — `ModuleRegistry.register()`'s existing
  last-write-wins behavior on the `name` key is untouched and out of scope here).
- JSON only — no YAML/TOML support. Kept to stdlib `json` to avoid a new dependency for a format
  choice nothing has asked for yet; revisit if a real manifest author prefers a different format.

## Future Impact

Once a real business module exists, its manifest entry gets added to a real (still-to-be-created)
manifest file, and `main.py` gains one new startup call — `ModuleManifestLoader().import_enabled(
ModuleManifestLoader().load_from_file(settings.module_manifest_path))` (or similar) — before
`registry.mount_all()`. That's the only edit `main.py` needs for this or any subsequent module,
which is the property `ModuleRegistry`'s own docstring promised and this ADR makes actually true.
