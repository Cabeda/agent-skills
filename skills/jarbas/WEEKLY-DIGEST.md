# Weekly Digest

Report the **actual** delivery / capability / coordination split for a finished week, so the budget set in `MORNING-PLAN.md` step 6 can be checked against what really happened. Use for "weekly digest", "how did my week go", "what was my split last week", `/week`, or a scheduled Friday/Monday run.

This mode **reads and reports only** — it writes no task changes. The one allowed write is an optional append to `state/weekly-digest.json` so the trend builds week over week.

## What this measures vs the morning plan

`MORNING-PLAN.md` step 6 reports the **planned** split for the day ahead. This digest reports the **completed** split for a week behind — plan vs actuals. The gap between them is the signal: a week planned ~63/20/15 that lands 90/5/5 means the backlog ate the capability time, which is exactly the erosion the user asked to see.

## 1. Fix the week window

Default window = the **most recent completed Mon–Sun** relative to today, in the Todoist account timezone (the configured `timezone`). On a Friday or weekend run the user usually means the current week so far; on a Monday run they usually mean the week that just ended. If the phrasing is explicit ("this week", "last week", a date range), honour it. State the exact window in the report.

`td completed list` boundaries are `--since` inclusive, `--until` **exclusive** (the day after the last day). Never pass the same date for both.

```bash
# Example: week Mon 2026-10-13 .. Sun 2026-10-19 inclusive
td completed list --json --full --since 2026-10-13 --until 2026-10-20
```

## 2. Pull the actuals

```bash
td settings view --json          # confirm timezone
td completed list --json --full --since YYYY-MM-DD --until YYYY-MM-DD
```

Each `results[]` entry carries what the split needs:
- `labels` — the bucket (`delivery` / `capability` / `coordination`); may also carry `spike`.
- `completedAt` — UTC ISO timestamp; convert to the account timezone to bucket by local day.
- `duration` — real minutes **when set**; usually `null`.
- `content`, `projectId`, `priority` — for the per-bucket task list and gap surfacing.

Filter to **work tasks only**. Exclude personal projects the same way the morning plan does — the budget is about the paid hours, not personal evening tasks. Keep only tasks whose project is listed in `work_projects` in the config (`scripts/config.py` prints it).

## 3. Compute the split

For each completed work task:
- **Bucket** = its `@delivery` / `@capability` / `@coordination` label. A task with **no bucket label is unmeasured** — do not guess it into a bucket; count it in a separate `unlabelled` tally.
- **Hours** = `duration` when present, else the **30-minute default** (same assumption as the morning plan, so planned and actual use one unit). State this assumption in the report — with durations mostly null, the hour figures are estimates, not a timesheet.

Aggregate:
- Total hours per bucket (`delivery`, `capability`, `coordination`) + `unlabelled`.
- Each bucket's **share of the measured (labelled) total**, so the three shares sum to ~100% independent of the unlabelled tail.
- Count of completed tasks per bucket.
- A per-day mini-view (hours per bucket per weekday) is optional but useful for spotting a run of 100%-delivery days.

Compare against the weekly target frame from `MORNING-PLAN.md` step 6:

| Bucket | Target share | ~hrs/week (40h) |
|---|---:|---:|
| Delivery | ~63% | ~25–26 |
| Capability | ~20–22% | ~8–9 |
| Coordination | ~15% | ~6 |

## 4. Report

```text
Weekly digest — <Mon DD> .. <Sun DD> (<timezone>)
(hours are estimates: duration-when-set, else 30 min/task)

Actual split (of labelled work):
  @delivery      A h   (P%)   N tasks     [target ~63%]
  @capability    B h   (Q%)   N tasks     [target ~20%]
  @coordination  C h   (R%)   N tasks     [target ~15%]
  unlabelled     U h          N tasks     ← not counted in the split

Capability anchor: <your recurring learning block, if you keep one> — ran? (yes/no + the project + its outcome)
Spikes closed:     <@spike tasks completed, with their deliverable/go-no-go if known>

Flags:
  <raise each that applies>
  - capability share well under target (backlog crowded out learning)
  - a run of 100%-delivery days (name them)
  - the capability anchor block did not run
  - large unlabelled tail (split is unreliable until tasks carry labels)

Top delivery items: <a few @delivery tasks, by project>
Top capability items: <the @capability / @spike tasks>
```

Keep it honest: if the labelled sample is tiny (if the bucket labels are new), say the week has little or no labelled history and the figures are indicative, not a verdict. Lead with the number the user cares about — **did capability survive the week** — not a wall of tables.

## 5. Optional trend append

If the user wants the trend tracked, append one record per completed week to `state/weekly-digest.json` next to this skill (create it on first run):

```json
{ "week_start": "2026-10-13", "week_end": "2026-10-19",
  "delivery_h": 0, "capability_h": 0, "coordination_h": 0, "unlabelled_h": 0,
  "delivery_pct": 0, "capability_pct": 0, "coordination_pct": 0,
  "anchor_block_ran": false, "spikes_closed": [], "generated_at": "<UTC ISO>" }
```

Append, never overwrite prior weeks — the point is the month-over-month trend. If the write fails, say so; do not report a trend you could not persist.

**Complete when:** the report names the exact week window, the per-bucket actual hours and shares against target, whether the capability anchor block ran, any unlabelled tail, and the flags — and, if trend tracking was requested, `state/weekly-digest.json` holds the new week's record.
