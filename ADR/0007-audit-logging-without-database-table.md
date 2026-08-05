# ADR-0007: Audit logging writes structured logs, not a database table

**Status:** Superseded by [ADR-0009](0009-audit-logs-table-reverses-adr-0007.md) — Stage 2 added
the `audit_logs` table this ADR deferred, once a concrete driving need (the charter's explicit
schema request) existed. The reasoning below was correct for Stage 1; kept for history.
**Date:** 2026-08-05

## Problem

Stage 1's charter calls for an "Audit Logging Framework." The obvious real-world implementation of
audit logging is a queryable database table (`audit_log`, with actor/action/resource/timestamp
columns) so history can be searched and reported on later. But Stage 1's charter is equally
explicit that no business entities exist yet, and a persisted, schema-defined audit table starts
to look like a business entity — it has real columns, real query needs, real retention questions —
none of which have been decided.

## Options Considered

1. **A real `audit_log` table via Alembic now.** Gets the "real" implementation built once, but
   requires deciding schema, retention, and query patterns without a concrete feature driving those
   decisions — exactly the kind of premature commitment Stage 1 is trying to avoid elsewhere
   (compare: `AuthorizationService` is permissive rather than encoding real permission rules with
   no `User`/`Role` model to check against).
2. **Structured JSON logging** to a dedicated `app.audit` logger channel, reusing the logging
   infrastructure already built in Stage 0 (console + rotating file, JSON formatter). No schema
   decisions needed now; the `AuditLogger` port stays the same regardless of what implementation
   backs it later.
3. **Skip audit logging in Stage 1 entirely.** Rejected — the charter explicitly asked for the
   framework, and the port + a working (if minimal) default costs little.

## Decision

Option 2. `application/interfaces/audit.py` defines the `AuditLogger` port
(`record(actor, action, resource_type, resource_id, metadata)`);
`infrastructure/audit/audit_logger.py`'s `LoggingAuditLogger` logs each call as a structured JSON
entry via the existing `get_logger("audit")` channel. No `audit_log` table, no Alembic migration.

## Reasoning

Mirrors the same principle applied throughout Stage 1: build the port so a real implementation can
be swapped in without touching callers, but don't guess at a schema or a real backend before a
concrete feature demands one. Audit *logging* (write-only, append-only, inspectable via log
tooling) is a legitimate, useful default in its own right — not merely a stand-in — for a system
that doesn't yet have anything worth auditing.

## Trade-offs

Audit history isn't SQL-queryable yet — finding "everything actor X did to resource Y" means
grepping/searching log files rather than running a query. Acceptable for Stage 1, where nothing
currently calls `AuditLogger.record()` at all (no business actions exist to audit).

## Future Impact

When a real feature needs queryable audit history (e.g. "show me the change history for this
Matter"), that's the point to add a persisted `AuditLogger` implementation backed by a table —
satisfying the same port, so nothing that already calls `AuditLogger.record()` needs to change.
That decision should get its own ADR at that time, since it will involve real schema and retention
choices this one deliberately deferred.
