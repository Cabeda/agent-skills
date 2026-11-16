#!/usr/bin/env python3
"""Guard: fail when today's written plan breaks a hard rule.

Run after the time writes, before the report. Checks every timed task on
today's board (fresh `td today` read unless --today is given):

  overlap_meeting   task interval intersects a busy meeting (busy_map.py)
  overlap_task      two timed tasks intersect
  work_outside      work-project task outside the work window
  personal_inside   personal-project task inside the work window
  no_time           open task on Today with no start time
  no_duration       timed task with no duration

Every open task on Today must have a start time and a duration. Tasks without
a duration are still checked as 30 min for overlaps. Timed items that end before
--after (default: now) are ignored, since the past cannot be replanned.

Usage:
  check_plan.py --busy busy.json [--today today.json] [--projects projects.json]
                [--after HH:MM]

Exit 0 when clean, 1 when there are violations, 2 on input errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from _common import (
    PERSONAL_PROJECTS, TZ, WORK_PROJECTS, hhmm, in_work_window, load_json,
    overlaps_work_window, project_names, results, run_json, task_interval,
)


def check(tasks: list[dict], names: dict, busy: dict | None, after: datetime, day) -> dict:
    timed = []
    untimed, no_duration = [], []
    for t in tasks:
        if t.get("checked") or t.get("isDeleted"):
            continue
        iv = task_interval(t)
        if iv is None:
            # On the board with no start time (date-only, overdue or undated).
            untimed.append(f"{t.get('content', '')[:50]} [{t['id']}]")
            continue
        if iv[0].date() != day or iv[1] <= after:
            continue
        if iv[2]:
            no_duration.append(f"{hhmm(iv[0])} {t.get('content', '')[:50]} [{t['id']}]")
        s, e, assumed = iv
        timed.append({"id": t["id"], "t": t.get("content", "")[:50], "s": s, "e": e,
                      "proj": names.get(t.get("projectId"), "?"), "assumed": assumed})
    timed.sort(key=lambda x: x["s"])

    def fmt(x):
        return f"{hhmm(x['s'])}-{hhmm(x['e'])} {x['t']} [{x['id']}]"

    violations, warnings = [], []
    # Every open task on Today needs a start time AND a duration.
    for label in untimed:
        violations.append({"rule": "no_time", "task": label})
    for label in no_duration:
        violations.append({"rule": "no_duration", "task": label})
    meetings = []
    if busy and busy.get("ok"):
        for m in busy.get("meetings", []):
            s = datetime.combine(day, datetime.strptime(m["s"], "%H:%M").time(), TZ)
            e = datetime.combine(day, datetime.strptime(m["e"], "%H:%M").time(), TZ)
            if e > after:
                meetings.append((s, e, m["what"]))
    else:
        warnings.append("calendar not read: meeting overlaps NOT checked")

    for i, a in enumerate(timed):
        for s, e, what in meetings:
            if a["s"] < e and a["e"] > s:
                violations.append({"rule": "overlap_meeting", "task": fmt(a),
                                   "with": f"{hhmm(s)}-{hhmm(e)} {what}"})
        for b in timed[i + 1:]:
            if b["s"] >= a["e"]:
                break
            violations.append({"rule": "overlap_task", "task": fmt(a), "with": fmt(b)})
        if a["proj"] in WORK_PROJECTS and not in_work_window(a["s"], a["e"]):
            violations.append({"rule": "work_outside", "task": fmt(a)})
        if a["proj"] in PERSONAL_PROJECTS and overlaps_work_window(a["s"], a["e"]):
            violations.append({"rule": "personal_inside", "task": fmt(a)})
    return {"ok": not violations, "checked": len(timed), "violations": violations,
            "warnings": warnings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--busy", help="busy_map.py output")
    ap.add_argument("--today")
    ap.add_argument("--projects")
    ap.add_argument("--after", help="HH:MM, default now")
    ap.add_argument("--date", help="YYYY-MM-DD, default today")
    args = ap.parse_args(argv)

    now = datetime.now(TZ)
    day = datetime.fromisoformat(args.date).date() if args.date else now.date()
    after = (datetime.combine(day, datetime.strptime(args.after, "%H:%M").time(), TZ)
             if args.after else now)
    busy = load_json(args.busy) if args.busy else None

    tasks_data, err = (load_json(args.today), None) if args.today else \
        run_json(["td", "today", "--json", "--full", "--all"])
    if err:
        print(json.dumps({"ok": False, "error": f"td today: {err}"}))
        return 2
    proj_data, err = (load_json(args.projects), None) if args.projects else \
        run_json(["td", "project", "list", "--json"])
    if err:
        print(json.dumps({"ok": False, "error": f"td project list: {err}"}))
        return 2

    out = check(results(tasks_data), project_names(proj_data), busy, after, day)
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
