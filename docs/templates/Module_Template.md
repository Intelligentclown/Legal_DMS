# Module Template

**Purpose:** The skeleton for documenting a new code module — a new row in
[docs/ModuleRegistry.md](../ModuleRegistry.md)'s per-stage tables, expanded here with the narrative
detail the registry's compact table format doesn't have room for. Use this template when a module
is substantial enough to need more explanation than a single table row can carry (a new port +
default implementation, a new subsystem); for something genuinely simple, adding a row directly to
[docs/ModuleRegistry.md](../ModuleRegistry.md) is enough and this template is unnecessary ceremony.

**When to use:** Introducing a new `application/interfaces/*.py` port, a new
`infrastructure/<name>/` implementation package, or an equivalent frontend module — anything that
would otherwise need its purpose reverse-engineered from source by a future reader.

**Copy destination:** Either (a) expand the relevant row in
[docs/ModuleRegistry.md](../ModuleRegistry.md) directly using this shape as a guide, or (b) for a
module substantial enough to need standalone narrative, add a subsection to
[docs/Architecture.md](../Architecture.md) using this shape, and keep the
[docs/ModuleRegistry.md](../ModuleRegistry.md) row as the compact pointer to it.

---

## Module: \<module.path\>

- **Location:** `backend/src/app/<layer>/<module>/` (or the frontend equivalent path).
- **Layer:** domain | application | infrastructure | presentation | workers (backend) — or the
  frontend equivalent (domain/application/infrastructure/presentation/shared).
- **Purpose:** What this module is for, in one or two sentences — the "why does this exist," not a
  restatement of its file list.
- **Public Interface:** The names a caller actually imports — class names, function names,
  exported constants. Not every internal helper, just the contract.
- **Dependencies:** What this module depends on (other ports, external libraries, config). Note
  explicitly if it's deliberately dependency-free (e.g. a pure domain module).
- **Status:** Not Started | Planned | In Progress | Complete (framework only) | Complete (default
  implementation, real backend deferred) | Complete | Deprecated — match
  [docs/ModuleRegistry.md](../ModuleRegistry.md)'s existing status vocabulary rather than inventing
  a new one.
- **Related ADRs:** Which architecture decision record(s) govern this module's design.
- **Testing:** Where its tests live and what they actually prove (not just "has tests" — this
  project's convention is to describe *what* is proven, e.g. "double-registration errors,
  unregistered-dispatch errors, exception propagation," not just "unit tests exist").
- **Owner:** Who owns this module (see [docs/ModuleRegistry.md](../ModuleRegistry.md)'s "Owner:
  AI" convention and its explanatory footnote).
- **Notes:** Anything a future reader would otherwise have to discover the hard way — a non-obvious
  constraint, a footgun, a deliberate deviation from this project's usual pattern (e.g. "registered
  non-singleton, the one exception to this project's singleton-by-default convention").
