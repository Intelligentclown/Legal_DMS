# ADR-0008: Stage 2 SQLAlchemy models are persistence-layer models, not domain entities

**Status:** Accepted
**Date:** 2026-08-05

## Problem

Stage 2 builds the complete database schema (49 tables) before any business feature exists to
consume it. Clean Architecture (established in
[ADR-0002](0002-clean-architecture-layering.md)) draws a line between `domain/` (pure entities,
no framework imports) and `infrastructure/persistence/` (SQLAlchemy implementations of
`application/interfaces` ports). With 49 tables and zero business logic yet, should these new
SQLAlchemy models be modeled as `domain/` entities with a separate ORM mapping layer, or as plain
persistence-layer models?

## Options Considered

1. **Domain entities + separate ORM mapping layer.** The "purest" Clean Architecture answer —
   `domain/matter.py` defines a framework-free `Matter` entity, `infrastructure/persistence/`
   defines a separate SQLAlchemy `MatterModel` and explicit `to_entity()`/`to_model()` mapping
   functions. Correct in the abstract, but Stage 2 has no business rules to justify what the
   domain entity's *shape* or *behavior* should be beyond "the same columns as the table" — every
   mapping function would be a mechanical 1:1 copy with no real logic, guessed at with no
   consuming use case to validate against.
2. **SQLAlchemy models directly as the persistence layer, no separate domain entity.** Matches
   what Stage 1's `SqlAlchemyRepository[ModelT]` already assumes ("the model is the entity" —
   see its own docstring) and what `AbstractRepository[T]`'s `SupportsId` Protocol already
   requires (structural typing, not inheritance). Models live in
   `infrastructure/persistence/models/`, organized by domain area, as plain columns + FK
   constraints.

## Decision

Option 2. All 49 Stage 2 tables are defined as SQLAlchemy models in
`infrastructure/persistence/models/`, with no corresponding `domain/` entity and no
`relationship()` ORM navigation declared (see the module docstring in
`infrastructure/persistence/models/__init__.py` — relationship() is deliberately deferred to the
first feature that needs a specific traversal, for the same "don't guess with nothing to validate
against" reason).

## Reasoning

- Directly consistent with the precedent Stage 1 already set for `SqlAlchemyRepository[ModelT]`:
  "the model IS the entity being persisted... a feature that needs a domain model distinct from
  its persistence shape can wrap this... nothing here forces that distinction where it isn't
  needed yet."
- A hand-written domain entity with no business rules is pure ceremony — every field would just
  mirror the table, and every mapping function would be a straight copy. That's exactly the kind
  of speculative abstraction the project's coding standards warn against.
- `AbstractRepository[T]`'s `SupportsId` Protocol (structural typing — "anything with a UUID id")
  was specifically designed in Stage 1 to accept either a real domain entity or a SQLAlchemy model
  without caring which. Nothing about Stage 1's repository/service layer requires a domain entity
  to exist.

## Trade-offs

- If a future business feature discovers it genuinely needs domain logic distinct from the
  persisted shape (e.g. a `Matter` aggregate that enforces invariants across several tables), that
  feature will need to introduce a real domain entity *then*, with real behavior to justify it —
  not retrofitted speculatively now.
- No ORM `relationship()` means query code must currently use explicit joins/separate queries
  rather than `matter.documents`-style navigation. Acceptable since no query code exists yet;
  the first repository that needs a specific traversal adds the specific `relationship()`
  with the cascade/loading behavior *that* use case actually needs.

## Future Impact

When the first real business feature is built (Stage 3+), its service/repository layer decides
per-entity whether the SQLAlchemy model is sufficient as-is or needs a domain entity wrapping it —
that decision happens with a real use case to validate against, not speculatively here. Don't
retroactively add domain entities for all 49 tables "for completeness" — add them exactly when a
feature's business rules require them.
