"""T156 structured delivery calendar validation; stdlib only, prospective T157+."""
from __future__ import annotations
from datetime import date, timedelta
import json
from pathlib import Path

REQUIRED = ("id", "title", "milestone", "lane", "dependencies", "critical_path",
            "planned_start", "planned_finish", "planned_duration",
            "forecast_start", "forecast_finish", "forecast_impact")
DONE = ("actual_start", "actual_completion", "actual_elapsed", "planned_finish_used",
        "variance", "classification", "critical_at_completion",
        "milestone_impact", "finalization_impact", "recalculated")
def day(value):
    if not isinstance(value, str) or len(value) != 10 or date.fromisoformat(value).isoformat() != value:
        raise ValueError("expected ISO YYYY-MM-DD")
    return date.fromisoformat(value)

def span(start, finish):
    return (day(finish)-day(start)).days+1

def movement(old, new):
    return (day(new)-day(old)).days

def direction(delta):
    return "earlier" if delta < 0 else "later" if delta > 0 else "unchanged"

def classification(delta):
    return "Early" if delta < 0 else "Late" if delta > 0 else "On Time"

def forecast(tasks, milestone_id, baseline):
    """Dependency DAG: finish=max(planned floor, predecessor finish+1), inclusive duration.
    Independent lanes overlap. Milestone date never advances without a complete
    dependency model: this function is for explicitly scheduled task networks only.
    """
    nodes = {t["id"]:t for t in tasks if t["milestone"] == milestone_id}
    cache = {}
    visiting = set()
    def finish(task_id):
        if task_id in cache: return cache[task_id]
        if task_id in visiting: raise ValueError("dependency cycle")
        if task_id not in nodes: raise ValueError("missing milestone dependency: "+task_id)
        visiting.add(task_id)
        t = nodes[task_id]
        floor = day(t["forecast_start"])
        for pred in t["dependencies"]:
            floor = max(floor, finish(pred)+timedelta(days=1))
        end = floor+timedelta(days=t["planned_duration"]-1)
        if t.get("actual_completion"):
            end = day(t["actual_completion"])
        visiting.remove(task_id)
        cache[task_id] = end
        return end
    if not nodes: return baseline
    return max([day(baseline)]+[finish(k) for k in nodes]).isoformat()

def check_calendar(data, rows):
    errors=[]
    if data.get("schema_version") != 1 or data.get("activation_task_number") != 157:
        errors.append("invalid schema/activation boundary")
    milestones={m.get("id"):m for m in data.get("milestones",[])}
    lanes={l.get("id") for l in data.get("lanes",[])}
    if not {"M1","M2","M3"}.issubset(milestones):
        errors.append("missing M1/M2/M3")
    for mid,m in milestones.items():
        try:
            delta=movement(m["baseline"],m["forecast"])
            if m.get("actual") is not None: day(m["actual"])
            day(m["last_recalculated"])
            if not m.get("confidence") or not m.get("risk"): raise ValueError("missing confidence/risk")
            history=[h for h in data.get("history",[]) if h.get("milestone")==mid]
            if delta and not history: raise ValueError("forecast moved without history")
            if history:
                prev=m["baseline"]
                for h in history:
                    if h["old"] != prev or movement(h["old"],h["new"]) != h["movement"] or direction(h["movement"]) != h["direction"] or not h["reason"] or not h["trigger"]:
                        raise ValueError("invalid forecast history")
                    day(h["recalculated"])
                    prev=h["new"]
                if prev != m["forecast"]: raise ValueError("history does not reconcile forecast")
        except (ValueError,KeyError,TypeError) as exc: errors.append(f"{mid}: {exc}")
    taskmap={t.get("id"):t for t in data.get("tasks",[])}
    if len(taskmap)!=len(data.get("tasks",[])): errors.append("duplicate calendar task ID")
    rowmap={r.task_id:r for r in rows}
    for task_id,row in rowmap.items():
        try: number=int(task_id[1:])
        except ValueError: continue
        if number < 157: continue
        if task_id not in taskmap: errors.append(f"{task_id}: missing mandatory calendar record")
    for task_id,t in taskmap.items():
        try:
            if not task_id.startswith("T") or int(task_id[1:])<157: raise ValueError("pre-activation task")
            if task_id not in rowmap: raise ValueError("calendar entry not in queue")
            for key in REQUIRED:
                if key not in t or t[key] is None: raise ValueError("missing "+key)
            if t["milestone"] not in milestones: raise ValueError("unknown milestone")
            if t["lane"] not in lanes: raise ValueError("unknown lane")
            if not isinstance(t["dependencies"],list) or not isinstance(t["critical_path"],dict) or not isinstance(t["forecast_impact"],dict): raise ValueError("invalid dependency/critical-path/impact metadata")
            if "slack_days" not in t["critical_path"] or "is_critical" not in t["critical_path"]: raise ValueError("missing critical path slack")
            if not isinstance(t["critical_path"]["is_critical"],bool) or type(t["critical_path"]["slack_days"]) is not int or t["critical_path"]["slack_days"]<0: raise ValueError("invalid critical path")
            if type(t["planned_duration"]) is not int or t["planned_duration"]<1 or span(t["planned_start"],t["planned_finish"])!=t["planned_duration"]: raise ValueError("planned duration mismatch")
            if span(t["forecast_start"],t["forecast_finish"])<1: raise ValueError("invalid forecast span")
            for dep in t["dependencies"]:
                if dep not in taskmap and dep not in rowmap: raise ValueError("unknown dependency")
            if not t.get("title"): raise ValueError("missing title")
            if "Done" in rowmap[task_id].text.split("|")[-2]:
                for key in DONE:
                    if key not in t or t[key] is None: raise ValueError("Done missing "+key)
                if t["planned_finish_used"] != t["planned_finish"]: raise ValueError("planned finish baseline changed")
                if span(t["actual_start"],t["actual_completion"])!=t["actual_elapsed"]: raise ValueError("actual elapsed mismatch")
                delta=movement(t["planned_finish_used"],t["actual_completion"])
                if t["variance"]!=delta or t["classification"]!=classification(delta): raise ValueError("variance/classification mismatch")
                day(t["recalculated"])
        except (ValueError,KeyError,TypeError,AttributeError) as exc: errors.append(f"{task_id}: {exc}")
    return errors

def validate_file(root,rows):
    try:
        data=json.loads((Path(root)/"docs/delivery_calendar.json").read_text(encoding="utf-8"))
        return check_calendar(data,rows)
    except (OSError,ValueError) as exc:
        return ["delivery calendar unavailable/invalid: "+str(exc)]
