"""Structured delivery-calendar validation for T157+ (stdlib only)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

PROJECT_TIMEZONE = "Asia/Kolkata"
SCHEMA_VERSION = 2
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = ("id", "title", "milestone", "lane", "dependencies", "critical_path",
            "planned_start", "planned_finish", "planned_duration", "forecast_start",
            "forecast_finish", "forecast_impact")
DONE = ("actual_start", "actual_completion", "actual_elapsed", "planned_finish_used",
        "variance", "classification", "critical_at_completion", "milestone_impact",
        "finalization_impact", "recalculated")


def day(value):
    if not isinstance(value, str) or len(value) != 10 or date.fromisoformat(value).isoformat() != value:
        raise ValueError("expected ISO YYYY-MM-DD")
    return date.fromisoformat(value)


def span(start, finish): return (day(finish) - day(start)).days + 1
def movement(old, new): return (day(new) - day(old)).days
def direction(delta): return "earlier" if delta < 0 else "later" if delta > 0 else "unchanged"
def classification(delta): return "Early" if delta < 0 else "Late" if delta > 0 else "On Time"


def local_completion_date(merged_at_utc):
    """Convert the canonical GitHub UTC timestamp using the fixed project clock."""
    if not isinstance(merged_at_utc, str) or not merged_at_utc.endswith("Z"):
        raise ValueError("merged_at_utc must be an ISO UTC timestamp ending in Z")
    instant = datetime.fromisoformat(merged_at_utc[:-1] + "+00:00")
    if instant.tzinfo is None or instant.utcoffset() != timedelta(0):
        raise ValueError("merged_at_utc must be UTC")
    return instant.astimezone(ZoneInfo(PROJECT_TIMEZONE)).date().isoformat()


def dependencies(task, schema_version):
    raw = task["dependencies"]
    if schema_version == 1:
        if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
            raise ValueError("invalid legacy dependencies")
        return raw, []
    if not isinstance(raw, dict):
        raise ValueError("dependencies must type finish_to_start and defect_evidence edges")
    scheduling, evidence = raw.get("finish_to_start"), raw.get("defect_evidence")
    if (not isinstance(scheduling, list) or not isinstance(evidence, list)
            or not all(isinstance(x, str) for x in scheduling + evidence)):
        raise ValueError("invalid typed dependencies")
    if set(scheduling) & set(evidence):
        raise ValueError("dependency cannot be both scheduling and defect evidence")
    return scheduling, evidence


def forecast(tasks, milestone_id, baseline):
    """Calculate only finish-to-start edges; evidence references are never scheduled."""
    nodes = {t["id"]: t for t in tasks if t["milestone"] == milestone_id}
    schema = SCHEMA_VERSION if all(isinstance(t.get("dependencies"), dict) for t in nodes.values()) else 1
    cache, visiting = {}, set()

    def finish(task_id):
        if task_id in cache: return cache[task_id]
        if task_id in visiting: raise ValueError("dependency cycle")
        if task_id not in nodes: raise ValueError("missing milestone scheduling dependency: " + task_id)
        visiting.add(task_id)
        task = nodes[task_id]
        floor = day(task["forecast_start"])
        scheduling, _ = dependencies(task, schema)
        for predecessor in scheduling:
            floor = max(floor, finish(predecessor) + timedelta(days=1))
        end = floor + timedelta(days=task["planned_duration"] - 1)
        if task.get("actual_completion"): end = day(task["actual_completion"])
        visiting.remove(task_id)
        cache[task_id] = end
        return end

    if not nodes: return baseline
    return max([day(baseline)] + [finish(key) for key in nodes]).isoformat()


def queue_status(row):
    cells = [cell.strip() for cell in row.text.strip().split("|")]
    if len(cells) != 6 or cells[0] or cells[-1] or cells[1] != row.task_id:
        raise ValueError("malformed four-column task queue row")
    if cells[3] not in ("Authorized", "Done"):
        raise ValueError("unsupported task queue status: " + cells[3])
    return cells[3]


def completion_evidence(task):
    evidence = task.get("completion_evidence")
    if not isinstance(evidence, dict): raise ValueError("Done missing completion_evidence")
    required = ("implementation_pr", "protected_merge_sha", "protected_merge_parents",
                "merged_at_utc", "timezone", "approved_qa_publication_head", "actual_start_evidence")
    if any(key not in evidence or evidence[key] in (None, "") for key in required):
        raise ValueError("incomplete completion_evidence")
    if type(evidence["implementation_pr"]) is not int or evidence["implementation_pr"] < 1:
        raise ValueError("invalid implementation_pr")
    if not SHA_RE.fullmatch(evidence["protected_merge_sha"]): raise ValueError("invalid protected_merge_sha")
    parents = evidence["protected_merge_parents"]
    if not isinstance(parents, list) or len(parents) != 2 or not all(SHA_RE.fullmatch(x) for x in parents):
        raise ValueError("protected merge must record exactly two SHA parents")
    if not SHA_RE.fullmatch(evidence["approved_qa_publication_head"]):
        raise ValueError("invalid approved QA publication head")
    if evidence["timezone"] != PROJECT_TIMEZONE: raise ValueError("completion timezone must be " + PROJECT_TIMEZONE)
    if local_completion_date(evidence["merged_at_utc"]) != task["actual_completion"]:
        raise ValueError("actual_completion does not match project-local merge date")
    return evidence


def check_scheduling_cycles(taskmap):
    """Only current, typed scheduling edges can form a calendar cycle."""
    visiting, visited = set(), set()

    def visit(task_id):
        if task_id in visiting: raise ValueError("dependency cycle")
        if task_id in visited: return
        visiting.add(task_id)
        for predecessor in taskmap[task_id]["dependencies"]["finish_to_start"]:
            if predecessor in taskmap: visit(predecessor)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in taskmap: visit(task_id)


def check_calendar(data, rows):
    errors = []
    schema = data.get("schema_version")
    if schema not in (1, SCHEMA_VERSION) or data.get("activation_task_number") != 157:
        return ["invalid schema/activation boundary"]
    if schema == SCHEMA_VERSION and data.get("project_timezone") != PROJECT_TIMEZONE:
        errors.append("project timezone must be " + PROJECT_TIMEZONE)
    milestones = {m.get("id"): m for m in data.get("milestones", [])}
    lanes = {lane.get("id") for lane in data.get("lanes", [])}
    if not {"M1", "M2", "M3"}.issubset(milestones): errors.append("missing M1/M2/M3")
    trigger_keys = set()
    for mid, milestone in milestones.items():
        try:
            delta = movement(milestone["baseline"], milestone["forecast"])
            if milestone.get("actual") is not None: day(milestone["actual"])
            day(milestone["last_recalculated"])
            if not milestone.get("confidence") or not milestone.get("risk"): raise ValueError("missing confidence/risk")
            history = [h for h in data.get("history", []) if h.get("milestone") == mid]
            if delta and not history: raise ValueError("forecast moved without history")
            previous = milestone["baseline"]
            for entry in history:
                key = entry.get("trigger_key")
                if schema == SCHEMA_VERSION and not key: raise ValueError("history missing immutable trigger_key")
                if key and key in trigger_keys: raise ValueError("duplicate immutable history trigger_key")
                if key: trigger_keys.add(key)
                if (entry["old"] != previous or movement(entry["old"], entry["new"]) != entry["movement"]
                        or direction(entry["movement"]) != entry["direction"] or not entry["reason"] or not entry["trigger"]):
                    raise ValueError("invalid forecast history")
                day(entry["recalculated"]); previous = entry["new"]
            if previous != milestone["forecast"]: raise ValueError("history does not reconcile forecast")
        except (ValueError, KeyError, TypeError) as exc: errors.append(f"{mid}: {exc}")
    taskmap = {task.get("id"): task for task in data.get("tasks", [])}
    if len(taskmap) != len(data.get("tasks", [])): errors.append("duplicate calendar task ID")
    rowmap = {row.task_id: row for row in rows}
    for task_id, row in rowmap.items():
        try: number = int(task_id[1:])
        except ValueError: continue
        if number >= 157 and task_id not in taskmap: errors.append(f"{task_id}: missing mandatory calendar record")
    for task_id, task in taskmap.items():
        try:
            if not task_id.startswith("T") or int(task_id[1:]) < 157: raise ValueError("pre-activation task")
            if task_id not in rowmap: raise ValueError("calendar entry not in queue")
            for key in REQUIRED:
                if key not in task or task[key] is None: raise ValueError("missing " + key)
            if task["milestone"] not in milestones or task["lane"] not in lanes: raise ValueError("unknown milestone/lane")
            if not isinstance(task["critical_path"], dict) or not isinstance(task["forecast_impact"], dict):
                raise ValueError("invalid critical-path/impact metadata")
            if (not isinstance(task["critical_path"].get("is_critical"), bool)
                    or type(task["critical_path"].get("slack_days")) is not int or task["critical_path"]["slack_days"] < 0):
                raise ValueError("invalid critical path")
            if type(task["planned_duration"]) is not int or task["planned_duration"] < 1 or span(task["planned_start"], task["planned_finish"]) != task["planned_duration"]:
                raise ValueError("planned duration mismatch")
            if span(task["forecast_start"], task["forecast_finish"]) < 1: raise ValueError("invalid forecast span")
            scheduling, evidence = dependencies(task, schema)
            if any(dep not in taskmap and dep not in rowmap for dep in scheduling + evidence): raise ValueError("unknown dependency")
            status = queue_status(rowmap[task_id])
            if status == "Done":
                for key in DONE:
                    if task.get(key) is None: raise ValueError("Done missing " + key)
                if task["planned_finish_used"] != task["planned_finish"]: raise ValueError("planned finish baseline changed")
                if span(task["actual_start"], task["actual_completion"]) != task["actual_elapsed"]: raise ValueError("actual elapsed mismatch")
                delta = movement(task["planned_finish_used"], task["actual_completion"])
                if task["variance"] != delta or task["classification"] != classification(delta): raise ValueError("variance/classification mismatch")
                day(task["recalculated"])
                if schema == SCHEMA_VERSION: completion_evidence(task)
            elif any(key in task and task[key] is not None for key in DONE + ("completion_evidence",)):
                raise ValueError("Authorized task has premature completion data")
        except (ValueError, KeyError, TypeError, AttributeError) as exc: errors.append(f"{task_id}: {exc}")
    if schema == SCHEMA_VERSION:
        try:
            check_scheduling_cycles(taskmap)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"scheduling topology: {exc}")
    return errors


def pending_closeout_alerts(data, rows):
    """Operational alert only: static validation cannot remotely prove a merge."""
    if data.get("schema_version") != SCHEMA_VERSION: return []
    alerts = []
    rowmap = {row.task_id: row for row in rows}
    for task in data.get("tasks", []):
        pending = task.get("protected_merge_pending_closeout")
        if pending and task.get("id") in rowmap and queue_status(rowmap[task["id"]]) == "Authorized":
            alerts.append(f"{task['id']}: protected implementation merge recorded; governance closeout remains mandatory")
    return alerts


def validate_file(root, rows):
    try:
        data = json.loads((Path(root) / "docs/delivery_calendar.json").read_text(encoding="utf-8"))
        return check_calendar(data, rows)
    except (OSError, ValueError) as exc:
        return ["delivery calendar unavailable/invalid: " + str(exc)]
