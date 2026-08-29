#!/usr/bin/env python3
"""Governance-consistency validator for Legal_DMS (T95).

Checks the repository's own governance artifacts (IMPLEMENTATION_QUEUE.md,
PROJECT_STATE.json, ADR/*.md) for objectively-checkable, text-level
inconsistencies, and fails with a clear message when it finds one.

What this validates (see docs/GOVERNANCE_VALIDATION.md for the full,
authoritative list):
  - duplicate task-ID rows in IMPLEMENTATION_QUEUE.md
  - a task row claiming "TNN is now Done" without also carrying this
    repository's established authorization phrase in the same row
  - ADR filename numbers vs. each file's own H1 header number
  - duplicate ADR filename numbers
  - two different ADR files claiming to resolve the same Required ADR #
  - dangling `ADR/NNNN` references inside IMPLEMENTATION_QUEUE.md
  - PROJECT_STATE.json's `governanceLedger` resolved/unresolved Required-ADR
    lists vs. what is dynamically computed from the ADR files themselves
  - an optional, structured `governanceLedger.inProgressTransitions` entry
    (T99) that lets a genuinely authorized, currently-in-progress
    Required-ADR resolution pass this gate during the deliberate window
    between its Architecture+QA PR merging (which adds the ADR file) and
    its own later Governance Closeout PR (which syncs the ledger) -- see
    "In-progress transition declarations" below. Absent this declaration,
    behavior is unchanged from T95.

What this deliberately does NOT validate (see docs/GOVERNANCE_VALIDATION.md
"Deliberately out of scope" section) -- most importantly, git ancestry
(whether a PR branch actually contains its authorization commit, the class
of defect found twice during T94) is NOT checked here; that remains a
Project Manager pre-merge verification responsibility this tool does not
replace.

Stdlib-only by design -- this validator must be runnable without installing
backend/ or frontend/ dependencies, so a documentation-only or governance-only
change gets fast, dependency-free CI feedback.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

AUTHORIZATION_PHRASE = "Authorized by the project owner"
QA_DECISION_PHRASE = "QA Decision"
REQUIRED_ADR_RANGE = range(1, 21)  # spec section 21 lists planning-list items #1-#20
TRANSITION_TASK_ID_RE = re.compile(r"^T\d+$")


@dataclass
class Violation:
    check: str
    message: str
    severity: str = "ERROR"  # ERROR fails CI; WARNING is reported but does not fail


@dataclass
class TaskRow:
    task_id: str
    line_no: int
    text: str


@dataclass
class TransitionExemption:
    """A validated, in-progress Required-ADR governance transition. Only ever
    constructed by validate_in_progress_transition() after every check below
    has passed -- never assembled or trusted from raw ledger input directly."""

    task: str
    required_adrs: set[int]


@dataclass
class AdrFile:
    number: int
    header_number: int | None
    path: Path
    resolves: set[int] = field(default_factory=set)


def find_repo_root(start: Path) -> Path:
    """Walk upward from `start` until a directory containing
    IMPLEMENTATION_QUEUE.md is found. Keeps the validator runnable from any
    working directory, including CI's default checkout path."""
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "IMPLEMENTATION_QUEUE.md").is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate repository root (no IMPLEMENTATION_QUEUE.md found in "
        f"{start} or any parent directory)."
    )


# ---------------------------------------------------------------------------
# IMPLEMENTATION_QUEUE.md checks
# ---------------------------------------------------------------------------

TASK_ROW_RE = re.compile(r"^\|\s*(T\d+)\s*\|")


def parse_task_rows(text: str) -> list[TaskRow]:
    """Every line beginning with a `| TNN |` cell is treated as one task
    row -- this repository's own convention keeps a task's entire prose on
    a single physical line, regardless of which table it lives in."""
    rows: list[TaskRow] = []
    for i, line in enumerate(text.splitlines(), start=1):
        m = TASK_ROW_RE.match(line)
        if m:
            rows.append(TaskRow(task_id=m.group(1), line_no=i, text=line))
    return rows


def check_duplicate_task_ids(rows: list[TaskRow]) -> list[Violation]:
    seen: dict[str, list[int]] = {}
    for row in rows:
        seen.setdefault(row.task_id, []).append(row.line_no)
    violations = []
    for task_id, lines in seen.items():
        if len(lines) > 1:
            violations.append(
                Violation(
                    "duplicate-task-id",
                    f"{task_id} appears as its own row {len(lines)} times "
                    f"(IMPLEMENTATION_QUEUE.md lines {lines}) -- task IDs must be unique "
                    "and immutable per AI_BOOTSTRAP.md.",
                )
            )
    return violations


def check_done_requires_authorization(rows: list[TaskRow]) -> list[Violation]:
    """A row that declares its own task Done must also carry this
    repository's established authorization phrase in the same row. This is
    a heuristic tied to this repository's actual, observed convention
    (verified present on every Done row from T4 through T94 at the time
    this check was written) -- not an assumption about how governance
    *should* be written. If that convention changes, update this check
    deliberately rather than letting it silently stop catching anything."""
    violations = []
    for row in rows:
        done_marker = f"{row.task_id} is now Done"
        if done_marker in row.text and AUTHORIZATION_PHRASE not in row.text:
            violations.append(
                Violation(
                    "done-without-authorization",
                    f"{row.task_id} (IMPLEMENTATION_QUEUE.md line {row.line_no}) is marked "
                    f'"{done_marker}" but its own row does not contain the '
                    f'"{AUTHORIZATION_PHRASE}" phrase -- a task must not be closed out '
                    "without repository-recorded authorization evidence in the same row.",
                )
            )
    return violations


def check_done_requires_qa_evidence(rows: list[TaskRow]) -> list[Violation]:
    """A row that declares its own task Done must also mention a QA
    Decision somewhere in the same row -- verified present on every Done
    row from T4 through T94 when this check was written, mirroring
    check_done_requires_authorization's discipline. This repository's own
    process (docs/DefinitionOfDone.md) requires a QA Decision before a
    task is closed out; 'Rework required' blocks merge entirely."""
    violations = []
    for row in rows:
        done_marker = f"{row.task_id} is now Done"
        if done_marker in row.text and QA_DECISION_PHRASE.lower() not in row.text.lower():
            violations.append(
                Violation(
                    "done-without-qa-evidence",
                    f"{row.task_id} (IMPLEMENTATION_QUEUE.md line {row.line_no}) is marked "
                    f'"{done_marker}" but its own row does not mention a "{QA_DECISION_PHRASE}" '
                    "-- a task must not be closed out without a recorded QA Decision.",
                )
            )
    return violations


def latest_task_number(rows: list[TaskRow], marker_fn) -> str | None:
    """Highest-numbered task row for which marker_fn(row) is true, or None
    if no row matches. Used to cross-check governanceLedger's
    latestTaskAuthorized/latestTaskDone against the rows themselves,
    instead of trusting a hand-maintained value."""
    candidates = [row for row in rows if marker_fn(row)]
    if not candidates:
        return None
    return max(candidates, key=lambda r: int(r.task_id[1:])).task_id


ADR_REFERENCE_RE = re.compile(r"ADR/(\d{4})\b")


def check_adr_references(text: str, existing_numbers: set[int]) -> list[Violation]:
    violations = []
    seen: set[int] = set()
    for m in ADR_REFERENCE_RE.finditer(text):
        num = int(m.group(1))
        if num in seen:
            continue
        seen.add(num)
        if num not in existing_numbers:
            violations.append(
                Violation(
                    "dangling-adr-reference",
                    f"IMPLEMENTATION_QUEUE.md references `ADR/{num:04d}` but no ADR file with "
                    "that number exists in ADR/.",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# ADR/*.md checks
# ---------------------------------------------------------------------------

ADR_FILENAME_RE = re.compile(r"^(\d{4})-.+\.md$")
ADR_HEADER_RE = re.compile(r"^#\s*ADR-(\d{4}):", re.MULTILINE)
# Only look inside the bolded "**Resolves:**" field, up to the next blank
# line or the next bolded field label -- deliberately not a whole-file scan,
# so an ADR's "Does not resolve" / "Dependencies" prose can freely mention
# other Required ADR numbers without this being misread as a resolution.
RESOLVES_BLOCK_RE = re.compile(
    r"\*\*Resolves:\*\*(.*?)(?:\n\n|\*\*Does not resolve|\*\*Dependencies)",
    re.DOTALL,
)
REQUIRED_ADR_NUMBER_RE = re.compile(r"#(\d{1,2})\b")


def parse_adr_files(adr_dir: Path) -> tuple[list[AdrFile], list[Violation]]:
    violations: list[Violation] = []
    adrs: list[AdrFile] = []
    numbers_seen: dict[int, list[Path]] = {}

    for path in sorted(adr_dir.glob("*.md")):
        m = ADR_FILENAME_RE.match(path.name)
        if not m:
            continue  # e.g. template.md -- not a numbered decision record
        number = int(m.group(1))
        numbers_seen.setdefault(number, []).append(path)

        content = path.read_text(encoding="utf-8")
        header_m = ADR_HEADER_RE.search(content)
        header_number = int(header_m.group(1)) if header_m else None
        if header_number is not None and header_number != number:
            violations.append(
                Violation(
                    "adr-number-mismatch",
                    f"{path.name}: filename number {number:04d} does not match its own "
                    f"H1 header number {header_number:04d}.",
                )
            )
        elif header_number is None:
            violations.append(
                Violation(
                    "adr-header-missing",
                    f"{path.name}: no `# ADR-NNNN: ...` header found to cross-check "
                    "against the filename number.",
                    severity="WARNING",
                )
            )

        resolves: set[int] = set()
        resolves_m = RESOLVES_BLOCK_RE.search(content)
        if resolves_m:
            for num_m in REQUIRED_ADR_NUMBER_RE.finditer(resolves_m.group(1)):
                n = int(num_m.group(1))
                if n in REQUIRED_ADR_RANGE:
                    resolves.add(n)

        adrs.append(AdrFile(number=number, header_number=header_number, path=path, resolves=resolves))

    for number, paths in numbers_seen.items():
        if len(paths) > 1:
            names = ", ".join(p.name for p in paths)
            violations.append(
                Violation(
                    "duplicate-adr-number",
                    f"ADR number {number:04d} is used by more than one file: {names}.",
                )
            )

    return adrs, violations


def check_duplicate_required_adr_resolution(adrs: list[AdrFile]) -> list[Violation]:
    resolved_by: dict[int, list[str]] = {}
    for adr in adrs:
        for n in adr.resolves:
            resolved_by.setdefault(n, []).append(adr.path.name)

    violations = []
    for n, files in resolved_by.items():
        if len(files) > 1:
            violations.append(
                Violation(
                    "duplicate-required-adr-resolution",
                    f"Required ADR #{n} is claimed as resolved by more than one ADR file: "
                    f"{', '.join(files)} -- this must not happen without one explicitly "
                    "superseding the other, and no ADR in this repository currently does.",
                )
            )
    return violations


def compute_resolved_required_adrs(adrs: list[AdrFile]) -> set[int]:
    resolved: set[int] = set()
    for adr in adrs:
        resolved |= adr.resolves
    return resolved


# ---------------------------------------------------------------------------
# PROJECT_STATE.json checks
# ---------------------------------------------------------------------------


def validate_in_progress_transition(
    ledger: dict, resolved: set[int], recorded_resolved: set[int], rows: list[TaskRow]
) -> tuple[list[Violation], TransitionExemption | None]:
    """Validate an optional `governanceLedger.inProgressTransitions` declaration
    against authoritative repository evidence already available to this validator
    (IMPLEMENTATION_QUEUE.md's own rows; the ADR-derived resolved set) -- never
    against git history, a task/ADR/PR number literal, or anything this validator
    doesn't already compute for its own, unrelated checks.

    Returns (violations, exemption). `exemption` is non-None only when every check
    below passes; any failure returns an empty exemption (fail-safe: a malformed,
    unauthorized, stale, ambiguous, or out-of-scope declaration grants no leniency
    at all, not partial leniency).

    This function decides one thing only: whether a *specific, currently-declared*
    ADR-resolution gap is legitimately explained by a named, currently-authorized,
    not-yet-Done task. It does not, and must not, know about any particular task
    ID, ADR number, or PR number -- see docs/GOVERNANCE_VALIDATION.md's
    "In-progress transition declarations" section for the generalization
    requirement this exists to satisfy."""
    raw = ledger.get("inProgressTransitions")
    if raw is None:
        return [], None  # no declaration at all -- ordinary settled-state validation applies

    if not isinstance(raw, list):
        return (
            [
                Violation(
                    "governance-transition-malformed",
                    "PROJECT_STATE.json governanceLedger.inProgressTransitions must be a list "
                    f"of at most one transition object; got {type(raw).__name__}.",
                )
            ],
            None,
        )

    if len(raw) == 0:
        return [], None  # explicitly declared empty -- equivalent to absent

    if len(raw) > 1:
        return (
            [
                Violation(
                    "governance-transition-ambiguous",
                    f"PROJECT_STATE.json governanceLedger.inProgressTransitions declares "
                    f"{len(raw)} simultaneous transitions -- at most one in-progress Required-ADR "
                    "transition is supported at a time; an ambiguous declaration is treated as "
                    "granting no exemption, not as if the first/most-plausible entry were chosen.",
                )
            ],
            None,
        )

    entry = raw[0]
    if not isinstance(entry, dict) or "task" not in entry or "requiredAdrs" not in entry:
        return (
            [
                Violation(
                    "governance-transition-malformed",
                    "PROJECT_STATE.json governanceLedger.inProgressTransitions[0] must be an "
                    f"object with 'task' and 'requiredAdrs' fields; got {entry!r}.",
                )
            ],
            None,
        )

    task = entry["task"]
    declared_raw = entry["requiredAdrs"]
    if not isinstance(task, str) or not TRANSITION_TASK_ID_RE.match(task):
        return (
            [
                Violation(
                    "governance-transition-malformed",
                    f"PROJECT_STATE.json governanceLedger.inProgressTransitions[0].task {task!r} "
                    "is not a valid task ID (expected the shape 'T' followed by digits).",
                )
            ],
            None,
        )
    if (
        not isinstance(declared_raw, list)
        or not declared_raw
        or not all(isinstance(n, int) and not isinstance(n, bool) for n in declared_raw)
    ):
        return (
            [
                Violation(
                    "governance-transition-malformed",
                    "PROJECT_STATE.json governanceLedger.inProgressTransitions[0].requiredAdrs "
                    f"must be a non-empty list of integers; got {declared_raw!r}.",
                )
            ],
            None,
        )

    declared_adrs = set(declared_raw)
    out_of_range = declared_adrs - set(REQUIRED_ADR_RANGE)
    if out_of_range:
        return (
            [
                Violation(
                    "governance-transition-invalid-adr-state",
                    "PROJECT_STATE.json governanceLedger.inProgressTransitions[0].requiredAdrs "
                    f"names Required-ADR number(s) {sorted(out_of_range)} outside the valid "
                    f"planning-list range {REQUIRED_ADR_RANGE.start}-{REQUIRED_ADR_RANGE.stop - 1}.",
                )
            ],
            None,
        )

    # The declared task must correspond to a genuinely authorized row -- not merely
    # any row that happens to share the ID, and not a fabricated/nonexistent one.
    task_row = next((r for r in rows if r.task_id == task), None)
    if task_row is None or AUTHORIZATION_PHRASE not in task_row.text:
        return (
            [
                Violation(
                    "governance-transition-unauthorized",
                    f"PROJECT_STATE.json governanceLedger.inProgressTransitions[0] declares task "
                    f"{task!r}, but IMPLEMENTATION_QUEUE.md has no row for {task!r} carrying the "
                    f'"{AUTHORIZATION_PHRASE}" phrase -- an in-progress transition must cite a '
                    "task this repository's own records show as actually authorized.",
                )
            ],
            None,
        )

    # The declared task need not be the single, numerically-highest authorized task
    # ("the frontier") -- only *an* authorized, not-yet-Done task. A frontier-equality
    # constraint would assume at most one task can ever be authorized-and-open at a
    # time; in practice a later-authorized task can be implemented and closed out
    # (becoming both the new frontier and already Done) before an earlier task's own
    # PR merges, leaving that earlier task's transition declaration unable to satisfy
    # either a frontier-equality check (it's no longer the frontier) or the
    # already-Done check below (it was never Done itself) -- rejected by a mechanism
    # meant to let it pass. The authorized-row check immediately above and the
    # already-Done check immediately below jointly express the actual requirement
    # ("authorized and still open") without assuming authorization is exclusive to
    # one task at a time.

    # A task already marked Done has no "in-progress" transition left to explain --
    # that window closes at Governance Closeout, which is expected to remove this
    # declaration, not leave it lingering as a permanent excuse.
    if f"{task} is now Done" in task_row.text:
        return (
            [
                Violation(
                    "governance-transition-already-settled",
                    f"PROJECT_STATE.json governanceLedger.inProgressTransitions[0] declares "
                    f"{task!r} as in-progress, but IMPLEMENTATION_QUEUE.md's own row already "
                    f"marks {task!r} Done -- a settled task must not carry a lingering "
                    "in-progress transition declaration; Governance Closeout should have removed "
                    "it.",
                )
            ],
            None,
        )

    # The declared ADRs must be *exactly* the real, currently-unsynchronized gap --
    # no more (that would excuse unrelated drift), no fewer (that would leave a
    # real mismatch this task doesn't actually account for).
    actual_gap = resolved - recorded_resolved
    if declared_adrs != actual_gap:
        return (
            [
                Violation(
                    "governance-transition-scope-mismatch",
                    "PROJECT_STATE.json governanceLedger.inProgressTransitions[0].requiredAdrs "
                    f"{sorted(declared_adrs)} does not exactly match the real, "
                    f"currently-unsynchronized ADR-resolution gap {sorted(actual_gap)} (what the "
                    "ADR files themselves resolve, minus governanceLedger.resolvedRequiredADRs) "
                    "-- a legitimate declaration must name exactly the gap it accounts for.",
                )
            ],
            None,
        )

    return [], TransitionExemption(task=task, required_adrs=declared_adrs)


def check_governance_ledger(
    project_state: dict, resolved: set[int], rows: list[TaskRow] | None = None
) -> list[Violation]:
    violations: list[Violation] = []
    ledger = project_state.get("governanceLedger")
    if ledger is None:
        return violations  # optional field; absence is not itself an error

    unresolved = set(REQUIRED_ADR_RANGE) - resolved
    recorded_resolved_for_transition = (
        set(ledger["resolvedRequiredADRs"]) if "resolvedRequiredADRs" in ledger else set()
    )
    transition_violations, exemption = validate_in_progress_transition(
        ledger, resolved, recorded_resolved_for_transition, rows or []
    )
    violations += transition_violations
    exempt_adrs = exemption.required_adrs if exemption is not None else set()

    # Each sub-field is independently optional -- a ledger that declares only, say,
    # latestTaskDone must not be flagged as if it had declared an empty resolved-ADR
    # list. Only compare a field that is actually present.
    if "resolvedRequiredADRs" in ledger:
        recorded_resolved = set(ledger["resolvedRequiredADRs"])
        if (recorded_resolved | exempt_adrs) != resolved:
            violations.append(
                Violation(
                    "governance-ledger-drift",
                    "PROJECT_STATE.json governanceLedger.resolvedRequiredADRs "
                    f"{sorted(recorded_resolved)} does not match what the ADR files "
                    f"themselves declare resolved {sorted(resolved)} -- missing: "
                    f"{sorted(resolved - recorded_resolved)}, extra/stale: "
                    f"{sorted(recorded_resolved - resolved)}.",
                )
            )
    if "unresolvedRequiredADRs" in ledger:
        recorded_unresolved = set(ledger["unresolvedRequiredADRs"])
        if (recorded_unresolved - exempt_adrs) != unresolved:
            violations.append(
                Violation(
                    "governance-ledger-drift",
                    "PROJECT_STATE.json governanceLedger.unresolvedRequiredADRs "
                    f"{sorted(recorded_unresolved)} does not match the complement of the "
                    f"resolved set {sorted(unresolved)} -- missing: "
                    f"{sorted(unresolved - recorded_unresolved)}, extra/stale: "
                    f"{sorted(recorded_unresolved - unresolved)}.",
                )
            )

    if rows is not None:
        for field_name, marker_fn in (
            ("latestTaskDone", lambda r: f"{r.task_id} is now Done" in r.text),
            ("latestTaskAuthorized", lambda r: AUTHORIZATION_PHRASE in r.text),
        ):
            if field_name not in ledger:
                continue  # optional sub-field; absence is not itself an error
            recorded = ledger[field_name]
            computed = latest_task_number(rows, marker_fn)
            if recorded == computed:
                continue
            # latestTaskDone is never exempted -- Closeout's zero-tolerance
            # requirement for the *settled* state must hold regardless of any
            # in-progress transition declared for a still-open task.
            if (
                field_name == "latestTaskAuthorized"
                and exemption is not None
                and exemption.task == computed
            ):
                continue  # the same validated transition already explains this exact drift
            violations.append(
                Violation(
                    "governance-ledger-drift",
                    f"PROJECT_STATE.json governanceLedger.{field_name} is {recorded!r} but "
                    f"IMPLEMENTATION_QUEUE.md's own rows compute {computed!r} -- update the "
                    "ledger or investigate why they disagree.",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def validate(root: Path) -> list[Violation]:
    violations: list[Violation] = []

    queue_path = root / "IMPLEMENTATION_QUEUE.md"
    queue_text = queue_path.read_text(encoding="utf-8")
    rows = parse_task_rows(queue_text)
    violations += check_duplicate_task_ids(rows)
    violations += check_done_requires_authorization(rows)
    violations += check_done_requires_qa_evidence(rows)

    adr_dir = root / "ADR"
    adrs, adr_violations = parse_adr_files(adr_dir)
    violations += adr_violations
    violations += check_duplicate_required_adr_resolution(adrs)

    existing_numbers = {adr.number for adr in adrs}
    violations += check_adr_references(queue_text, existing_numbers)

    state_path = root / "PROJECT_STATE.json"
    try:
        project_state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        violations.append(
            Violation("invalid-project-state-json", f"PROJECT_STATE.json is not valid JSON: {exc}")
        )
    else:
        resolved = compute_resolved_required_adrs(adrs)
        violations += check_governance_ledger(project_state, resolved, rows)

    return violations


def report(root: Path) -> str:
    """Human-readable resolved/unresolved Required-ADR summary -- the live
    answer to "which Required ADRs are resolved?" for a fresh agent, without
    needing to grep every ADR file by hand."""
    adrs, _ = parse_adr_files(root / "ADR")
    resolved = compute_resolved_required_adrs(adrs)
    unresolved = sorted(set(REQUIRED_ADR_RANGE) - resolved)
    resolved_by: dict[int, str] = {}
    for adr in adrs:
        for n in adr.resolves:
            resolved_by[n] = adr.path.name

    lines = ["Required ADR resolution status (computed from ADR/*.md 'Resolves:' fields):", ""]
    for n in REQUIRED_ADR_RANGE:
        if n in resolved_by:
            lines.append(f"  #{n:2d}  RESOLVED  -- {resolved_by[n]}")
        else:
            lines.append(f"  #{n:2d}  unresolved")
    lines.append("")
    lines.append(f"Resolved:   {sorted(resolved)}")
    lines.append(f"Unresolved: {unresolved}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=None, help="Repository root (default: auto-detected)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print the Required-ADR resolution summary instead of validating.",
    )
    args = parser.parse_args(argv)

    root = args.root or find_repo_root(Path(__file__).parent)

    if args.report:
        print(report(root))
        return 0

    violations = validate(root)
    errors = [v for v in violations if v.severity == "ERROR"]
    warnings = [v for v in violations if v.severity == "WARNING"]

    for v in violations:
        print(f"[{v.severity}] {v.check}: {v.message}", file=sys.stderr)

    if errors:
        print(
            f"\ngovernance_validate: {len(errors)} error(s), {len(warnings)} warning(s).",
            file=sys.stderr,
        )
        return 1

    print(
        f"governance_validate: OK ({len(warnings)} warning(s), 0 errors) -- "
        f"{root / 'IMPLEMENTATION_QUEUE.md'}, {root / 'PROJECT_STATE.json'}, "
        f"{root / 'ADR'} are internally consistent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
