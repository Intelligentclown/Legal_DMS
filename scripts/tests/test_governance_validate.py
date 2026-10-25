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
from copy import deepcopy
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

    def test_known_limitation_narrative_mention_is_not_distinguished_from_assertion(self) -> None:
        """Documents an accepted limitation rather than silently ignoring it: this check is pure
        substring matching, so it cannot tell a genuine "this task IS authorized" assertion apart
        from a row that merely narrates/quotes the phrase while discussing a DIFFERENT task's
        history (e.g. T94's own row quotes its own prior defect using this exact phrase). A row
        that is Done and happens to contain the phrase anywhere, even in a quoting/narrative
        context, is accepted as passing here -- see docs/GOVERNANCE_VALIDATION.md's "What this
        deliberately does not validate" section. Human/AI review remains the backstop for this
        gap; it is not claimed to be mechanically closed."""
        row = gv.TaskRow(
            "T96",
            1,
            "| T96 | Historically, tasks required the phrase 'Authorized by the project owner' "
            "before being marked done; this task has not received that. T96 is now Done. |",
        )
        # Documented current behavior: passes, because the phrase is present somewhere in the
        # row, even though it does not actually assert T96's own authorization.
        self.assertEqual(gv.check_done_requires_authorization([row]), [])


class TestDoneRequiresQaEvidence(unittest.TestCase):
    def test_done_with_qa_decision_mention_is_clean(self) -> None:
        row = gv.TaskRow(
            "T50", 1, "| T50 | ... QA Decision: Approved with comments ... T50 is now Done -- merged. |"
        )
        self.assertEqual(gv.check_done_requires_qa_evidence([row]), [])

    def test_done_without_qa_decision_mention_is_flagged(self) -> None:
        row = gv.TaskRow("T99", 1, "| T99 | some task ... T99 is now Done -- merged. |")
        violations = gv.check_done_requires_qa_evidence([row])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].check, "done-without-qa-evidence")

    def test_case_insensitive_match(self) -> None:
        row = gv.TaskRow("T60", 1, "| T60 | qa decision: approved. T60 is now Done. |")
        self.assertEqual(gv.check_done_requires_qa_evidence([row]), [])


class TestLatestTaskNumber(unittest.TestCase):
    def test_returns_highest_matching_task(self) -> None:
        rows = [
            gv.TaskRow("T5", 1, "| T5 | Authorized by the project owner. |"),
            gv.TaskRow("T12", 2, "| T12 | Authorized by the project owner. |"),
            gv.TaskRow("T9", 3, "| T9 | not authorized text here |"),
        ]
        result = gv.latest_task_number(rows, lambda r: gv.AUTHORIZATION_PHRASE in r.text)
        self.assertEqual(result, "T12")  # numeric max, not lexicographic ("T9" > "T12" as strings)

    def test_returns_none_when_no_match(self) -> None:
        rows = [gv.TaskRow("T1", 1, "| T1 | nothing relevant |")]
        self.assertIsNone(gv.latest_task_number(rows, lambda r: "never matches" in r.text))


class TestGovernanceLedgerLatestTaskDrift(unittest.TestCase):
    def _rows(self) -> list[gv.TaskRow]:
        return [
            gv.TaskRow("T1", 1, "| T1 | Authorized by the project owner. T1 is now Done. QA Decision: Approved. |"),
            gv.TaskRow("T2", 2, "| T2 | Authorized by the project owner. Not yet implemented. |"),
        ]

    def test_matching_latest_fields_are_clean(self) -> None:
        state = {"governanceLedger": {"latestTaskDone": "T1", "latestTaskAuthorized": "T2"}}
        self.assertEqual(gv.check_governance_ledger(state, resolved=set(), rows=self._rows()), [])

    def test_stale_latest_task_done_is_flagged(self) -> None:
        state = {"governanceLedger": {"latestTaskDone": "T2"}}  # T2 isn't actually Done
        violations = gv.check_governance_ledger(state, resolved=set(), rows=self._rows())
        self.assertEqual(len(violations), 1)
        self.assertIn("latestTaskDone", violations[0].message)

    def test_missing_latest_fields_are_not_an_error(self) -> None:
        state = {"governanceLedger": {"resolvedRequiredADRs": [], "unresolvedRequiredADRs": list(gv.REQUIRED_ADR_RANGE)}}
        self.assertEqual(gv.check_governance_ledger(state, resolved=set(), rows=self._rows()), [])

    def test_rows_not_provided_skips_latest_task_checks(self) -> None:
        # backward-compat: callers that don't pass rows only get the resolved/unresolved check.
        state = {"governanceLedger": {"latestTaskDone": "totally wrong"}}
        self.assertEqual(gv.check_governance_ledger(state, resolved=set()), [])


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

    def test_topic_similarity_does_not_imply_resolution(self) -> None:
        """An ADR whose body extensively discusses File/Matter lifecycle concepts (Required
        ADR #8's actual subject matter) but whose Resolves field only names #9 must be recorded
        as resolving #9 only -- never inferred to also resolve #8 merely because the words
        overlap. This is the exact discipline ADR/0027 itself follows in the real repository."""
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            content = (
                "# ADR-0009: Something About File Numbering\n\n"
                "**Status:** Proposed\n\n"
                "**Resolves:** planning-list item **#9** only.\n\n"
                "**Does not resolve:** Required ADR #8 (Matter vs File lifecycle), #10, #20.\n\n"
                "## Context\n\n"
                "This ADR discusses File, Matter, lifecycle, deletion cascade, and Workflow "
                "attachment granularity extensively in its body -- the same vocabulary Required "
                "ADR #8 covers -- but never resolves #8; it explicitly defers it.\n"
            )
            (adr_dir / "0009-file-numbering.md").write_text(content, encoding="utf-8")
            adrs, violations = gv.parse_adr_files(adr_dir)
            self.assertEqual(violations, [])
            self.assertEqual(adrs[0].resolves, {9})  # not {8, 9, 10, 20}

    def test_non_numbered_files_are_skipped_not_flagged(self) -> None:
        """ADR/template.md (a real file in this repository) has no leading NNNN- filename
        number and must be silently skipped, not treated as a malformed/mismatched ADR."""
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            (adr_dir / "template.md").write_text("# ADR-XXXX: Template\n\nFill this in.\n", encoding="utf-8")
            self._write_adr(adr_dir, "0001-a.md", 1, "planning-list item **#1**.")
            adrs, violations = gv.parse_adr_files(adr_dir)
            self.assertEqual(violations, [])
            self.assertEqual(len(adrs), 1)  # template.md did not become a phantom ADR


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

    def test_ledger_declaring_only_one_of_the_pair_is_not_flagged_for_the_other(self) -> None:
        """Regression test: a governanceLedger that declares only resolvedRequiredADRs (e.g. it
        predates unresolvedRequiredADRs being added, or simply doesn't track it) must not be
        flagged as if it had declared an empty unresolvedRequiredADRs list -- found and fixed
        during the T95 hardening pass, where the original implementation used dict.get(key, [])
        and so silently treated "field absent" the same as "field declared empty"."""
        state = {"governanceLedger": {"resolvedRequiredADRs": [1, 2]}}
        self.assertEqual(gv.check_governance_ledger(state, resolved={1, 2}), [])


class TestInProgressTransition(unittest.TestCase):
    """T99: an optional governanceLedger.inProgressTransitions declaration that lets a
    genuinely authorized, currently-in-progress Required-ADR resolution pass this gate
    during the deliberate window before its own Governance Closeout PR syncs the ledger.
    No task ID, ADR number, or PR number is hard-coded anywhere in the mechanism under
    test -- every fixture below uses arbitrary numbers to make that concrete, not just
    asserted in prose."""

    def _authorized_row(self, task: str, *, done: bool = False) -> gv.TaskRow:
        text = f"| {task} | Some governance-hardening task. Authorized by the project owner, 2026-01-01."
        if done:
            text += f" {task} is now Done -- merged. QA Decision: Approved."
        text += " |"
        return gv.TaskRow(task, 1, text)

    def _unauthorized_row(self, task: str) -> gv.TaskRow:
        return gv.TaskRow(task, 1, f"| {task} | Not yet authorized, no project-owner phrase here. |")

    # 1. Valid authorized in-progress transition -> PASS.
    def test_valid_in_progress_transition_passes(self) -> None:
        rows = [self._authorized_row("T41")]  # arbitrary task ID, not T98/T99
        ledger = {
            "resolvedRequiredADRs": [1, 2],
            "unresolvedRequiredADRs": sorted(set(gv.REQUIRED_ADR_RANGE) - {1, 2, 7}),
            "latestTaskAuthorized": "T41",
            "inProgressTransitions": [{"task": "T41", "requiredAdrs": [7]}],
        }
        state = {"governanceLedger": ledger}
        # ADR files themselves now resolve {1, 2, 7} -- #7 is the in-progress addition.
        violations = gv.check_governance_ledger(state, resolved={1, 2, 7}, rows=rows)
        self.assertEqual(violations, [])

    # 2. Valid settled state -> PASS (no declaration at all -- pre-T99 behavior, unchanged).
    def test_valid_settled_state_with_no_declaration_passes(self) -> None:
        rows = [self._authorized_row("T41", done=True)]
        ledger = {
            "resolvedRequiredADRs": [1, 2, 7],
            "unresolvedRequiredADRs": sorted(set(gv.REQUIRED_ADR_RANGE) - {1, 2, 7}),
            "latestTaskDone": "T41",
            "latestTaskAuthorized": "T41",
        }
        state = {"governanceLedger": ledger}
        violations = gv.check_governance_ledger(state, resolved={1, 2, 7}, rows=rows)
        self.assertEqual(violations, [])

    # 3. Ordinary latestTaskAuthorized drift (no transition declared at all) -> FAIL.
    def test_ordinary_drift_without_any_declaration_still_fails(self) -> None:
        rows = [self._authorized_row("T41")]
        state = {"governanceLedger": {"latestTaskAuthorized": "T5"}}  # stale, no declaration
        violations = gv.check_governance_ledger(state, resolved=set(), rows=rows)
        checks = [v.check for v in violations]
        self.assertIn("governance-ledger-drift", checks)

    # 4. Unauthorized transition (declared task has no authorized row at all) -> FAIL.
    def test_unauthorized_transition_fails(self) -> None:
        rows = [self._unauthorized_row("T41")]
        ledger = {
            "resolvedRequiredADRs": [],
            "inProgressTransitions": [{"task": "T41", "requiredAdrs": [7]}],
        }
        violations = gv.check_governance_ledger({"governanceLedger": ledger}, resolved={7}, rows=rows)
        checks = [v.check for v in violations]
        self.assertIn("governance-transition-unauthorized", checks)
        # No exemption granted -- the underlying drift also still reports.
        self.assertIn("governance-ledger-drift", checks)

    # 5. Stale/invalid transition declaration (wrong shape) -> FAIL.
    def test_malformed_transition_declaration_fails(self) -> None:
        rows = [self._authorized_row("T41")]
        for bad_entry in (
            {"task": "T41"},  # missing requiredAdrs
            {"requiredAdrs": [7]},  # missing task
            {"task": "not-a-task-id", "requiredAdrs": [7]},
            {"task": "T41", "requiredAdrs": []},  # empty list
            {"task": "T41", "requiredAdrs": ["7"]},  # wrong element type
            {"task": "T41", "requiredAdrs": [7.5]},  # not an int
        ):
            with self.subTest(bad_entry=bad_entry):
                ledger = {"inProgressTransitions": [bad_entry]}
                violations = gv.check_governance_ledger(
                    {"governanceLedger": ledger}, resolved={7}, rows=rows
                )
                self.assertIn("governance-transition-malformed", [v.check for v in violations])

    # 6. Invalid Required-ADR state (out-of-range number) -> FAIL.
    def test_out_of_range_required_adr_fails(self) -> None:
        rows = [self._authorized_row("T41")]
        ledger = {"inProgressTransitions": [{"task": "T41", "requiredAdrs": [999]}]}
        violations = gv.check_governance_ledger({"governanceLedger": ledger}, resolved=set(), rows=rows)
        self.assertIn("governance-transition-invalid-adr-state", [v.check for v in violations])

    # 7. Missing transition evidence (declared ADR isn't actually resolved by any ADR file) -> FAIL.
    def test_missing_evidence_fails(self) -> None:
        rows = [self._authorized_row("T41")]
        ledger = {
            "resolvedRequiredADRs": [1],
            "inProgressTransitions": [{"task": "T41", "requiredAdrs": [7]}],
        }
        # #7 is claimed in-progress, but no ADR file anywhere actually resolves it --
        # the ADR-derived `resolved` set below proves it (only {1}, same as recorded).
        violations = gv.check_governance_ledger({"governanceLedger": ledger}, resolved={1}, rows=rows)
        self.assertIn("governance-transition-scope-mismatch", [v.check for v in violations])

    # 8. Ambiguous/multiple transition declarations -> FAIL safely (no partial exemption).
    def test_multiple_simultaneous_transitions_fail_safely(self) -> None:
        rows = [self._authorized_row("T41")]
        ledger = {
            "resolvedRequiredADRs": [1],
            "inProgressTransitions": [
                {"task": "T41", "requiredAdrs": [7]},
                {"task": "T41", "requiredAdrs": [8]},
            ],
        }
        violations = gv.check_governance_ledger(
            {"governanceLedger": ledger}, resolved={1, 7, 8}, rows=rows
        )
        checks = [v.check for v in violations]
        self.assertIn("governance-transition-ambiguous", checks)
        # Fail-safe: the real, unexplained drift is still reported, not silently excused.
        self.assertIn("governance-ledger-drift", checks)

    # 9 (T100): a transition for a non-frontier task that is still authorized and not
    # yet Done now PASSES. T99's original mechanism required the declared task to
    # equal the single, numerically-highest authorized task ("the frontier"), which
    # wrongly rejected exactly this legitimate case in practice: T99 was authorized
    # after T98, then fully implemented and closed out (becoming both the new
    # frontier and "already Done") before T98's own PR could merge, leaving T98 -- an
    # authorized, still-open task -- unable to satisfy either the old frontier check
    # (T98 is no longer the frontier once T99 is authorized) or the already-settled
    # check (T98 itself was never Done). T100 removes the frontier-equality
    # constraint; being authorized and not-yet-Done is sufficient on its own.
    def test_transition_for_non_frontier_but_still_open_authorized_task_now_passes(self) -> None:
        rows = [self._authorized_row("T5"), self._authorized_row("T41")]  # T41 is the frontier
        ledger = {
            "resolvedRequiredADRs": [1],
            "unresolvedRequiredADRs": sorted(set(gv.REQUIRED_ADR_RANGE) - {1, 7}),
            # T5 is authorized and still open, but is NOT the frontier (T41 is).
            "inProgressTransitions": [{"task": "T5", "requiredAdrs": [7]}],
        }
        violations = gv.check_governance_ledger(
            {"governanceLedger": ledger}, resolved={1, 7}, rows=rows
        )
        self.assertEqual(violations, [])

    def test_wrong_task_check_no_longer_exists(self) -> None:
        """T100 removed the frontier-equality constraint entirely, not merely widened
        it -- documents that governance-transition-wrong-task can no longer occur,
        checked structurally (source inspection), not just by absence of a failing
        test case."""
        import inspect

        source = inspect.getsource(gv.validate_in_progress_transition)
        self.assertNotIn("governance-transition-wrong-task", source)

    def test_the_actual_t98_t99_race_scenario_reproduced_and_fixed(self) -> None:
        """The exact real-world shape T100 exists to fix, using the real task IDs and
        ADR number involved -- not to hard-code them into the mechanism (the tests
        above already prove genericity with arbitrary IDs), but to demonstrate this
        specific, previously-failing case is now resolved."""
        rows = [
            self._authorized_row("T98"),  # authorized, implemented, QA-approved, NOT Done
            self._authorized_row("T99", done=True),  # authorized after T98, closed out first
        ]
        ledger = {
            "resolvedRequiredADRs": [1, 2, 3, 4, 5, 6, 7, 9, 13, 18, 19],
            "unresolvedRequiredADRs": [8, 10, 11, 12, 15, 16, 17, 20],  # #14 excluded: in-progress
            "latestTaskDone": "T99",
            "latestTaskAuthorized": "T99",
            "inProgressTransitions": [{"task": "T98", "requiredAdrs": [14]}],
        }
        resolved = {1, 2, 3, 4, 5, 6, 7, 9, 13, 14, 18, 19}  # ADR-0029 now resolves #14 too
        violations = gv.check_governance_ledger({"governanceLedger": ledger}, resolved=resolved, rows=rows)
        self.assertEqual(violations, [])

    # 9b. A transition declared for a task that has already reached Done -> FAIL
    # (the "already settled" case -- Closeout should have removed the declaration).
    def test_transition_for_already_done_task_fails(self) -> None:
        rows = [self._authorized_row("T41", done=True)]
        ledger = {
            "resolvedRequiredADRs": [1],
            "inProgressTransitions": [{"task": "T41", "requiredAdrs": [7]}],
        }
        violations = gv.check_governance_ledger(
            {"governanceLedger": ledger}, resolved={1, 7}, rows=rows
        )
        self.assertIn("governance-transition-already-settled", [v.check for v in violations])

    # 10. No hard-coded T98/T99/ADR-0029 exception exists -- the mechanism works
    # identically for arbitrary task IDs and ADR numbers never seen elsewhere in this
    # module or its tests, proving nothing is keyed to a literal.
    def test_mechanism_is_generalized_not_hard_coded_to_any_specific_task_or_adr(self) -> None:
        rows = [self._authorized_row("T777")]
        ledger = {
            "resolvedRequiredADRs": [3],
            "unresolvedRequiredADRs": sorted(set(gv.REQUIRED_ADR_RANGE) - {3, 19}),
            "latestTaskAuthorized": "T777",
            "inProgressTransitions": [{"task": "T777", "requiredAdrs": [19]}],
        }
        violations = gv.check_governance_ledger(
            {"governanceLedger": ledger}, resolved={3, 19}, rows=rows
        )
        self.assertEqual(violations, [])
        # And the source module itself contains no literal reference to T98, T99, or
        # ADR-0029 anywhere in the transition-validation function -- a structural,
        # not merely behavioral, proof that no such exception was hard-coded.
        import inspect

        source = inspect.getsource(gv.validate_in_progress_transition)
        for literal in ("T98", "T99", "0029", "ADR-0029"):
            self.assertNotIn(literal, source)

    # 11. Existing governance validation behavior remains intact once the transition
    # completes -- strict settled-state comparison resumes with zero tolerance, even
    # though the same task was, until Closeout, legitimately exempted.
    def test_settled_state_after_transition_completes_is_strict_again(self) -> None:
        rows = [self._authorized_row("T41", done=True)]  # Closeout has happened
        # Ledger fully synced, no lingering declaration -- exactly Closeout's job.
        ledger = {
            "resolvedRequiredADRs": [1, 2, 7],
            "unresolvedRequiredADRs": sorted(set(gv.REQUIRED_ADR_RANGE) - {1, 2, 7}),
            "latestTaskDone": "T41",
            "latestTaskAuthorized": "T41",
        }
        violations = gv.check_governance_ledger({"governanceLedger": ledger}, resolved={1, 2, 7}, rows=rows)
        self.assertEqual(violations, [])

        # But if Closeout forgot to sync (stale resolved set persists post-Done), that
        # must still fail -- Done tasks get zero leniency, regardless of any transition
        # ever having existed for them.
        stale_ledger = dict(ledger, resolvedRequiredADRs=[1, 2])
        violations = gv.check_governance_ledger(
            {"governanceLedger": stale_ledger}, resolved={1, 2, 7}, rows=rows
        )
        self.assertIn("governance-ledger-drift", [v.check for v in violations])

    def test_absent_declaration_grants_no_exemption_object(self) -> None:
        violations, exemption = gv.validate_in_progress_transition(
            ledger={}, resolved={1}, recorded_resolved=set(), rows=[]
        )
        self.assertEqual(violations, [])
        self.assertIsNone(exemption)

    def test_non_list_declaration_is_malformed(self) -> None:
        violations, exemption = gv.validate_in_progress_transition(
            ledger={"inProgressTransitions": {"task": "T1", "requiredAdrs": [1]}},
            resolved={1},
            recorded_resolved=set(),
            rows=[self._authorized_row("T1")],
        )
        self.assertIn("governance-transition-malformed", [v.check for v in violations])
        self.assertIsNone(exemption)


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


class TestT156Calendar(unittest.TestCase):
    def setUp(self):
        from delivery_calendar import check_calendar, forecast
        self.check=check_calendar
        self.forecast=forecast
        self.data={"schema_version":1,"activation_task_number":157,"milestones":[
            {"id":k,"baseline":"2026-12-31","forecast":"2026-12-31","actual":None,
             "confidence":"low","risk":"planning","last_recalculated":"2026-10-17"} for k in ("M1","M2","M3")],
            "lanes":[{"id":"core"}],"history":[],"tasks":[]}
        self.row=gv.TaskRow("T157",1,"| T157 | Authorized by the project owner | Authorized | T156 |")
        self.task={"id":"T157","title":"synthetic","milestone":"M3","lane":"core",
            "dependencies":[],"critical_path":{"is_critical":False,"slack_days":5},
            "planned_start":"2026-10-20","planned_finish":"2026-10-22","planned_duration":3,
            "forecast_start":"2026-10-20","forecast_finish":"2026-10-22","forecast_impact":{}}
        self.data["tasks"]=[self.task]
    def errors(self,rows=None):
        return self.check(self.data,[self.row] if rows is None else rows)
    def test_valid(self): self.assertEqual(self.errors(),[])
    def test_missing_fields(self):
        for key in ("planned_start","planned_finish","planned_duration","milestone","lane","dependencies","critical_path"):
            with self.subTest(key=key):
                t=self.task.copy(); t.pop(key); self.data["tasks"]=[t]
                self.assertTrue(self.errors())
        self.data["tasks"]=[self.task]
    def test_bad_date_and_duration(self):
        for key,value in (("planned_start","2026-13-01"),("planned_duration",4)):
            with self.subTest(key=key):
                t=self.task.copy();t[key]=value;self.data["tasks"]=[t]
                self.assertTrue(self.errors())
    def test_historical_exempt_and_t157_missing(self):
        self.assertEqual(self.errors([gv.TaskRow("T155",1,"| T155 | Done |")]),["T157: calendar entry not in queue"])
        self.data["tasks"]=[]
        self.assertEqual(self.errors([gv.TaskRow("T155",1,"| T155 | Done |")]),[])
        self.assertTrue(self.errors())
    def test_completion_variance(self):
        done=gv.TaskRow("T157",1,"| T157 | synthetic | Done | T156 |")
        t=self.task
        t.update(actual_start="2026-10-20",actual_completion="2026-10-21",actual_elapsed=2,
                 planned_finish_used="2026-10-22",variance=-1,classification="Early",
                 critical_at_completion=False,milestone_impact=0,finalization_impact=0,
                 recalculated="2026-10-22")
        self.assertEqual(self.errors([done]),[])
        for actual,variance,label in (("2026-10-22",0,"On Time"),("2026-10-24",2,"Late")):
            t.update(actual_completion=actual,actual_elapsed=(gv_date(actual)-gv_date("2026-10-20")).days+1,
                     variance=variance,classification=label)
            self.assertEqual(self.errors([done]),[])
        for field in ("actual_start","actual_completion","actual_elapsed","variance","classification"):
            x=t.copy();x.pop(field);self.data["tasks"]=[x]
            self.assertTrue(self.errors([done]))
        self.data["tasks"]=[t]
        for actual,variance,label in (("2026-10-21",-1,"Late"),("2026-10-22",0,"Early"),("2026-10-24",2,"On Time")):
            t.update(actual_completion=actual,actual_elapsed=(gv_date(actual)-gv_date("2026-10-20")).days+1,
                     variance=variance,classification=label)
            self.assertTrue(self.errors([done]))
    def test_history_required_and_reconciled(self):
        self.data["milestones"][2]["forecast"]="2027-01-01"
        self.assertTrue(self.errors())
        self.data["history"]=[{"milestone":"M3","old":"2026-12-31","new":"2027-01-01",
            "movement":1,"direction":"later","reason":"critical predecessor delay",
            "trigger":"T157","recalculated":"2026-10-24"}]
        self.assertEqual(self.errors(),[])
        self.data["history"][0]["reason"]=""
        self.assertTrue(self.errors())
    def test_slack_critical_and_acceleration(self):
        from delivery_calendar import forecast
        base="2026-10-22"
        a=dict(self.task,id="T157",planned_duration=3,forecast_start="2026-10-20",actual_completion="2026-10-21")
        b=dict(self.task,id="T158",planned_duration=2,forecast_start="2026-10-23",dependencies=[])
        # Early noncritical task cannot pull another lane's finish forward.
        self.assertEqual(forecast([a,b],"M3",base),"2026-10-24")
        a["actual_completion"]="2026-10-23"
        self.assertEqual(forecast([a,b],"M3",base),"2026-10-24")
        b["dependencies"]=["T157"]
        self.assertEqual(forecast([a,b],"M3",base),"2026-10-25")
        a["actual_completion"]="2026-10-19"
        b["forecast_start"]="2026-10-20"
        self.assertEqual(forecast([a,b],"M3","2026-10-20"),"2026-10-21")


    def test_status_cell_isolated_from_description_and_predecessor(self):
        """Only the real four-column Status cell controls Done validation."""
        for row_text in (
            "| T157 | Description says Done already | Authorized | T156 |",
            "| T157 | ordinary work | Authorized | T156 Done context |",
        ):
            with self.subTest(row=row_text):
                self.assertEqual(self.errors([gv.TaskRow("T157", 1, row_text)]), [])
        self.assertTrue(self.errors([
            gv.TaskRow("T157", 1, "| T157 | Description says Authorized | Done | T156 |")
        ]))
        self.assertTrue(self.errors([
            gv.TaskRow("T157", 1, "| T157 | malformed | Done |")
        ]))
        self.assertTrue(self.errors([
            gv.TaskRow("T157", 1, "| T157 | malformed | Done | T156 | extra |")
        ]))

    def test_real_four_column_done_requires_each_completion_field(self):
        row = gv.TaskRow("T157", 1, "| T157 | completed task | Done | T156 |")
        required = ("actual_start", "actual_completion", "actual_elapsed", "variance", "classification")
        complete = dict(self.task, actual_start="2026-10-20",
                        actual_completion="2026-10-22", actual_elapsed=3,
                        planned_finish_used="2026-10-22", variance=0,
                        classification="On Time", critical_at_completion=False,
                        milestone_impact=0, finalization_impact=0,
                        recalculated="2026-10-22")
        for field in required:
            with self.subTest(missing=field):
                incomplete = complete.copy()
                incomplete.pop(field)
                self.data["tasks"] = [incomplete]
                self.assertTrue(any("Done missing " + field in e for e in self.errors([row])))
        for field in required:
            with self.subTest(invalid=field):
                invalid = complete.copy()
                invalid[field] = {
                    "actual_start": "not-a-date", "actual_completion": "not-a-date",
                    "actual_elapsed": 9, "variance": 9, "classification": "Late"
                }[field]
                self.data["tasks"] = [invalid]
                self.assertTrue(self.errors([row]))
        self.data["tasks"] = [complete]
        self.assertEqual(self.errors([row]), [])

class TestProtectedMergeCalendarV2(unittest.TestCase):
    def setUp(self):
        from delivery_calendar import PROJECT_TIMEZONE, check_calendar
        self.check = check_calendar
        self.row = gv.TaskRow("T157", 1, "| T157 | Authorized by the project owner; T157 is now Done | Done | T156 |")
        self.data = {
            "schema_version": 2, "activation_task_number": 157, "project_timezone": PROJECT_TIMEZONE,
            "milestones": [{"id": key, "baseline": "2026-10-31", "forecast": "2026-10-31",
                            "actual": None, "confidence": "low", "risk": "test",
                            "last_recalculated": "2026-10-18"} for key in ("M1", "M2", "M3")],
            "lanes": [{"id": "core"}], "history": [],
            "tasks": [{
                "id": "T157", "title": "synthetic", "milestone": "M1", "lane": "core",
                "dependencies": {"finish_to_start": [], "defect_evidence": []},
                "critical_path": {"is_critical": True, "slack_days": 0},
                "planned_start": "2026-10-18", "planned_finish": "2026-10-20",
                "planned_duration": 3, "forecast_start": "2026-10-18",
                "forecast_finish": "2026-10-20", "forecast_impact": {},
                "actual_start": "2026-10-18", "actual_completion": "2026-10-19",
                "actual_elapsed": 2, "planned_finish_used": "2026-10-20",
                "variance": -1, "classification": "Early", "critical_at_completion": True,
                "milestone_impact": 0, "finalization_impact": 0, "recalculated": "2026-10-19",
                "completion_evidence": {
                    "implementation_pr": 1, "protected_merge_sha": "a" * 40,
                    "protected_merge_parents": ["b" * 40, "c" * 40],
                    "merged_at_utc": "2026-10-18T18:31:00Z", "timezone": PROJECT_TIMEZONE,
                    "approved_qa_publication_head": "d" * 40,
                    "actual_start_evidence": "PR opened 2026-10-18"
                }
            }]
        }

    def errors(self, rows=None):
        return self.check(self.data, [self.row] if rows is None else rows)

    def test_valid_protected_completion_and_utc_boundary(self):
        self.assertEqual(self.errors(), [])

    def test_rejects_missing_or_mismatched_protected_merge_provenance(self):
        for key, value in (
            ("protected_merge_sha", "not-a-sha"),
            ("protected_merge_parents", ["b" * 40]),
            ("merged_at_utc", "2026-10-18T18:31:00+00:00"),
            ("timezone", "UTC"),
        ):
            with self.subTest(key=key):
                copy = deepcopy(self.data)
                copy["tasks"][0]["completion_evidence"][key] = value
                self.assertTrue(self.check(copy, [self.row]))

    def test_rejects_premature_done_data_on_authorized_task(self):
        authorized = gv.TaskRow("T157", 1, "| T157 | Authorized by the project owner | Authorized | T156 |")
        self.assertTrue(any("premature completion" in error for error in self.errors([authorized])))

    def test_t157_hold_preserves_authorized_null_completion_state(self):
        task = self.data["tasks"][0]
        for key in ("actual_start", "actual_completion", "actual_elapsed", "planned_finish_used",
                    "variance", "classification", "critical_at_completion", "milestone_impact",
                    "finalization_impact", "recalculated", "completion_evidence"):
            task.pop(key)
        held = gv.TaskRow("T157", 1, "| T157 | Authorized by the project owner; frozen PR #296 | Authorized | T156 |")
        self.assertEqual(self.errors([held]), [])

    def test_evidence_edges_do_not_schedule_but_true_cycles_fail(self):
        self.data["tasks"][0]["dependencies"]["defect_evidence"] = ["T158"]
        second = deepcopy(self.data["tasks"][0])
        second.update(id="T158", actual_start=None, actual_completion=None, actual_elapsed=None,
                      planned_finish_used=None, variance=None, classification=None,
                      critical_at_completion=None, milestone_impact=None,
                      finalization_impact=None, recalculated=None)
        second.pop("completion_evidence")
        second["dependencies"] = {"finish_to_start": [], "defect_evidence": ["T157"]}
        self.data["tasks"].append(second)
        rows = [self.row, gv.TaskRow("T158", 2, "| T158 | Authorized by the project owner | Authorized | T157 |")]
        self.assertEqual(self.errors(rows), [])
        second["dependencies"]["finish_to_start"] = ["T157"]
        self.data["tasks"][0]["dependencies"]["finish_to_start"] = ["T158"]
        self.assertTrue(any("dependency cycle" in error for error in self.errors(rows)))

    def test_duplicate_history_trigger_is_rejected(self):
        self.data["history"] = [
            {"milestone": "M1", "old": "2026-10-31", "new": "2026-10-31", "movement": 0,
             "direction": "unchanged", "reason": "one", "trigger": "merge", "trigger_key": "event"},
            {"milestone": "M2", "old": "2026-10-31", "new": "2026-10-31", "movement": 0,
             "direction": "unchanged", "reason": "two", "trigger": "merge", "trigger_key": "event"},
        ]
        self.assertTrue(any("duplicate immutable" in error for error in self.errors()))

    def test_snapshot_completion_tuple_must_match_calendar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "delivery_calendar.json").write_text(json.dumps(self.data), encoding="utf-8")
            state = {"governanceLedger": {"completionProvenance": {"T157": {
                "implementationPr": 1, "protectedMergeSha": "f" * 40,
                "protectedMergeParents": ["b" * 40, "c" * 40],
                "mergedAtUtc": "2026-10-18T18:31:00Z", "timezone": "Asia/Kolkata"
            }}}}
            violations = gv.check_calendar_completion_provenance(state, root, [self.row])
            self.assertEqual([v.check for v in violations], ["completion-provenance-snapshot-drift"])

    def test_pending_closeout_reports_without_fabricating_actuals(self):
        from delivery_calendar import pending_closeout_alerts
        task = self.data["tasks"][0]
        for key in ("actual_start", "actual_completion", "actual_elapsed", "planned_finish_used",
                    "variance", "classification", "critical_at_completion", "milestone_impact",
                    "finalization_impact", "recalculated"):
            task.pop(key)
        task.pop("completion_evidence")
        task["protected_merge_pending_closeout"] = {"protected_merge_sha": "a" * 40}
        authorized = gv.TaskRow("T157", 1, "| T157 | Authorized by the project owner | Authorized | T156 |")
        self.assertEqual(self.errors([authorized]), [])
        self.assertEqual(len(pending_closeout_alerts(self.data, [authorized])), 1)


class TestMilestoneCompletionProvenanceV3(unittest.TestCase):
    def setUp(self):
        from delivery_calendar import PROJECT_TIMEZONE, check_calendar
        self.check = check_calendar
        self.row = gv.TaskRow("T157", 1, "| T157 | Authorized by the project owner | Authorized | T156 |")
        self.data = {"schema_version": 3, "activation_task_number": 157, "project_timezone": PROJECT_TIMEZONE,
            "milestones": [{"id": key, "baseline": "2026-10-31", "forecast": "2026-10-31", "actual": None,
                            "confidence": "low", "risk": "test", "last_recalculated": "2026-10-18"} for key in ("M1", "M2", "M3")],
            "lanes": [{"id": "core"}], "history": [], "tasks": [{
                "id": "T157", "title": "synthetic", "milestone": "M1", "lane": "core",
                "dependencies": {"finish_to_start": [], "defect_evidence": []}, "critical_path": {"is_critical": False, "slack_days": 1},
                "planned_start": "2026-10-18", "planned_finish": "2026-10-20", "planned_duration": 3,
                "forecast_start": "2026-10-18", "forecast_finish": "2026-10-20", "forecast_impact": {}}]}
    def provenance(self):
        return {"accepted_at_utc": "2026-10-18T18:31:00Z", "acceptance_scope": "internal_office_dogfooding",
            "acceptance_reference": "Issue #1 Project Owner acceptance", "evidence_references": ["docs/acceptance/M1.md", "PR #1"],
            "evidence_sha256": "a" * 64, "baseline_at_completion": "2026-10-31", "forecast_at_completion": "2026-10-31",
            "actual_completion": "2026-10-19", "variance_days": -12, "variance_classification": "Early", "confidence_at_completion": "low"}
    def completed(self):
        data = deepcopy(self.data)
        data["milestones"][0].update(actual="2026-10-19", completion_provenance=self.provenance())
        return data
    def test_v3_valid_completion_and_null_milestones_are_supported(self):
        self.assertEqual(self.check(self.completed(), [self.row]), [])
    def test_v2_record_remains_valid_without_v3_milestone_provenance(self):
        legacy = deepcopy(self.data); legacy["schema_version"] = 2
        self.assertEqual(self.check(legacy, [self.row]), [])
    def test_rejects_missing_malformed_or_unsupported_provenance(self):
        for key, value in (("completion_provenance", None), ("acceptance_scope", "production_like"),
                           ("evidence_sha256", "not-a-digest"), ("evidence_references", ["same", "same"])):
            with self.subTest(key=key):
                data = self.completed()
                if key == "completion_provenance": data["milestones"][0][key] = value
                else: data["milestones"][0]["completion_provenance"][key] = value
                self.assertTrue(self.check(data, [self.row]))
    def test_rejects_contradictory_snapshot_variance_and_confidence(self):
        for key, value in (("forecast_at_completion", "2026-10-30"), ("actual_completion", "2026-10-18"),
                           ("variance_days", 0), ("variance_classification", "On Time"), ("confidence_at_completion", "high")):
            with self.subTest(key=key):
                data = self.completed(); data["milestones"][0]["completion_provenance"][key] = value
                self.assertTrue(self.check(data, [self.row]))
    def test_null_actual_cannot_smuggle_completion_provenance(self):
        data = deepcopy(self.data); data["milestones"][0]["completion_provenance"] = self.provenance()
        self.assertTrue(self.check(data, [self.row]))


class TestT180M1CompletionReconciliation(unittest.TestCase):
    """Regression coverage for the owner-authorized M1 reconciliation only."""

    def setUp(self):
        from delivery_calendar import check_calendar

        self.check = check_calendar
        self.root = Path(__file__).resolve().parents[2]
        self.data = json.loads(
            (self.root / "docs" / "delivery_calendar.json").read_text(encoding="utf-8")
        )
        self.rows = gv.parse_task_rows(
            (self.root / "IMPLEMENTATION_QUEUE.md").read_text(encoding="utf-8")
        )

    def m1(self, data):
        return next(milestone for milestone in data["milestones"] if milestone["id"] == "M1")

    def test_authoritative_m1_package_is_valid_and_digest_is_reproducible(self):
        m1 = self.m1(self.data)
        provenance = m1["completion_provenance"]
        package = {
            key: provenance[key]
            for key in (
                "accepted_at_utc",
                "acceptance_reference",
                "acceptance_scope",
                "evidence_references",
            )
        }
        import hashlib

        serialized = json.dumps(package, sort_keys=True, separators=(",", ":")) + "\n"
        self.assertEqual(
            hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            provenance["evidence_sha256"],
        )
        self.assertEqual(m1["actual"], "2026-10-25")
        self.assertEqual(provenance["acceptance_scope"], "internal_office_dogfooding")
        self.assertEqual(self.check(self.data, self.rows), [])

    def test_rejects_missing_or_malformed_m1_evidence(self):
        for key, value in (("evidence_references", []), ("evidence_sha256", "bad")):
            with self.subTest(key=key):
                data = deepcopy(self.data)
                self.m1(data)["completion_provenance"][key] = value
                self.assertTrue(self.check(data, self.rows))

    def test_rejects_utc_local_scope_variance_and_snapshot_contradictions(self):
        cases = (
            ("accepted_at_utc", "2026-10-24T17:00:00Z"),
            ("acceptance_scope", "production_like"),
            ("variance_days", -20),
            ("variance_classification", "On Time"),
            ("baseline_at_completion", "2026-11-14"),
            ("forecast_at_completion", "2026-11-14"),
            ("confidence_at_completion", "high"),
        )
        for key, value in cases:
            with self.subTest(key=key):
                data = deepcopy(self.data)
                self.m1(data)["completion_provenance"][key] = value
                self.assertTrue(self.check(data, self.rows))

    def test_m2_and_m3_are_unchanged(self):
        milestones = {milestone["id"]: milestone for milestone in self.data["milestones"]}
        self.assertEqual(
            (
                milestones["M2"]["baseline"],
                milestones["M2"]["forecast"],
                milestones["M2"]["actual"],
            ),
            ("2026-12-31", "2026-12-31", None),
        )
        self.assertEqual(
            (
                milestones["M3"]["baseline"],
                milestones["M3"]["forecast"],
                milestones["M3"]["actual"],
            ),
            ("2027-02-28", "2027-02-28", None),
        )


class TestCancelledTaskGovernance(unittest.TestCase):
    def setUp(self):
        from delivery_calendar import PROJECT_TIMEZONE, check_calendar
        self.check = check_calendar
        self.row = gv.TaskRow("T157", 1, "| T157 | Authorized by the project owner; T157 is Cancelled | Cancelled | T156 |")
        self.data = {
            "schema_version": 2, "activation_task_number": 157, "project_timezone": PROJECT_TIMEZONE,
            "milestones": [{"id": key, "baseline": "2026-10-31", "forecast": "2026-10-31",
                            "actual": None, "confidence": "low", "risk": "test",
                            "last_recalculated": "2026-10-20"} for key in ("M1", "M2", "M3")],
            "lanes": [{"id": "core"}], "history": [], "tasks": [{
                "id": "T157", "title": "synthetic", "milestone": "M1", "lane": "core",
                "dependencies": {"finish_to_start": [], "defect_evidence": []},
                "critical_path": {"is_critical": False, "slack_days": 1},
                "planned_start": "2026-10-20", "planned_finish": "2026-10-22",
                "planned_duration": 3, "forecast_start": "2026-10-20",
                "forecast_finish": "2026-10-22", "forecast_impact": {},
                "cancellation_evidence": {
                    "cancelled_task_id": "T157", "owner_approval_provenance": "Issue #1 owner approval",
                    "cancellation_date": "2026-10-20", "reason": "Superseded scope",
                    "evidence_reference": "governance record #1"
                }
            }]
        }

    def errors(self, rows=None):
        return self.check(self.data, [self.row] if rows is None else rows)

    def test_valid_cancelled_state_requires_no_completion_actuals(self):
        self.assertEqual(self.errors(), [])

    def test_missing_or_invalid_cancellation_evidence_is_rejected(self):
        for key, value in (("owner_approval_provenance", None), ("cancellation_date", "not-a-date"),
                           ("cancelled_task_id", "T158"), ("reason", ""), ("evidence_reference", "")):
            with self.subTest(key=key):
                data = deepcopy(self.data)
                if value is None:
                    data["tasks"][0]["cancellation_evidence"].pop(key)
                else:
                    data["tasks"][0]["cancellation_evidence"][key] = value
                self.assertTrue(self.check(data, [self.row]))

    def test_cancelled_completion_evidence_is_mutually_exclusive(self):
        data = deepcopy(self.data)
        data["tasks"][0]["actual_completion"] = "2026-10-20"
        self.assertTrue(any("contradictory completion" in error for error in self.check(data, [self.row])))

    def test_successor_provenance_is_not_authorization(self):
        data = deepcopy(self.data)
        data["tasks"][0]["cancellation_evidence"].update(
            successor_task_id="T169", successor_state="proposed_unapproved")
        self.assertEqual(self.check(data, [self.row]), [])
        data["tasks"][0]["cancellation_evidence"]["successor_state"] = "authorized"
        self.assertTrue(any("unknown successor" in error for error in self.check(data, [self.row])))

    def test_historical_proposed_successor_survives_independent_authorization_and_done(self):
        data = deepcopy(self.data)
        evidence_at_cancellation = {
            **data["tasks"][0]["cancellation_evidence"],
            "successor_task_id": "T169", "successor_state": "proposed_unapproved",
        }
        data["tasks"][0]["cancellation_evidence"] = deepcopy(evidence_at_cancellation)
        successor = deepcopy(data["tasks"][0])
        successor["id"] = "T169"
        successor.pop("cancellation_evidence")
        data["tasks"].append(successor)
        rows = [self.row, gv.TaskRow("T169", 2, "| T169 | Authorized by the project owner | Authorized | T157 |")]
        self.assertEqual(self.check(data, rows), [])
        self.assertEqual(data["tasks"][0]["cancellation_evidence"], evidence_at_cancellation)
        rows[1] = gv.TaskRow("T169", 2, "| T169 | Authorized by the project owner; T169 is now Done | Done | T157 |")
        from delivery_calendar import cancellation_evidence
        self.assertEqual(cancellation_evidence(data["tasks"][0], {row.task_id: row for row in rows}),
                         evidence_at_cancellation)
        self.assertEqual(data["tasks"][0]["cancellation_evidence"], evidence_at_cancellation)

    def test_existing_authorized_successor_is_valid_historical_provenance(self):
        data = deepcopy(self.data)
        successor = deepcopy(data["tasks"][0])
        successor["id"] = "T158"
        successor.pop("cancellation_evidence")
        data["tasks"].append(successor)
        data["tasks"][0]["cancellation_evidence"].update(
            successor_task_id="T158", successor_state="authorized")
        rows = [self.row, gv.TaskRow("T158", 2, "| T158 | Authorized by the project owner | Authorized | T157 |")]
        self.assertEqual(self.check(data, rows), [])

    def test_invalid_historical_or_current_successor_state_is_rejected(self):
        data = deepcopy(self.data)
        data["tasks"][0]["cancellation_evidence"].update(
            successor_task_id="T169", successor_state="future_state")
        self.assertTrue(any("unsupported historical" in error for error in self.check(data, [self.row])))
        data = deepcopy(self.data)
        successor = deepcopy(data["tasks"][0])
        successor["id"] = "T169"
        successor.pop("cancellation_evidence")
        data["tasks"].append(successor)
        data["tasks"][0]["cancellation_evidence"].update(
            successor_task_id="T169", successor_state="proposed_unapproved")
        rows = [self.row, gv.TaskRow("T169", 2, "| T169 | Authorized by the project owner; T169 is Cancelled | Cancelled | T157 |")]
        self.assertTrue(any("not currently independently authorized" in error for error in self.check(data, rows)))

    def test_invalid_self_or_contradictory_successor_assignments_are_rejected(self):
        data = deepcopy(self.data)
        data["tasks"][0]["cancellation_evidence"].update(
            successor_task_id="T157", successor_state="proposed_unapproved")
        self.assertTrue(any("cannot supersede itself" in error for error in self.check(data, [self.row])))
        data = deepcopy(self.data)
        data["tasks"][0]["successor_task_id"] = "T169"
        self.assertTrue(any("successor assignment belongs" in error for error in self.check(data, [self.row])))

    def test_cancelled_finish_to_start_predecessor_is_rejected(self):
        data = deepcopy(self.data)
        dependent = deepcopy(data["tasks"][0])
        dependent["id"] = "T158"
        dependent["dependencies"] = {"finish_to_start": ["T157"], "defect_evidence": []}
        dependent.pop("cancellation_evidence")
        data["tasks"].append(dependent)
        rows = [self.row, gv.TaskRow("T158", 2, "| T158 | Authorized by the project owner | Authorized | T157 |")]
        self.assertTrue(any("predecessor T157 is Cancelled" in error for error in self.check(data, rows)))


class TestQueueStateTransitions(unittest.TestCase):
    def test_authorized_done_and_cancelled_states_are_compatible(self):
        rows = [
            gv.TaskRow("T157", 1, "| T157 | Authorized by the project owner | Authorized | T156 |"),
            gv.TaskRow("T158", 2, "| T158 | Authorized by the project owner; T158 is now Done | Done | T157 |"),
            gv.TaskRow("T159", 3, "| T159 | Authorized by the project owner; T159 is Cancelled | Cancelled | T158 |"),
        ]
        self.assertEqual(gv.check_task_states(rows), [])
        state = {"governanceLedger": {"latestTaskDone": "T158", "latestTaskAuthorized": "T159"}}
        self.assertEqual(gv.check_governance_ledger(state, set(), rows), [])

    def test_cancelled_cannot_claim_done_or_skip_prior_authorization(self):
        contradictory = gv.TaskRow("T157", 1, "| T157 | Authorized by the project owner; T157 is now Done; T157 is Cancelled | Cancelled | T156 |")
        unauthorised = gv.TaskRow("T158", 2, "| T158 | T158 is Cancelled | Cancelled | T157 |")
        errors = gv.check_task_states([contradictory, unauthorised])
        self.assertTrue(any(error.check == "task-state-contradiction" for error in errors))
        self.assertTrue(any(error.check == "cancelled-without-authorization" for error in errors))


def gv_date(value):
    from datetime import date
    return date.fromisoformat(value)


if __name__ == "__main__":
    unittest.main()
