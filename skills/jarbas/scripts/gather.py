#!/usr/bin/env python3
"""Run every morning-plan read in one call and print one compact summary.

Steps (parallel where independent):
  1. td today --json --full --all   + td project list --json
  2. busy_map.py | select_today.py --today | every configured extension

Each raw output is saved under --out so check_plan.py and the agent can
re-read a single file instead of re-fetching. Only the summaries are printed.

Extensions come from the `extensions` list in the jarbas config (see
_common.py). Each is {"name": "...", "cmd": [...]}; the command must print one
JSON object. Placeholders in cmd: {date} {today} {projects} {out}. Its result
is printed under extensions.<name> and saved to <out>/<name>.json. Extensions
run only after Todoist was read, because they may need today.json.

Usage:
  gather.py [--out DIR] [--limit 3] [--date YYYY-MM-DD]

DIR defaults to $JARBAS_SCRATCH/jarbas/<date> (else $TMPDIR/jarbas/<date>). Exit 0 even
when one source fails: its section carries ok=false and the error, so the
plan can go ahead and flag the gap.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from _common import CONFIG, TZ

HERE = Path(__file__).resolve().parent
PY = sys.executable


def run(cmd: list[str], out_file: Path | None = None, timeout: int = 180) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s: {' '.join(cmd[:3])}"}
    if out_file is not None:
        out_file.write_text(p.stdout, encoding="utf-8")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        tail = (p.stderr or p.stdout).strip().splitlines()
        return {"ok": False, "error": (tail[-1] if tail else f"exit {p.returncode}")[:300]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out")
    ap.add_argument("--limit", default=os.environ.get("JARBAS_DAILY_LIMIT") or str(CONFIG["daily_limit"]))
    ap.add_argument("--date")
    args = ap.parse_args(argv)

    day = args.date or datetime.now(TZ).date().isoformat()
    base = os.environ.get("JARBAS_SCRATCH") or tempfile.gettempdir()
    out = Path(args.out or Path(base) / "jarbas" / day)
    out.mkdir(parents=True, exist_ok=True)
    today, projects = out / "today.json", out / "projects.json"

    summary = {"run_dir": str(out), "date": day, "now": datetime.now(TZ).strftime("%H:%M")}
    exts = CONFIG["extensions"]
    with ThreadPoolExecutor(max_workers=5 + len(exts)) as pool:
        # Calendar does not depend on Todoist, so it runs alongside everything.
        f_busy = pool.submit(run, [PY, str(HERE / "busy_map.py"), "--date", day], out / "busy.json")
        f_today = pool.submit(run, ["td", "today", "--json", "--full", "--all"], today)
        f_proj = pool.submit(run, ["td", "project", "list", "--json"], projects)
        if "results" in f_today.result() and "results" in f_proj.result():
            subst = {"date": day, "today": str(today), "projects": str(projects), "out": str(out)}
            f_ext = {e["name"]: pool.submit(
                         run, [os.path.expanduser(a.format(**subst)) for a in e["cmd"]],
                         out / f"{e['name']}.json")
                     for e in exts}
            f_sel = pool.submit(run, [PY, str(HERE / "select_today.py"), "--today", str(today),
                                      "--projects", str(projects), "--limit", str(args.limit)],
                                out / "select.json")
            summary["board"] = f_sel.result()
            summary["extensions"] = {n: f.result() for n, f in f_ext.items()}
        else:
            err = {"ok": False, "error": "td read failed; fix Todoist auth before any write"}
            summary["board"] = err
            summary["extensions"] = {e["name"]: err for e in exts}
        summary["calendar"] = f_busy.result()

    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
