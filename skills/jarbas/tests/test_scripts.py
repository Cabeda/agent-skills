"""Offline tests for the jarbas scripts. Run: python3 -m unittest discover -s tests"""

import json
import os
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["JARBAS_CONFIG"] = str(HERE / "config.test.json")
sys.path.insert(0, str(HERE.parent / "scripts"))

import busy_map  # noqa: E402
import check_plan  # noqa: E402
import _common  # noqa: E402
import select_today  # noqa: E402
from _common import TZ  # noqa: E402

DAY = date(2026, 11, 13)  # a Friday
NAMES = {"W": "Work", "P": "Projects", "I": "Inbox", "S": "Social"}  # ids -> project names


def task(tid, content, proj="W", due=None, dur=None, prio=1, labels=(), rec=False, desc=""):
    t = {"id": tid, "content": content, "projectId": proj, "priority": prio,
         "labels": list(labels), "description": desc, "checked": False,
         "isDeleted": False, "dayOrder": -1}
    if due:
        t["due"] = {"date": due, "isRecurring": rec}
    if dur:
        t["duration"] = {"amount": dur, "unit": "minute"}
    return t


class SelectToday(unittest.TestCase):
    def test_classify_buckets(self):
        cases = {
            "close work": ("close work", "W", {}),
            "ticket": ("Triage ticket #635", "W", {}),
            "quick": ("Meditate", "I", {"labels": ["quick"]}),
            "routine": ("Friday lunch exercise - legs", "I", {}),
            "personal": ("Map the apartment", "P", {}),
            "social": ("Call grandma", "S", {}),
            "deep": ("Draft design doc", "W", {}),
        }
        for want, (content, proj, kw) in cases.items():
            kind = select_today.classify(task("x", content, proj, **kw), NAMES[proj])
            expect = {"close work": "fixed", "social": "routine"}.get(want, want)
            self.assertEqual(kind, expect, content)

    def test_clarified_quick_with_date(self):
        t = task("x", "Call mom", "I", desc="[clarified 2026-06-19: quick]")
        self.assertEqual(select_today.classify(t, "Inbox"), "quick")

    def test_recurring_untagged_personal_admin_is_routine(self):
        t = task("x", "withdraw cash", "I", due="2026-11-13T19:45:00", dur=15, rec=True)
        self.assertEqual(select_today.classify(t, "Inbox"), "routine")

    def test_limit_fills_by_ui_priority(self):
        tasks = [task("a", "deep a", prio=1), task("b", "deep b", prio=4),
                 task("c", "deep c", prio=2), task("d", "deep d", prio=3)]
        out = select_today.select(tasks, NAMES, limit=2)
        self.assertEqual([r["id"] for r in out["committed"]], ["b", "d"])
        self.assertEqual([r["p"] for r in out["committed"]], [1, 2])
        self.assertEqual([r["id"] for r in out["backlog"]], ["c", "a"])

    def test_unlabelled_work_reported(self):
        out = select_today.select([task("a", "deep a"), task("b", "deep b", labels=["delivery"])],
                                  NAMES, 3)
        self.assertEqual(out["unlabelled_work"], ["a"])


def ev(summary, s, e, **kw):
    return {"summary": summary, "start": {"dateTime": s}, "end": {"dateTime": e}, **kw}


class BusyMap(unittest.TestCase):
    def setUp(self):
        self.cals = [{"id": "primary", "summary": "me"}, {"id": "t1", "summary": "Todoist"},
                     {"id": "work", "summary": "Calendar"}]

    def test_rules(self):
        events = {
            "primary": {"items": [
                ev("1:1", "2026-11-13T15:30:00Z", "2026-11-13T16:00:00Z"),
                ev("Hidden", "2026-11-13T10:00:00Z", "2026-11-13T11:00:00Z", transparency="transparent"),
                ev("Declined", "2026-11-13T11:00:00Z", "2026-11-13T12:00:00Z",
                   attendees=[{"self": True, "responseStatus": "declined"}]),
                ev("🔧 Project block", "2026-11-13T14:00:00Z", "2026-11-13T17:00:00Z"),
                {"summary": "Support", "start": {"date": "2026-11-13"}, "end": {"date": "2026-11-14"}},
            ]},
            "work": {"items": [
                ev("Handover", "2026-11-13T14:30:00Z", "2026-11-13T15:45:00Z"),
                ev("1:1", "2026-11-13T15:30:00Z", "2026-11-13T16:00:00Z"),  # duplicate invite
            ]},
            "t1": {"items": [ev("a task", "2026-11-13T09:00:00Z", "2026-11-13T10:00:00Z")]},
        }
        out = busy_map.build(DAY, self.cals, events, {})
        self.assertEqual(out["mirrors_skipped"], ["Todoist"])
        self.assertEqual(out["busy"], ["14:30-16:00"])  # Lisbon is UTC in November
        self.assertEqual(len(out["meetings"]), 2)
        self.assertEqual(out["meeting_hours"], 1.5)
        self.assertEqual(out["delivery_budget_h"], 3.5)
        self.assertEqual(len(out["focus_blocks"]), 1)
        self.assertEqual(out["all_day"][0]["what"], "Support")

    def test_failed_calendar_listed(self):
        out = busy_map.build(DAY, self.cals, {}, {"work": "403"})
        self.assertEqual(out["calendars_failed"], [{"cal": "work", "error": "403"}])
        self.assertEqual(out["calendars_read"], 1)


class Config(unittest.TestCase):
    def test_layers_merge_and_expand_here(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "config.json"
            base.write_text(json.dumps({"work_projects": ["Work"], "daily_limit": 2}))
            (Path(d) / "config.d").mkdir()
            (Path(d) / "config.d" / "work.json").write_text(json.dumps({
                "work_projects": ["Work", "Other"], "overlays": ["x"],
                "extensions": [{"name": "e", "cmd": ["{here}/run.py"]}]}))
            old = os.environ["JARBAS_CONFIG"]
            os.environ["JARBAS_CONFIG"] = str(base)
            try:
                cfg = _common.load_config()
            finally:
                os.environ["JARBAS_CONFIG"] = old
        self.assertEqual(cfg["work_projects"], ["Work", "Other"])
        self.assertEqual(cfg["daily_limit"], 2)
        self.assertEqual(cfg["overlays"], ["x"])
        self.assertEqual(cfg["extensions"][0]["cmd"], [str(Path(d).resolve() / "config.d") + "/run.py"])
        self.assertEqual(cfg["timezone"], "UTC")  # default survives

    def test_empty_config_never_matches(self):
        self.assertIsNone(_common._any([]).search("anything"))


class CheckPlan(unittest.TestCase):
    BUSY = {"ok": True, "meetings": [{"s": "14:30", "e": "15:15", "what": "Handover"}]}
    AFTER = datetime(2026, 11, 13, 8, 0, tzinfo=TZ)

    def run_check(self, tasks, busy=BUSY):
        return check_plan.check(tasks, NAMES, busy, self.AFTER, DAY)

    def rules(self, out):
        return sorted(v["rule"] for v in out["violations"])

    def test_clean(self):
        out = self.run_check([task("a", "x", due="2026-11-13T10:00:00", dur=30),
                              task("b", "y", due="2026-11-13T10:30:00", dur=30),
                              task("c", "z", "P", due="2026-11-13T19:00:00", dur=30)])
        self.assertTrue(out["ok"], out)

    def test_each_rule(self):
        out = self.run_check([
            task("a", "meeting clash", due="2026-11-13T14:45:00", dur=30),
            task("b", "t1", due="2026-11-13T10:00:00", dur=45),
            task("c", "t2", due="2026-11-13T10:30:00", dur=15),
            task("d", "late work", due="2026-11-13T18:45:00", dur=30),
            task("e", "personal at noon", "P", due="2026-11-13T12:00:00", dur=30),
        ])
        self.assertEqual(self.rules(out), ["overlap_meeting", "overlap_task", "personal_inside",
                                           "work_outside"])

    def test_missing_duration_and_time_are_violations(self):
        after = datetime(2026, 11, 13, 11, 0, tzinfo=TZ)
        out = check_plan.check([task("a", "old", due="2026-11-13T10:00:00", dur=30),
                                task("b", "old2", due="2026-11-13T10:15:00", dur=30),
                                task("c", "nodur", due="2026-11-13T12:00:00"),
                                task("d", "next", due="2026-11-13T12:15:00", dur=15),
                                task("e", "dateonly", due="2026-11-13"),
                                task("f", "undated")],
                               NAMES, self.BUSY, after, DAY)
        # Past tasks are ignored; 30m default still catches the c/d overlap.
        self.assertEqual(self.rules(out), ["no_duration", "no_time", "no_time", "overlap_task"])

    def test_no_calendar_warns(self):
        out = self.run_check([], busy={"ok": False})
        self.assertIn("calendar not read", out["warnings"][0])


if __name__ == "__main__":
    unittest.main()
