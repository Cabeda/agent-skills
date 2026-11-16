#!/usr/bin/env python3
"""Read every accessible Google Calendar for one day and print the busy map.

Replaces one `gws calendar events list` call per calendar. Calendars are read
in parallel; raw event JSON never reaches the model.

Rules (MORNING-PLAN.md step 1):
  - skip calendars listed in `mirror_calendars` (default "todoist", task mirrors)
  - skip transparent, cancelled, declined and workingLocation events
  - all-day events are reported but never busy
  - focus/deep-work blocks (eventType focusTime, or a focus-style title) are
    capacity windows, not busy
  - everything else with a start/end time is a hard busy block

Usage:
  busy_map.py [--date YYYY-MM-DD]
  busy_map.py --fixture calendars.json   # {"calendars": {...}, "events": {id: {...}}}

Exit 0 with ok=true, or exit 2 with ok=false and an error (auth_expired ->
run `gws auth login`).
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

from _common import (
    DAILY_DELIVERY_H, FOCUS_TITLE, MIRROR_CALENDARS, TZ, WORK_END, WORK_START, hhmm,
    load_json, merge, run_json, to_local,
)

FOCUS = FOCUS_TITLE


def gws(args: list[str]):
    return run_json(["gws", "calendar", *args], timeout=45)


def day_bounds(day: date):
    start = datetime.combine(day, datetime.min.time(), TZ)
    return start, start + timedelta(days=1)


def declined(ev: dict) -> bool:
    return any(a.get("self") and a.get("responseStatus") == "declined"
               for a in ev.get("attendees") or [])


def build(day: date, calendars: list[dict], events: dict, errors: dict) -> dict:
    """Pure part: turn calendar list + per-calendar events into the busy map."""
    meetings, all_day, focus, seen = [], [], [], set()
    read, skipped = [], []
    for cal in calendars:
        cid, name = cal["id"], cal.get("summary") or cal["id"]
        if name.strip().lower() in MIRROR_CALENDARS:
            skipped.append(name)
            continue
        if cid in errors:
            continue
        read.append(name)
        for ev in (events.get(cid) or {}).get("items", []):
            if (ev.get("status") == "cancelled" or ev.get("transparency") == "transparent"
                    or ev.get("eventType") == "workingLocation" or declined(ev)):
                continue
            title = (ev.get("summary") or "(no title)")[:60]
            st, en = ev.get("start") or {}, ev.get("end") or {}
            if "dateTime" not in st:
                if st.get("date"):
                    all_day.append({"what": title, "cal": name})
                continue
            s, e = to_local(st["dateTime"]), to_local(en["dateTime"])
            item = {"s": hhmm(s), "e": hhmm(e), "what": title, "cal": name}
            if ev.get("eventType") == "focusTime" or FOCUS.search(title):
                focus.append(item)
                continue
            key = (s, e, title)
            if key in seen:  # same invite visible through two calendars
                continue
            seen.add(key)
            meetings.append((s, e, item))

    meetings.sort(key=lambda m: m[0])
    busy = merge([(s, e) for s, e, _ in meetings])
    ws = datetime.combine(day, WORK_START, TZ)
    we = datetime.combine(day, WORK_END, TZ)
    secs = sum(max(0, (min(e, we) - max(s, ws)).total_seconds()) for s, e in busy)
    meeting_h = round(secs / 3600, 2)
    return {
        "ok": True,
        "date": day.isoformat(),
        "weekday": day.strftime("%a"),
        "calendars_read": len(read),
        "calendars_failed": [{"cal": c, "error": e} for c, e in errors.items()],
        "mirrors_skipped": skipped,
        "meetings": [m for _, _, m in meetings],
        "busy": [f"{hhmm(s)}-{hhmm(e)}" for s, e in busy],
        "focus_blocks": focus,
        "all_day": all_day,
        "meeting_hours": meeting_h,
        "delivery_budget_h": round(max(0.0, DAILY_DELIVERY_H - meeting_h), 2),
    }


def fetch(day: date) -> dict:
    cal_list, err = gws(["calendarList", "list", "--params",
                         json.dumps({"minAccessRole": "reader", "showHidden": True})])
    if err:
        code = "auth_expired" if "invalid_grant" in err else "calendar_list_failed"
        return {"ok": False, "error": code, "detail": err,
                "fix": "gws auth login" if code == "auth_expired" else None}
    calendars = cal_list.get("items", [])
    s, e = day_bounds(day)
    params = {"timeMin": s.isoformat(), "timeMax": e.isoformat(),
              "singleEvents": True, "orderBy": "startTime", "maxResults": 250}

    def one(cal):
        data, err = gws(["events", "list", "--params",
                         json.dumps({**params, "calendarId": cal["id"]})])
        return cal["id"], data, err

    wanted = [c for c in calendars if (c.get("summary") or "").strip().lower() not in MIRROR_CALENDARS]
    events, errors = {}, {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for cid, data, err in pool.map(one, wanted):
            if err:
                errors[cid] = err
            else:
                events[cid] = data
    names = {c["id"]: c.get("summary") or c["id"] for c in calendars}
    out = build(day, calendars, events, errors)
    out["calendars_failed"] = [{"cal": names.get(c, c), "error": e} for c, e in errors.items()]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", help="local date, default today")
    ap.add_argument("--fixture", help="offline input for tests")
    args = ap.parse_args(argv)
    day = date.fromisoformat(args.date) if args.date else datetime.now(TZ).date()
    if args.fixture:
        fx = load_json(args.fixture)
        out = build(day, fx["calendars"], fx.get("events", {}), fx.get("errors", {}))
    else:
        out = fetch(day)
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
