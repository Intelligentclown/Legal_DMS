# ADR-0012: Transaction Pipeline

**Status:** Accepted
**Date:** 2026-08-05

## Problem

[ADR/0010](0010-command-bus.md)'s Trade-offs section explicitly deferred a "pipeline/middleware
hook around dispatch (validation, authorization, **transaction wrapping**, logging)," and
[ADR/0011](0011-query-bus.md) repeated the same deferral for `QueryBus`. The project owner has
since requested a Transaction Pipeline directly, resolving that deferral. Because the phrase
"Transaction Pipeline" could plausibly mean several structurally different things — and one of
them (changing `CommandHandler`'s signature) would be a breaking change to the already-shipped
`CommandBus` port — three concrete options were presented to the project owner before writing any
code, per this project's "don't guess at new architecture" rule:

1. A decorator/pipeline-behavior wrapping `CommandBus` dispatch in a transaction boundary, with no
   change to `Command`/`CommandHandler`/`CommandBus`.
2. Fixing the actual, already-documented critical bug in `IMPLEMENTATION_QUEUE.md` (F1/T1–T3):
   `get_db()` never commits, causing writes to silently vanish. Unrelated to `CommandBus`.
3. A broader generic pipeline-behavior chain (transaction, logging, validation slots), of which
   only the transaction behavior would actually be implemented now.

The project owner chose option 1.

## Options Considered

(As presented above.) Option 1 was preferred because it resolves the specific trade-off both
ADR-0010 and ADR-0011 already named, without touching the unrelated `get_db()` bug (option 2 — a
real, separate P0 finding that still needs its own fix, tracked in `IMPLEMENTATION_QUEUE.md` and
still pending project-owner approval as its own body of work) or building a general
chain-of-responsibility abstraction for a single concrete use today (option 3 — the same
premature-generalization trap Stage 1 avoided everywhere else, and that ADR-0011 itself warned
against when it chose not to build a generic bus for both commands and queries).

## Decision

Three new pieces:

1. **`UnitOfWork` port** (`application/interfaces/unit_of_work.py`): `begin()`/`commit()`/
   `rollback()`, plus `UnitOfWorkError` for misuse (double-begin, or commit/rollback with no active
   transaction). Deliberately silent on *what* resource is being transacted or how a handler gains
   access to it — today, nothing does; see Trade-offs.
2. **`InMemoryUnitOfWork`** (`infrastructure/transactions/in_memory_unit_of_work.py`): the Stage-1-
   style default — tracks active/committed/rolled-back state without backing an actual resource,
   same category as `InMemoryEventBus`/`InMemoryCommandBus`/`InMemoryQueryBus`. Registered in
   `configure_container()` as **`singleton=False`** — the first non-singleton port registration in
   this project, because a unit of work is inherently per-operation state, not a shared service (see
   Reasoning).
3. **`TransactionPipelineBehavior`** (`infrastructure/commands/transaction_pipeline_behavior.py`):
   a `CommandBus` decorator. `register()` delegates to the inner bus unchanged. `dispatch()` calls
   `unit_of_work.begin()`, delegates to the inner bus's `dispatch()`, then `commit()`s if the
   handler's `Result` is a success or `rollback()`s if it's a failure; a handler exception also
   rolls back before propagating (mirrors `InMemoryCommandBus`'s own no-swallow behavior). It takes
   a `UnitOfWork` **factory**, not a single instance, so every dispatch gets its own transaction.

`configure_container()` registers `UnitOfWork -> InMemoryUnitOfWork` alongside the existing ports,
but **does not** change `CommandBus`'s own registration to the decorated version — `CommandBus`
still resolves to a plain `InMemoryCommandBus`, exactly as before this change. Applying the
pipeline is something a future feature opts into explicitly (`TransactionPipelineBehavior(inner,
factory)`), not a default silently forced onto every existing and future command dispatch.

## Reasoning

- Resolves the exact trade-off both prior ADRs named, without scope creep into the unrelated
  `get_db()` bug or a speculative generic pipeline.
- The decorator pattern keeps `Command`/`CommandHandler`/`CommandBus` completely unchanged — no
  existing test (`test_command_bus.py`, `test_container.py`) needed to change, and no future
  handler author needs to learn a new dispatch signature.
- `UnitOfWork` as non-singleton is a deliberate, documented deviation from this project's usual
  "everything registers as a singleton by default" pattern (`EventBus`, `CommandBus`, `QueryBus`,
  etc. are all naturally singletons — they're stateless routers holding handler maps). A unit of
  work is the opposite: its whole purpose is per-operation mutable state (is a transaction active,
  has it been committed). Sharing one instance across concurrent dispatches would let one
  operation's commit/rollback affect another's — silently wrong. Taking a factory (`Callable[[],
  UnitOfWork]`) in `TransactionPipelineBehavior`, resolved fresh per `dispatch()` call, is what
  makes this safe.
- Not wiring the pipeline into `CommandBus`'s own container registration avoids a silent behavior
  change to every dispatch call made before this feature existed — consistent with this project's
  standing principle (stated verbatim in `InMemoryEventBus`'s own docstring) that a deliberate
  design change is "worth its own decision, not a silent default."

## Trade-offs

- `InMemoryUnitOfWork` backs no real resource — a handler wrapped by `TransactionPipelineBehavior`
  today has no way to actually read or write anything transactionally; the pipeline currently
  proves *orchestration* (begin → dispatch → commit-or-rollback), not persistence. A real
  resource-backed implementation (e.g. wrapping a SQLAlchemy `AsyncSession`, following
  `SqlAlchemyRepository`'s precedent) is future work once a real feature needs it — deliberately not
  built now, the same "don't build the concrete resource before a consumer exists" discipline this
  project has followed throughout Stage 1.
- The port says nothing about how a handler obtains the active unit of work's underlying resource
  (a session, a connection) to actually use it. Solving that (an ambient/contextvar accessor vs. a
  `CommandHandler` signature change vs. something else) is a separate decision, deferred until a
  real handler needs it.
- `TransactionPipelineBehavior` is available but not applied anywhere by default — a future feature
  must remember to wrap its `CommandBus` with it to get transactional dispatch; nothing enforces
  that a given command *should* be transactional versus not.
- This still leaves the real, separate `get_db()` commit bug (`IMPLEMENTATION_QUEUE.md` F1/T1–T3)
  unfixed — it is not the same problem as this ADR solves and remains open, still pending
  project-owner approval as its own item.

## Future Impact

Once a real feature needs transactional command handling, it (a) builds a resource-backed
`UnitOfWork` implementation (e.g. `SqlAlchemyUnitOfWork`) satisfying this port, (b) solves the
"how does the handler reach the active resource" question as its own decision, and (c) wraps
whatever `CommandBus` it resolves with `TransactionPipelineBehavior(inner, factory)` at
registration time. None of that requires touching `Command`, `CommandHandler`, `CommandBus`, or
this ADR's `UnitOfWork` port — only adding a new implementation and opting in.
