"""T183 PostgreSQL File-Number Allocator Concurrency Regression Coverage.

Verifies ADR-0027 single-statement atomic counter allocation on PostgreSQL 16:
- Concurrent first allocation for one Matter (uninitialized sequence).
- Unique, sequential allocation results (no gaps, no duplicates).
- No primary-key UniqueViolationError (pk_file_number_sequences).
- No duplicate sequence records in file_number_sequences.
- Correct persistent counter state (next_number).
- Rollback and reuse after aborted allocation.
- Repeated executions across multiple sessions and matters.
- Cross-tenant and Matter isolation.
- Subsequent allocation after concurrent initialization.
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.persistence.models.file import File, FileNumberSequence
from app.infrastructure.persistence.sqlalchemy_file_repository import SqlAlchemyFileRepository
from tests.integration.test_t137_file_document_tenant_foundation import _seed_legacy_document
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_disposable_database_with,
)


def _make_matter_helper(engine, org_id: str):
    async def create_matter(matter_number: str) -> str:
        new_matter_id = str(uuid4())
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO matters (id, organization_id, matter_number, matter_type_id, "
                    "matter_status_id, client_id, title, opened_at) "
                    "SELECT CAST(:id AS uuid), CAST(:org AS uuid), CAST(:number AS varchar), "
                    "m.matter_type_id, m.matter_status_id, m.client_id, "
                    "CAST(:title AS varchar), now() "
                    "FROM matters m WHERE m.organization_id = CAST(:org AS uuid) LIMIT 1"
                ),
                {
                    "id": new_matter_id,
                    "org": org_id,
                    "number": matter_number,
                    "title": f"Matter {matter_number}",
                },
            )
        return new_matter_id

    return create_matter


def test_t183_allocator_concurrency_and_lifecycle_comprehensive() -> None:
    """Comprehensive PostgreSQL 16 allocator concurrency, rollback, and isolation suite."""
    url, name = provision_disposable_database_with(
        "legal_dms_t183_allocator", upgrade_target="head"
    )
    try:
        ids = asyncio.run(_seed_legacy_document(url, at_head=True))
        org_id = UUID(ids["org"])
        other_org_id = UUID(ids["other"])
        matter_id = UUID(ids["matter"])

        async def run_suite() -> None:
            engine = create_async_engine(url)
            factory = async_sessionmaker(engine, expire_on_commit=False)
            create_matter = _make_matter_helper(engine, str(org_id))

            async def allocate(
                m_id: UUID, o_id: UUID, title: str, *, commit: bool = True
            ) -> tuple[int, Exception | None]:
                try:
                    async with factory() as session:
                        repo = SqlAlchemyFileRepository(session)
                        file = File(
                            id=uuid4(),
                            organization_id=o_id,
                            matter_id=m_id,
                            file_number=0,
                            title=title,
                        )
                        await repo.allocate_and_add(file)
                        if commit:
                            await session.commit()
                        else:
                            await session.rollback()
                        return file.file_number, None
                except Exception as exc:
                    return -1, exc

            try:
                # -------------------------------------------------------------
                # 1. Concurrent first allocation on a fresh Matter (16 workers)
                # -------------------------------------------------------------
                concurrency_count = 16
                results = await asyncio.gather(
                    *(
                        allocate(matter_id, org_id, f"first-wave-{i}")
                        for i in range(concurrency_count)
                    )
                )
                errors = [err for _, err in results if err is not None]
                assert (
                    not errors
                ), f"Encountered unexpected errors during first allocation: {errors}"

                allocated_numbers = [num for num, _ in results]
                assert len(allocated_numbers) == concurrency_count
                assert (
                    len(set(allocated_numbers)) == concurrency_count
                ), "Allocated numbers contain duplicates"
                assert sorted(allocated_numbers) == list(range(1, concurrency_count + 1)), (
                    f"Allocated numbers not sequential 1..{concurrency_count}: "
                    f"{sorted(allocated_numbers)}"
                )

                # Verify exactly one sequence row exists for this Matter
                async with factory() as session:
                    seq_rows = (
                        (
                            await session.execute(
                                select(FileNumberSequence).where(
                                    FileNumberSequence.matter_id == matter_id
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    assert (
                        len(seq_rows) == 1
                    ), f"Expected exactly 1 sequence row, found {len(seq_rows)}"
                    assert seq_rows[0].next_number == concurrency_count + 1, (
                        f"Expected next_number={concurrency_count + 1}, "
                        f"got {seq_rows[0].next_number}"
                    )

                    # Verify persisted file rows match allocated numbers
                    files_in_matter = (
                        (
                            await session.execute(
                                select(File.file_number)
                                .where(File.matter_id == matter_id)
                                .order_by(File.file_number)
                            )
                        )
                        .scalars()
                        .all()
                    )
                    assert files_in_matter == list(range(1, concurrency_count + 1))

                # -------------------------------------------------------------
                # 2. Subsequent concurrent allocation after initialization (10 workers)
                # -------------------------------------------------------------
                second_wave_count = 10
                second_results = await asyncio.gather(
                    *(
                        allocate(matter_id, org_id, f"second-wave-{i}")
                        for i in range(second_wave_count)
                    )
                )
                second_errors = [err for _, err in second_results if err is not None]
                assert not second_errors, f"Encountered errors in second wave: {second_errors}"

                second_numbers = [num for num, _ in second_results]
                expected_second_range = list(
                    range(concurrency_count + 1, concurrency_count + second_wave_count + 1)
                )
                assert (
                    sorted(second_numbers) == expected_second_range
                ), f"Second wave not sequential: {sorted(second_numbers)}"

                async with factory() as session:
                    seq_row = (
                        await session.execute(
                            select(FileNumberSequence).where(
                                FileNumberSequence.matter_id == matter_id
                            )
                        )
                    ).scalar_one()
                    expected_next = concurrency_count + second_wave_count + 1
                    assert (
                        seq_row.next_number == expected_next
                    ), f"Expected next_number={expected_next}, got {seq_row.next_number}"

                # -------------------------------------------------------------
                # 3. Rollback and sequence number reuse
                # -------------------------------------------------------------
                # Allocate in a session that rolls back
                rollback_number, rollback_err = await allocate(
                    matter_id, org_id, "transient-rollback", commit=False
                )
                assert rollback_err is None
                assert rollback_number == expected_next

                # Subsequent committed allocation must reuse the exact same number
                reused_number, reused_err = await allocate(
                    matter_id, org_id, "committed-reuse", commit=True
                )
                assert reused_err is None
                assert (
                    reused_number == rollback_number
                ), f"Expected reused number {rollback_number}, but got {reused_number}"

                # Verify persistent next_number advanced by exactly 1
                async with factory() as session:
                    seq_row = (
                        await session.execute(
                            select(FileNumberSequence).where(
                                FileNumberSequence.matter_id == matter_id
                            )
                        )
                    ).scalar_one()
                    assert seq_row.next_number == expected_next + 1

                # -------------------------------------------------------------
                # 4. Repeated first-allocation trials across distinct Matters
                # -------------------------------------------------------------
                trial_workers = 8
                for trial_idx in range(5):
                    trial_matter_str = await create_matter(f"TRIAL-M-{trial_idx}")
                    trial_matter_id = UUID(trial_matter_str)

                    trial_results = await asyncio.gather(
                        *(
                            allocate(trial_matter_id, org_id, f"trial-{trial_idx}-{w}")
                            for w in range(trial_workers)
                        )
                    )
                    t_errors = [e for _, e in trial_results if e is not None]
                    assert not t_errors, f"Trial {trial_idx} had errors: {t_errors}"

                    t_nums = [n for n, _ in trial_results]
                    assert sorted(t_nums) == list(
                        range(1, trial_workers + 1)
                    ), f"Trial {trial_idx} unexpected numbers: {sorted(t_nums)}"

                    async with factory() as session:
                        trial_seq = (
                            await session.execute(
                                select(FileNumberSequence).where(
                                    FileNumberSequence.matter_id == trial_matter_id
                                )
                            )
                        ).scalar_one()
                        assert trial_seq.next_number == trial_workers + 1

                # -------------------------------------------------------------
                # 5. Concurrent allocation across multiple Matters simultaneously
                # -------------------------------------------------------------
                multi_matters = [UUID(await create_matter(f"MULTI-M-{idx}")) for idx in range(3)]
                workers_per_matter = 8
                all_tasks = []
                for m in multi_matters:
                    for w in range(workers_per_matter):
                        all_tasks.append((m, allocate(m, org_id, f"simultaneous-{w}")))

                simultaneous_results = await asyncio.gather(*(task for _, task in all_tasks))
                for idx, m in enumerate(multi_matters):
                    m_results = simultaneous_results[
                        idx * workers_per_matter : (idx + 1) * workers_per_matter
                    ]
                    m_errors = [e for _, e in m_results if e is not None]
                    assert not m_errors, f"Simultaneous Matter {m} errors: {m_errors}"
                    m_nums = [n for n, _ in m_results]
                    assert sorted(m_nums) == list(
                        range(1, workers_per_matter + 1)
                    ), f"Simultaneous Matter {m} unexpected numbers: {sorted(m_nums)}"

                # -------------------------------------------------------------
                # 6. Tenant and Matter isolation (fail-closed cross-tenant guard)
                # -------------------------------------------------------------
                # Attempt to allocate for matter_id with other_org_id
                _cross_num, cross_err = await allocate(
                    matter_id, other_org_id, "cross-tenant-attempt", commit=True
                )
                assert (
                    cross_err is not None
                ), "Cross-tenant allocation must fail closed, but succeeded"

                # Verify original matter's sequence was not corrupted by cross-tenant attempt
                async with factory() as session:
                    seq_row = (
                        await session.execute(
                            select(FileNumberSequence).where(
                                FileNumberSequence.matter_id == matter_id
                            )
                        )
                    ).scalar_one()
                    assert seq_row.organization_id == org_id
                    assert seq_row.next_number == expected_next + 1

            finally:
                await engine.dispose()

        asyncio.run(run_suite())
    finally:
        drop_disposable_database(name)
