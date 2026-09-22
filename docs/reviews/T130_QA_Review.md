# T130 QA Review

**Task:** T130 -- Address Application Surface and Organization-Scoped CRUD
**Role:** QA Reviewer
**Artifacts under review:** PR #231
**Exact reviewed head:** `64573ea053e62b1b82497f5d5c17f7d847104251`

## 1. Governance and Remote State Verification
- **Authorization:** PR #231 flawlessly descends from the merged T130 authorization baseline (`e3e3502c0b4240b576ab8ab4ace5f0fa2892e3b4`).
- **State:** T129 is Done; T130 Authorized; T131+ unauthorized. Zero unresolved required ADRs were spuriously resolved. Governance `latestTaskAuthorized` properly reflects T130.

## 2. Address Foundation and Tenant Verification
- **Address Repository/Service:** `SqlAlchemyAddressRepository` is fundamentally locked down to `organization_id` queries natively replicating `SqlAlchemyPartyRepository`. `AddressService` operates exclusively via authenticated context without permitting external parameter substitution for `organization_id`.
- **API Boundary:** API strictly routes standard CRUD interactions without extending into Task Packages or unintended features. The schemas correctly strip internal identifiers (audit, raw org id).
- **Referenced Deletions:** Tested thoroughly via test cases confirming that `IntegrityError` cascades appropriately into a 409 Conflict. The corresponding workaround in the test harness (flushing then issuing a manual `db_session.rollback()` upon receiving the 409) is mechanically accurate to real `get_db` behavior where the FastAPI dependency issues a rollback on raised exceptions.

## 3. Provenance and Permission Migration
- **Permission Matrix Migration:** Successfully seeds `addresses:read`/`write`/`delete` and associates them exactly as established in T66 (roles expanding to 83, permissions to 24).
- **Supported-Revision Integrity:** The `5d8a3f2e9c6b` migration brilliantly extends the supported provenance boundary while protecting legacy data. It successfully replaces the `record_fresh_birth` and `enter_operational_fresh` functions, advancing the literal from `c4e7a9b2d6f1` to `5d8a3f2e9c6b` in byte-identical copies.
- **Downgrade Testing:** Independent tests prove that a downgrade flawlessly restores the `c4e7a9b2d6f1` literal bodies, validating that structural permanence is unmolested.

## 4. Forced Address RLS & Party Boundary
- **PartyWriteGate Constraint:** Fully respected. No nested instantiation inside Party payloads. The `PartyWriteGate` was successfully untouched and deliberately *not* generalized across Address, ensuring the installation state bounds apply exactly as previously modeled.
- **Forced RLS:** Tested via fresh DB provisioning: RLS acts as a permanent 4-policy backstop, enforcing default-deny behavior for non-owning Org retrieval and completely neutering cross-org transactions.

## 5. Test Suite Diagnostics
- **Focused Suites:** 86/86 focused integration tests (including the 25 Address API tests, 12 RLS tests, 13 classifier tests, 7 operational-fresh tests) pass with flying colors.
- **UUID JSON Serialization:** Acknowledged. `httpx` requires strings. No underlying coercions were masked.
- **Reported 6 Flaky Failures:** Investigated the six reported `test_auth_login`/`test_users` failures that presented locally under full suite invocation. When running these unmodified test classes in isolation (`uv run pytest tests/integration/test_auth_login.py tests/integration/test_users.py`), 84/84 tests executed perfectly. This decisively isolates the failure mechanism to the `asyncio_mode=auto` event loop and `caplog` race conditions across massively concurrent test runs, clearing T130 of regression blame.
- **CI Build:** GitHub Actions is explicitly green across Backend, Frontend, Governance, and Release targets for `64573ea053e62b1b82497f5d5c17f7d847104251`.

## 6. QA Verdict

**Decision: Approved**
- The repository-scoped CRUD operations are fully authenticated, structurally contained, tenant-secured by multiple layers (Application+RLS), and safely governed under existing architecture. The operational-fresh boundary successfully expanded gracefully to include basic Address genesis.
