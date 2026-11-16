"""Shared helpers for the jarbas scripts (stdlib only).

Times: Todoist due datetimes are floating local times; Calendar times carry an
offset. Everything is converted to the configured timezone before comparing.

Configuration is layered JSON, never edited in this skill:

  $JARBAS_CONFIG or ~/.config/jarbas/config.json    your base config
  <same dir>/config.d/*.json                        overlays, merged in name order

Dicts merge recursively, lists concatenate, scalars from later files win. In an
overlay file, the string "{here}" expands to that file's real directory, so an
overlay skill can point at its own scripts. See config.example.json.
"""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULTS = {
    "timezone": "UTC",
    "daily_limit": 3,
    "daily_delivery_h": 5.0,
    "work_window": {"start": "09:00", "end": "18:00", "days": [0, 1, 2, 3, 4]},
    "work_projects": [],          # tasks here must sit inside the work window
    "personal_projects": [],      # tasks here must sit outside the work window
    "routine_projects": [],       # every task here is routine
    "routine_labels": ["routine"],  # a task with any of these labels is routine
    "quick_names": [],            # regexes: maintenance tasks, <=10 min
    "routine_names": [],          # regexes: recurring admin, social calls
    "task_rules": [],             # [{"regex": ..., "kind": ...}], first match wins
    "focus_title_regex": r"(\bfocus\b|deep[ -]?work)",
    "mirror_calendars": ["todoist"],
    "overlays": [],               # skill names whose HOOKS.md the plan must follow
    "extensions": [],             # [{"name": ..., "cmd": [...]}] run by gather.py
}


def _merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = _merge(a[k], v) if k in a else copy.deepcopy(v)
        return out
    if isinstance(a, list) and isinstance(b, list):
        return a + [x for x in b if x not in a]
    return copy.deepcopy(b)


def _expand_here(value, here: str):
    if isinstance(value, str):
        return value.replace("{here}", here)
    if isinstance(value, list):
        return [_expand_here(v, here) for v in value]
    if isinstance(value, dict):
        return {k: _expand_here(v, here) for k, v in value.items()}
    return value


def config_paths() -> list[Path]:
    base = Path(os.environ.get("JARBAS_CONFIG") or Path.home() / ".config" / "jarbas" / "config.json")
    return [base, *sorted((base.parent / "config.d").glob("*.json"))]


def load_config() -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    for path in config_paths():
        if not path.exists():
            continue
        here = str(path.resolve().parent)
        cfg = _merge(cfg, _expand_here(json.loads(path.read_text(encoding="utf-8")), here))
    return cfg


CONFIG = load_config()
TZ = ZoneInfo(os.environ.get("JARBAS_TZ") or CONFIG["timezone"])
WORK_START = time.fromisoformat(CONFIG["work_window"]["start"])
WORK_END = time.fromisoformat(CONFIG["work_window"]["end"])
WORK_DAYS = set(CONFIG["work_window"]["days"])
DEFAULT_MIN = 30
DAILY_DELIVERY_H = float(CONFIG["daily_delivery_h"])

WORK_PROJECTS = set(CONFIG["work_projects"])
PERSONAL_PROJECTS = set(CONFIG["personal_projects"])
ROUTINE_PROJECTS = set(CONFIG["routine_projects"])
ROUTINE_LABELS = {l.lower() for l in CONFIG["routine_labels"]}
BUCKETS = ("delivery", "capability", "coordination")


def run_json(cmd: list[str], timeout: int = 60):
    """Run a CLI that prints JSON. Returns (data, None) or (None, error).

    Leading non-JSON lines (glab upgrade banners, keyring notices) are skipped.
    """
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    out = p.stdout
    starts = [i for i in (out.find("{"), out.find("[")) if i >= 0]
    if p.returncode != 0 or not starts:
        err = (p.stderr or out).strip().splitlines()
        return None, (err[-1] if err else f"exit {p.returncode}")[:300]
    try:
        return json.loads(out[min(starts):]), None
    except json.JSONDecodeError as exc:
        return None, f"bad JSON: {exc}"


def results(data):
    """td returns {"results": [...]}; accept a bare list too."""
    if isinstance(data, dict):
        return data.get("results", [])
    return data or []


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def to_local(value: str) -> datetime:
    """Parse an ISO datetime; naive values are taken as local."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt.astimezone(TZ)


def hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def task_due(task: dict):
    """Return (local datetime or None, date or None) for a task's due."""
    due = task.get("due") or {}
    raw = due.get("datetime") or due.get("date")
    if not raw:
        return None, None
    if "T" in raw:
        dt = to_local(raw)
        return dt, dt.date()
    return None, date.fromisoformat(raw[:10])


def duration_min(task: dict):
    d = task.get("duration") or {}
    if not d.get("amount"):
        return None
    return d["amount"] * (1440 if d.get("unit") == "day" else 1)


def task_interval(task: dict):
    """(start, end, assumed) for a timed task, else None. 30 min default."""
    start, _ = task_due(task)
    if start is None:
        return None
    mins = duration_min(task)
    return start, start + timedelta(minutes=mins or DEFAULT_MIN), mins is None


def ui_priority(api_priority: int) -> int:
    """Todoist API priority 4 is UI p1."""
    return 5 - int(api_priority or 1)


def in_work_window(start: datetime, end: datetime) -> bool:
    day0 = start.replace(hour=0, minute=0, second=0, microsecond=0)
    return (start.weekday() in WORK_DAYS
            and start >= day0.replace(hour=WORK_START.hour, minute=WORK_START.minute)
            and end <= day0.replace(hour=WORK_END.hour, minute=WORK_END.minute))


def overlaps_work_window(start: datetime, end: datetime) -> bool:
    if start.weekday() not in WORK_DAYS:
        return False
    day0 = start.replace(hour=0, minute=0, second=0, microsecond=0)
    ws = day0.replace(hour=WORK_START.hour, minute=WORK_START.minute)
    we = day0.replace(hour=WORK_END.hour, minute=WORK_END.minute)
    return start < we and end > ws


def merge(intervals):
    """Merge [(start, end), ...] into sorted, non-overlapping intervals."""
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def project_names(projects_data) -> dict:
    return {p["id"]: p["name"] for p in results(projects_data)}


def _any(patterns: list[str]):
    """One case-insensitive regex from many, or one that never matches."""
    return re.compile("|".join(f"(?:{p})" for p in patterns) if patterns else r"(?!x)x", re.I)


QUICK_NAME = _any(CONFIG["quick_names"])
ROUTINE_NAME = _any(CONFIG["routine_names"])
TASK_RULES = [(re.compile(r["regex"], re.I), r["kind"]) for r in CONFIG["task_rules"]]
CONTROL_NAME = re.compile(r"^plan (the|my) day", re.I)
CLARIFIED_QUICK = re.compile(r"\[clarified[^\]]*:\s*quick\]", re.I)
FOCUS_TITLE = re.compile(CONFIG["focus_title_regex"], re.I)
MIRROR_CALENDARS = {c.strip().lower() for c in CONFIG["mirror_calendars"]}
