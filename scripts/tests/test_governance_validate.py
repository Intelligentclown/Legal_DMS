#!/usr/bin/env python3
"""Tests for scripts/governance_validate.py.

Stdlib unittest only, by design -- see governance_validate.py's own
module docstring for why this tool avoids backend/frontend dependencies.

Run directly: `python scripts/tests/test_governance_validate.py`
Or:           `python -m unittest discover -s scripts/tests`
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import governance_validate as gv  # noqa: E402


class TestParseTaskRows(unittest.TestCase):
    def test_finds_rows_regardless_of_table_column_width(self) -> None:
        text = (
            "| ID  | Task | Complexity | Depends on |\n"
            "|---|---|---|---|\n"
            "| T1 | first task | S | |\n"
            "| T2                | second task, wide column | M | T1 |\n"
        )
        rows = gv.parse_task_rows(text)
        self.assertEqual([r.task_id for r in rows], ["T1", "T2"])


class TestDuplicateTaskIds(unittest.TestCase):
    def test_no_duplicates_is_clean(self) -> None:
        rows = [gv.TaskRow("T1", 1, "| T1 | a |"), gv.TaskRow("T2", 2, "| T2 | b |")]
        self.assertEqual(gv.check_duplicate_task_ids(rows), [])

    def test_duplicate_task_id_is_flagged(self) -> None:
        rows = [
            gv.TaskRow("T5", 10, "| T5 | first definition |"),
            gv.TaskRow("T5", 40, "| T5 | accidentally redefined |"),
        ]
        violations = gv.check_duplicate_task_ids(rows)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].check, "duplicate-task-id")
        self.assertIn("T5", violations[0].message)


class TestDoneRequiresAuthorization(unittest.TestCase):
    def test_done_with_authorization_phrase_is_clean(self) -> None:
        row = gv.TaskRow(
            "T50",
            1,
            "| T50 | ... Authorized by the project owner, 2026-01-01 ... T50 is now Done -- merged. |",
        )
        self.assertEqual(gv.check_done_requires_authorization([row]), [])

    def test_done_without_authorization_phrase_is_flagged(self) -> None:
        row = gv.TaskRow("T99", 1, "| T99 | some task ... T99 is now Done -- merged. |")
        violations = gv.check_done_requires_authorization([row])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].check, "done-without-authorization")

    def test_not_yet_done_task_is_not_flagged(self) -> None:
        row = gv.TaskRow(
            "T100", 1, "| T100 | Authorized by the project owner, 2026-01-01, not implemented yet. |"
        )
        self.assertEqual(gv.check_done_requires_authorization([row]), [])

    def test_done_marker_for_a_different_task_does_not_cross_contaminate(self) -> None:
        # T94's own row narrates that T93 is now Done as historical context;
        # that must not be misread as a claim that T94 itself is Done.
        row = gv.TaskRow(
            "T94",
            1,
            "| T94 | Authorized by the project owner. Depends on T93, and T93 is now Done -- merged. |",
        )
        self.assertEqual(gv.check_done_requires_authorization([row]), [])


class TestAdrReferences(unittest.TestCase):
    def test_existing_reference_is_clean(self) -> None:
        text = "See `ADR/0021-foo.md` for details."
        self.assertEqual(gv.check_adr_references(text, existing_numbers={21}), [])

    def test_dangling_reference_is_flagged(self) -> None:
        text = "See `ADR/0099-does-not-exist.md` for details."
        violations = gv.check_adr_references(text, existing_numbers={21, 22})
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].check, "dangling-adr-reference")

    def test_same_dangling_reference_only_reported_once(self) -> None:
        text = "`ADR/0099-x.md` mentioned twice: `ADR/0099-x.md` again."
        violations = gv.check_adr_references(text, existing_numbers=set())
        self.assertEqual(len(violations), 1)


class TestAdrFileParsing(unittest.TestCase):
    def _write_adr(self, adr_dir: Path, filename: str, header_number: int, resolves_text: str) -> None:
        content = (
            f"# ADR-{header_number:04d}: Something\n\n"
            "**Status:** Proposed\n\n"
            f"**Resolves:** {resolves_text}\n\n"
            "**Does not resolve:** nothing relevant here.\n\n"
            "## Context\n\nirrelevant body text mentioning #99 which must not be parsed as a resolution.\n"
        )
        (adr_dir / filename).write_text(content, encoding="utf-8")

    def test_clean_adr_set_has_no_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            self._write_adr(adr_dir, "0001-a.md", 1, "planning-list item **#1**.")
            self._write_adr(adr_dir, "0002-b.md", 2, "planning-list item **#2**.")
            adrs, violations = gv.parse_adr_files(adr_dir)
            self.assertEqual(violations, [])
            self.assertEqual({a.resolves.pop() for a in adrs}, {1, 2})

    def test_filename_header_mismatch_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            self._write_adr(adr_dir, "0003-c.md", 4, "planning-list item **#3**.")  # header says 4, not 3
            _, violations = gv.parse_adr_files(adr_dir)
            checks = [v.check for v in violations]
            self.assertIn("adr-number-mismatch", checks)

    def test_duplicate_adr_number_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            self._write_adr(adr_dir, "0005-a.md", 5, "planning-list item **#5**.")
            self._write_adr(adr_dir, "0005-b-accidental-dup.md", 5, "planning-list item **#5**.")
            _, violations = gv.parse_adr_files(adr_dir)
            checks = [v.check for v in violations]
            self.assertIn("duplicate-adr-number", checks)

    def test_unrelated_hash_mentions_outside_resolves_block_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            self._write_adr(adr_dir, "0006-a.md", 6, "planning-list item **#6**.")
            adrs, _ = gv.parse_adr_files(adr_dir)
            self.assertEqual(adrs[0].resolves, {6})  # not {6, 99} from the body text


class TestDuplicateRequiredAdrResolution(unittest.TestCase):
    def test_no_overlap_is_clean(self) -> None:
        adrs = [
            gv.AdrFile(1, 1, Path("0001-a.md"), resolves={1}),
            gv.AdrFile(2, 2, Path("0002-b.md"), resolves={2}),
        ]
        self.assertEqual(gv.check_duplicate_required_adr_resolution(adrs), [])

    def test_two_adrs_resolving_the_same_required_adr_is_flagged(self) -> None:
        adrs = [
            gv.AdrFile(1, 1, Path("0001-a.md"), resolves={9}),
            gv.AdrFile(2, 2, Path("0002-b.md"), resolves={9}),
        ]
        violations = gv.check_duplicate_required_adr_resolution(adrs)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].check, "duplicate-required-adr-resolution")


class TestGovernanceLedger(unittest.TestCase):
    def test_matching_ledger_is_clean(self) -> None:
        state = {"governanceLedger": {"resolvedRequiredADRs": [1, 2], "unresolvedRequiredADRs": sorted(set(gv.REQUIRED_ADR_RANGE) - {1, 2})}}
        self.assertEqual(gv.check_governance_ledger(state, resolved={1, 2}), [])

    def test_stale_resolved_list_is_flagged(self) -> None:
        state = {"governanceLedger": {"resolvedRequiredADRs": [1], "unresolvedRequiredADRs": sorted(set(gv.REQUIRED_ADR_RANGE) - {1})}}
        violations = gv.check_governance_ledger(state, resolved={1, 2})  # #2 newly resolved, ledger not updated
        checks = [v.check for v in violations]
        self.assertIn("governance-ledger-drift", checks)

    def test_missing_ledger_is_not_an_error(self) -> None:
        self.assertEqual(gv.check_governance_ledger({}, resolved={1}), [])


class TestValidateAgainstRealRepository(unittest.TestCase):
    """The most important test: the actual repository, as it stands, must
    pass with zero errors. This is what "verify a clean repository passes"
    means in practice, not just synthetic fixtures."""

    def test_real_repository_passes(self) -> None:
        root = gv.find_repo_root(Path(__file__).parent)
        violations = gv.validate(root)
        errors = [v for v in violations if v.severity == "ERROR"]
        self.assertEqual(
            errors,
            [],
            f"Real repository failed governance validation: {[v.message for v in errors]}",
        )

    def test_report_mode_runs_without_error(self) -> None:
        root = gv.find_repo_root(Path(__file__).parent)
        output = gv.report(root)
        self.assertIn("Resolved:", output)
        self.assertIn("Unresolved:", output)


class TestFindRepoRoot(unittest.TestCase):
    def test_raises_when_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                gv.find_repo_root(Path(tmp))


if __name__ == "__main__":
    unittest.main()
