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

    # 9. Transition for the wrong task/ancestry (an older, superseded authorized task) -> FAIL.
    def test_transition_for_non_latest_authorized_task_fails(self) -> None:
        rows = [self._authorized_row("T5"), self._authorized_row("T41")]  # T41 is the frontier
        ledger = {
            "resolvedRequiredADRs": [1],
            "inProgressTransitions": [{"task": "T5", "requiredAdrs": [7]}],  # stale task cited
        }
        violations = gv.check_governance_ledger(
            {"governanceLedger": ledger}, resolved={1, 7}, rows=rows
        )
        self.assertIn("governance-transition-wrong-task", [v.check for v in violations])

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


if __name__ == "__main__":
    unittest.main()
