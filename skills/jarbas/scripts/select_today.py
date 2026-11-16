#!/usr/bin/env python3
"""Split today's Todoist board into committed / backlog / exempt / personal.

Implements the daily commitment model in SKILL.md so the model never re-derives
the sort by hand:

  committed  deep work, filled to --limit by UI priority (p1 first), then due
             date, then Today order. Only these get a due time.
  backlog    deep work beyond the limit. Stays on Today and still gets a time and duration.
  exempt     quick, routine, control (plan-the-day), plus any kind you add
             through `task_rules` in the config (for example fixed-time
             tasks). Never counted against the limit.
  personal   tasks in `personal_projects`. Placed outside the work window.

Usage:
  select_today.py [--today today.json] [--projects projects.json] [--limit 3]

Without --today/--projects it runs `td today --json --full --all` and
`td project list --json`. Prints one compact JSON object.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from _common import (
    BUCKETS, CLARIFIED_QUICK, CONFIG, CONTROL_NAME, PERSONAL_PROJECTS, QUICK_NAME,
    ROUTINE_LABELS, ROUTINE_NAME, ROUTINE_PROJECTS, TASK_RULES, WORK_PROJECTS, duration_min, hhmm,
    load_json, project_names, results, run_json, task_due, ui_priority,
)

CORE_KINDS = {"deep", "personal"}  # every other kind is exempt from the limit


def classify(task: dict, project: str) -> str:
    content = task.get("content", "")
    labels = {l.lower() for l in task.get("labels") or []}
    recurring = bool((task.get("due") or {}).get("isRecurring"))
    mins = duration_min(task)
    if CONTROL_NAME.search(content):
        return "control"
    for pattern, kind in TASK_RULES:
        if pattern.search(content.strip()):
            return kind
    if (labels & {"quick"} or CLARIFIED_QUICK.search(task.get("description") or "")
            or (mins is not None and mins <= 10) or QUICK_NAME.search(content)):
        return "quick"
    if labels & ROUTINE_LABELS or project in ROUTINE_PROJECTS or ROUTINE_NAME.search(content):
        return "routine"
    if project in PERSONAL_PROJECTS:
        return "personal"
    if recurring and project not in WORK_PROJECTS and not labels:
        return "routine"  # recurring admin outside work
    return "deep"


def row(task: dict, project: str, kind: str) -> dict:
    start, day = task_due(task)
    labels = task.get("labels") or []
    bucket = next((b for b in BUCKETS if b in labels), None)
    out = {
        "id": task["id"],
        "t": task.get("content", "")[:70],
        "p": ui_priority(task.get("priority", 1)),
        "kind": kind,
        "proj": project,
        "due": hhmm(start) if start else None,
        "dur": duration_min(task),
        "rec": bool((task.get("due") or {}).get("isRecurring")),
    }
    if bucket:
        out["bucket"] = bucket
    if "spike" in labels:
        out["spike"] = True
    if day and not start:
        out["date"] = day.isoformat()
    return out


def select(tasks: list[dict], names: dict, limit: int) -> dict:
    active = [t for t in tasks if not t.get("checked") and not t.get("isDeleted")]
    rows = []
    for t in active:
        project = names.get(t.get("projectId"), t.get("projectId") or "?")
        rows.append((t, row(t, project, classify(t, project))))

    def sort_key(pair):
        t, _ = pair
        start, day = task_due(t)
        return (-int(t.get("priority", 1)), (day.isoformat() if day else "9999"),
                t.get("dayOrder", 0) if t.get("dayOrder", -1) >= 0 else 10**6)

    deep = sorted([p for p in rows if p[1]["kind"] == "deep"], key=sort_key)
    committed = [r for _, r in deep[:limit]]
    backlog = [r for _, r in deep[limit:]]
    exempt = [r for _, r in rows if r["kind"] not in CORE_KINDS]
    personal = [r for _, r in rows if r["kind"] == "personal"]
    unlabelled = [r["id"] for _, r in rows
                  if r["proj"] in WORK_PROJECTS and "bucket" not in r and r["kind"] != "control"]
    return {
        "limit": limit,
        "counts": {"active": len(active), "committed": len(committed), "backlog": len(backlog),
                   "exempt": len(exempt), "personal": len(personal)},
        "committed": committed,
        "backlog": backlog,
        "exempt": exempt,
        "personal": personal,
        "unlabelled_work": unlabelled,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--today", help="saved `td today --json --full --all` output")
    ap.add_argument("--projects", help="saved `td project list --json` output")
    ap.add_argument("--limit", type=int, default=int(os.environ.get("JARBAS_DAILY_LIMIT") or CONFIG["daily_limit"]))
    args = ap.parse_args(argv)

    if args.today:
        tasks_data, err = load_json(args.today), None
    else:
        tasks_data, err = run_json(["td", "today", "--json", "--full", "--all"])
    if err:
        print(json.dumps({"ok": False, "error": f"td today: {err}"}))
        return 2
    if args.projects:
        proj_data, err = load_json(args.projects), None
    else:
        proj_data, err = run_json(["td", "project", "list", "--json"])
    if err:
        print(json.dumps({"ok": False, "error": f"td project list: {err}"}))
        return 2

    out = {"ok": True, **select(results(tasks_data), project_names(proj_data), args.limit)}
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
