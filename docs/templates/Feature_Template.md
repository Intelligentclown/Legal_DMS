# Feature Template

**Purpose:** The skeleton for a new entry in [docs/FeatureRegistry.md](../FeatureRegistry.md).
This project's registry currently has no real business-feature entries (Stages 0–2 were
infrastructure/framework/schema only, by charter) — the first real feature to be wired to the Stage
2 schema will be the first real use of this template. See
[docs/FeatureRegistry.md](../FeatureRegistry.md) for the (currently infrastructure-only) precedent
entry, "System Health Check," and expand from its shape.

**When to use:** Any time a real business feature (something a legal documentation office's staff
would recognize as a capability — Matter Management, Client Management, Document Automation, etc.)
is planned or built. Not for framework/infrastructure additions with no business-facing capability
— those get an ADR (via [ADR_Template.md](ADR_Template.md)) and a [Module_Template.md](Module_Template.md)
entry instead, not a feature entry.

**Copy destination:** Append as a new `### <Feature Name>` section within
[docs/FeatureRegistry.md](../FeatureRegistry.md) — don't create a separate file per feature; the
registry is meant to be read as one document covering every feature.

---

### \<Feature Name\>

- **Description:** What the feature does, for whom, in plain language a non-technical stakeholder
  could read.
- **Status:** Not Started | Planned | In Progress | Completed | Deferred | Cancelled
- **Stage:** Which numbered stage this feature belongs to.
- **Dependencies:** Other features, ports, or schema sections this feature requires to exist first.
- **Related ADRs:** Any architecture decision records this feature's design relies on or introduced.
- **Related APIs:** The routes this feature adds or uses — link to their
  [docs/API.md](../API.md) entries (see [APIEndpointTemplate.md](APIEndpointTemplate.md) for adding
  a new one).
- **Related Database Tables:** Which Stage 2 tables this feature reads from or writes to — link to
  [docs/Database.md](../Database.md).
- **Related UI Screens:** Which frontend pages/components implement this feature.
- **Acceptance Criteria:** What must be true for this feature to be considered done — specific and
  checkable, not aspirational.
- **Testing:** What test coverage exists (unit, integration, E2E) and where.
- **Future Improvements:** Known gaps or deferred enhancements, each with a name reason it wasn't
  done now (not scope, not time-boxed yet, waiting on a dependency, etc.) — mirror this project's
  existing convention of naming *why* something is deferred, not just that it is.
