---
name: jarbas
description: "Plan, time-block, replan, or reorder today's tasks through Todoist and Google Calendar. Use for 'plan my day', 'adjust my task times', 'replan my afternoon', 'move the remaining tasks', 'order today', 'what should I work on first', 'add one more', 'increase my limit', 'weekly digest', 'how did my week go', 'my delivery/capability split', /plan-day, /today, or /week."
metadata:
  version: 2.0.0
  category: productivity
  requires:
    bins: [td, python3, gws]
---

# Jarbas

Keep today's executable plan current in Todoist. Route by intent first, read only that mode's guide, and verify the exact fields the user asked to change.

## Ownership

- **Todoist owns actions:** task due times, durations, priorities, recurrence, and Today order.
- **Calendar owns commitments:** meetings, appointments, shifts, and fixed recurring events.
- Calendar events are read-only availability constraints. Write task changes to Todoist, not Calendar.
- Represent each commitment once: recurring appointments live in Calendar; recurring actions live in Todoist.
- A Todoist task mirrored into Calendar remains a Todoist task. Treat the calendar copy as display-only because a rescheduled occurrence of a recurring task may not sync correctly.

## Configuration and overlays

Nothing personal is hard-coded in this skill. Run `python3 <skill>/scripts/config.py` first: it prints the merged config (`$JARBAS_CONFIG`, else `~/.config/jarbas/config.json`, plus `config.d/*.json`) and whether each file exists. `config.example.json` documents every key. The config sets timezone, daily limit, work window, project names, name patterns for quick/routine tasks, and task rules.

An **overlay** is another skill that adds a data source or rule this skill must not know about, for example a work mailbox. `overlays` in the config lists overlay skill names. For each one, load that skill and read its `HOOKS.md`. Follow its hook at the matching step of the mode you are running. If `overlays` is empty, or a named skill is not installed, skip this and do not mention it. Extension commands in `extensions` run by themselves inside `gather.py`; their output is in `extensions.<name>` of its summary. See [`EXTENSIONS.md`](EXTENSIONS.md) for the contract.

## Route first

Choose the primary mode before fetching data, then read its guide:

| User intent | Mode guide | Scope |
|---|---|---|
| “Plan/triage my day”, “what first?” | [`MORNING-PLAN.md`](MORNING-PLAN.md) | Full triage, availability, committed set within the daily limit, times, and order |
| “Adjust times”, “move the rest”, “replan my afternoon”, “add one more”, “increase my limit”, “add <task>”, “drop X do Y”, priorities changed | [`REPLAN-NOW.md`](REPLAN-NOW.md) | Surgical updates: commitment changes and time shifts to unfinished tasks |
| “Order/reorder today” | [`DAY-ORDER.md`](DAY-ORDER.md) | `dayOrder` only; due times remain unchanged |
| “Weekly digest”, “how did my week go”, “my split last week”, `/week` | [`WEEKLY-DIGEST.md`](WEEKLY-DIGEST.md) | Read-only: actual delivery/capability/coordination split of a finished week vs the budget targets |

Read exactly one primary mode guide. For a mixed request, combine only explicitly requested effects. A time-adjustment request always starts with **Replan now**, never Morning plan. "Add one more", "increase my limit", "add <task>", or any mid-day priority change also starts with **Replan now**, never Morning plan. A "how did my week go" / "weekly split" request is **Weekly digest** — a read-only actuals report, never a planning or write mode.

## Daily commitment model

Today's plan is a small, priority-ordered **committed set** plus always-on exempt buckets.

- **Committed set:** deep-work tasks selected by Todoist priority (p1 highest → p4 default), filling up to the **daily limit**. Ties within a priority level break by earliest due date, then Today order. Committed tasks get the earliest, best slots.
- **Daily limit:** the number of committed deep-work tasks for the day. It **starts at `daily_limit` (default 3)** and only grows when the user asks (see Replan now). Never raise it on your own.
- **Backlog ("Not committed today"):** deep-work tasks beyond the limit. They stay on Today and keep their priority. They are not promised, but they still get a start time and a duration, in the free gaps left after the committed set. Never auto-defer them to a future date.
- **Exempt buckets — `quick` and `routine`:** always ride along and never count against the limit. `quick` = maintenance ≤10 min (label `quick`, `[clarified: quick]`, a duration of 10 min or less, or a name matching `quick_names`). `routine` = recurring admin and social calls (a label in `routine_labels`, a project in `routine_projects`, or a name matching `routine_names`). A recurring task outside `work_projects` that has no labels is also routine. Any other kind you define in `task_rules` is exempt too.

### Every task has a start time and a duration (HARD RULE)
No open task on Today may be left without a start time or without a duration. This covers committed, backlog, `quick`, `routine`, `fixed` and overlay-added tasks, in every mode.

- Write both: `td task reschedule id:<id> <YYYY-MM-DDTHH:MM:00>` for the time and `td task update id:<id> --duration <N>m` for the duration. A duration you assumed (30 min) is not enough: write it to Todoist.
- Estimate a missing duration from the task: `quick` 10 min, deep work 60 min, anything else 30 min. Keep an existing duration unchanged.
- A recurring task keeps its recurrence. Set its time with `reschedule`, never by clearing the due date.
- If the day has no free gap left, place the task in the next free gap anyway: after the work window for a personal task, or at the start of the next working day for a work task. Say so in the report. Do not leave it untimed and do not stack it on top of another item.
- `check_plan.py` reports `no_time` and `no_duration` violations. The plan is not finished until there are none.

### No overlapping events (HARD RULE)
The user cannot multitask, so **no two scheduled items may overlap in time** — not task-on-task, and not task-on-Calendar-meeting. Every timed task must occupy a free gap: its `[start, start+duration)` interval must not intersect any Calendar event's `[start, end)` interval, nor any other timed task's interval. This applies to **every** timed item written by this skill (committed deep work, `quick`, `routine`, and any task an overlay adds alike), in every mode.

- **Only exception: all-day events.** An all-day Calendar event (a date-only span with no start/end time, e.g. an all-day conference) does NOT block any window — tasks may be scheduled freely during it. Every timed Calendar event (a meeting with a real start/end) is a hard busy block.
- **Focus / deep-work blocks are containers, not busy blocks.** A self-owned focus block (a title matching `focus_title_regex`, e.g. "Focus: deep work", "focus time" — a block whose purpose is to hold work, not a meeting with other people) is NOT a busy commitment and does NOT block its window. It is the *target* window for committed deep-work tasks: schedule deep work **inside** it. The no-overlap rule still applies task-on-task within the block (one task at a time, sequential 30-min slots), but a deep-work task landing inside a focus block is expected, not a collision. Treat these blocks as available capacity to fill and aggregate; do not schedule around them as if they were meetings.
- Assume a **30-minute default duration** only while checking collisions. Always write the real or estimated duration to Todoist.
- Fit tasks into the real free gaps between meetings. If there are not enough non-overlapping gaps today, move the overflow to the next free gap as described in "Every task has a start time and a duration", and say in the report that it did not fit today. Never resolve congestion by double-booking, and never by leaving a task untimed.
- When the Calendar cannot be read, you cannot verify non-overlap against meetings: place tasks only in windows you are confident are free, avoid task-on-task overlap regardless, and explicitly flag that the plan was made without a live calendar read.

### Fixed-time tasks
A task whose `task_rules` kind is `fixed` keeps its time and rides along without counting toward the limit. If its time is missing or wrong, restore it with `td task update id:<id> --due "<recurrence at HH:MM>"` so the recurrence is preserved, then verify. A fixed-time task still obeys the no-overlap rule: if a meeting sits on it, keep the recurrence and flag the collision rather than double-booking.

Ask a question only when ambiguity prevents a safe write. Consolidate all blocking ambiguities into one message. When the user supplied exact tasks and times, execute directly.

## Scripts

Deterministic work lives in `scripts/` (stdlib Python, tests in `tests/`, run `python3 -m unittest discover -s tests`). Prefer a script over re-deriving its logic in prose.

| Script | Does |
|---|---|
| `config.py` | Prints the merged config and overlay list |
| `gather.py` | All morning reads and configured extensions in parallel; one compact summary |
| `busy_map.py` | Every calendar, mirrors/transparent/declined skipped, merged busy blocks, meeting hours |
| `select_today.py` | committed / backlog / exempt / personal split |
| `check_plan.py` | Fails on overlaps and work-hour violations |

## Shared mutation contract

### Fresh state

Fetch immediately before calculating changes:

```bash
td settings view --json
td today --json --full --all
```

Use the Todoist account timezone. Include only active tasks (`checked=false`, `isDeleted=false`) for planning. Keep a before-state for every field that may change. Re-fetch immediately before a write batch if the user may have changed or completed tasks meanwhile.

### Status reads

A Today view is active-only; it is not a completion report. For any status, progress, or “am I getting everything done?” request, fetch both active and completed records:

```bash
td today --json --full --all
td completed list --json --full
```

The completed-list command defaults to today. For an explicit date, use `--since YYYY-MM-DD --until NEXT-YYYY-MM-DD`, where the end boundary is the following calendar date and is exclusive. Never use the same date for `--since` and `--until`. Count completed tasks from `completedAt` in the Todoist account timezone, and report active and completed tasks separately; never infer zero completions from an empty Today result.

### Time writes

Use the recurrence-preserving command with an explicit local datetime:

```bash
td task reschedule id:TASK_ID YYYY-MM-DDT15:30:00 --json
td task update id:TASK_ID --duration 45m --json
```

Replace `YYYY-MM-DD` with the requested local calendar date before executing.

`td task reschedule` takes the date as a positional argument. Use an explicit date rather than `tomorrow`. Change duration only when requested or required by an agreed time block.

For recurring tasks, preserve and verify the recurrence expression. Rescheduling an occurrence in Todoist does not imply that its mirrored recurring Calendar event changed.

### Verify writes

After writing, fetch each affected task by ID:

```bash
td task view id:TASK_ID --json --full
```

A mutation is complete only when the re-fetched task proves all applicable conditions:

- task ID is the intended task;
- `due.date` (local, `YYYY-MM-DDTHH:MM:SS`) matches the requested date and time;
- duration matches the requested value;
- recurrence is unchanged unless the user requested a recurrence change;
- priority, labels, project, and completion state are unchanged unless requested;
- `dayOrder` matches the requested order when ordering was requested.

If any condition fails, correct it or report the exact mismatch. Command success alone is not completion.
