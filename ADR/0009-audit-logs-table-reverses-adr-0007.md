# ADR-0009: `audit_logs` table reverses ADR-0007

**Status:** Accepted (supersedes [ADR-0007](0007-audit-logging-without-database-table.md))
**Date:** 2026-08-05

## Problem

[ADR-0007](0007-audit-logging-without-database-table.md) (Stage 1) deliberately deferred a
database-backed audit table: `AuditLogger.record()` writes structured JSON logs instead, on the
reasoning that "audit history isn't SQL-queryable yet... acceptable for Stage 1, where nothing
currently calls `AuditLogger.record()` at all." That ADR explicitly named its own reversal
condition: *"When a real feature needs queryable audit history... that's the point to add a
persisted `AuditLogger` implementation."*

Stage 2's charter directly asks for an `AuditLogs` table as part of the complete database schema.

## Options Considered

1. **Leave ADR-0007 as-is, don't add the table.** Rejected — Stage 2's charter is explicit and
   unambiguous about wanting this table; silently ignoring it isn't an option, and there's no
   principled reason to refuse a database-schema stage's direct request for a database table.
2. **Add the table without acknowledging ADR-0007.** Rejected — leaves two contradictory documents
   in `/ADR` with no link between them, exactly what the project's documentation discipline exists
   to prevent ("never change architecture without documenting why").
3. **Add the table, and record this ADR explaining that Stage 2's explicit ask is precisely the
   "concrete driving need" ADR-0007 said to wait for.**

## Decision

Option 3. `infrastructure/persistence/models/activity.py` now defines `AuditLog`, mirroring
`AuditLogger.record()`'s parameters exactly (`actor_id`, `action`, `resource_type`, `resource_id`,
a `metadata` JSONB column exposed as `audit_metadata` in Python to avoid shadowing SQLAlchemy's
own `Base.metadata`, `created_at`).

## Reasoning

This isn't a case of "Stage 1 got it wrong" — ADR-0007's reasoning was sound *at the time*: no
schema existed yet, and guessing at columns/retention with nothing driving the design would have
been premature. Stage 2 is exactly the concrete need that changes the calculus: the charter asks
for a complete schema, `AuditLogger`'s port shape already exists and is stable, and mapping it to
a table is now a straightforward, well-justified addition rather than a guess.

## Trade-offs

The table exists but nothing writes to it yet — `LoggingAuditLogger` (the Stage 1 default,
registered in the DI container) is unchanged and still only logs to files. A
`SqlAlchemyAuditLogger` implementing the same `AuditLogger` port against this table is future
work, not part of Stage 2 (which builds schema only, no repositories/services per its charter).

## Future Impact

When a future stage wires a `SqlAlchemyAuditLogger`, it satisfies the existing `AuditLogger` port
(`application/interfaces/audit.py`) — no port changes needed, `container.register(AuditLogger,
SqlAlchemyAuditLogger)` replaces the `LoggingAuditLogger` registration, and every existing caller
keeps working unchanged. This is the DI-container-and-ports architecture (ADR-0006) working as
intended: the concrete implementation swapped, nothing else did.
