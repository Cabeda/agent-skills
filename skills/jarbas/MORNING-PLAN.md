# Morning Plan

Full-day planning. Todoist is the plan; Calendar supplies busy windows. Scripts do every read and every rule check; you decide times and write them. `<skill>` below is this skill's directory.

Hard rules (from `SKILL.md`, enforced by `check_plan.py`):
- No timed item overlaps a meeting or another timed item.
- Every open task on Today gets a start time and a written duration, backlog included. None stays untimed.
- Tasks in `work_projects` sit inside the configured work window. Tasks in `personal_projects` sit outside it.
- Committed deep work gets the best slots first. Backlog tasks take the gaps that remain.
- All-day events and focus blocks (titles matching `focus_title_regex`) are not busy.

## Hooks

An overlay skill (see `SKILL.md`, "Configuration and overlays") can attach work to four points in this plan: `pre-gather`, `after-gather`, `after-check`, `report`. Each point below says where it runs. If no overlay is configured, skip every "Hook" line.

## 0. Config and hook: pre-gather

```bash
python3 <skill>/scripts/config.py
```

Note `overlays`. **Hook `pre-gather`:** for each overlay, run what its `HOOKS.md` lists under `pre-gather`, for example starting a background job that must finish before the report.

**Complete when:** you know the config and every `pre-gather` hook has started.

## 1. Gather (one call)

```bash
python3 <skill>/scripts/gather.py
```

It reads Todoist, every calendar and every configured extension in parallel, saves raw files under `run_dir`, and prints one summary with these sections:

- `calendar`: `busy` (merged `HH:MM-HH:MM`), `meetings`, `focus_blocks`, `meeting_hours`, `delivery_budget_h`. `ok:false` with `error:auth_expired` means the gws token expired: plan without meetings, keep the hard rules, and tell the user to run `gws auth login`.
- `board`: `committed`, `backlog`, `exempt`, `personal`, `unlabelled_work`. Each row has `id`, `t` (title), `p` (UI priority, 1 = highest), `kind`, `proj`, `due`, `dur`, `rec`.
- `extensions`: one entry per configured extension, keyed by name. The overlay's `HOOKS.md` says what each one means.

If `board.ok` is false, Todoist auth is broken: stop and report. Never write against an unverified account.

Do not re-run `td today` or the calendar reads to re-derive any of this. If a classification is wrong, fix the task's label in Todoist (`quick`), not the split.

**Complete when:** you hold the summary and know which sections failed.

## 2. Hook: after-gather

For each overlay, run what its `HOOKS.md` lists under `after-gather`. Typical use: turn an extension's output into tasks. Tasks created here join the list to place in step 3.

**Complete when:** every `after-gather` hook is done, or none is configured.

## 3. Place times

Free time = the work window minus `calendar.busy`, from now on. Place in this order, each in the earliest free gap that fits, without overlap:

1. `exempt` items already at a sensible time stay put, including `fixed` ones.
2. Tasks added by overlay hooks, in the order the overlay gives.
3. `committed` deep work, in the order given. Prefer `focus_blocks`.
4. Remaining `exempt` quick/routine items. Keep social calls in one block.
5. `personal` tasks: outside the work window.
6. `backlog` tasks, in priority order, in whatever gaps remain.

Give every item a duration too: keep the existing one, else `quick` 10 min, deep work 60 min, other 30 min. When today's gaps run out, use the next free gap as `SKILL.md` describes ("Every task has a start time and a duration") and list those items as "moved past today's gaps". Never leave a task untimed and never stack.

**Complete when:** every open task on Today has a target time and a duration.

## 4. Write and verify

Use the time-write and verify rules in `SKILL.md`: `td task reschedule id:<id> <YYYY-MM-DDTHH:MM:00>`, then `td task update id:<id> --duration <N>m` for any task whose duration is missing or changed, then `td task view id:<id> --json`. For a recurring task, check `due.isRecurring` is still true afterwards; if it flipped, restore it with `td task update id:<id> --due "<original due.string>"`.

Never clear a task's time. Backlog tasks are timed like the rest.

**Complete when:** every written task reads back with the intended time, a duration, and unchanged recurrence.

## 5. Check the plan, then hook: after-check

```bash
python3 <skill>/scripts/check_plan.py --busy <run_dir>/busy.json --projects <run_dir>/projects.json
```

It re-reads Todoist and exits 1 with a `violations` list (`overlap_meeting`, `overlap_task`, `work_outside`, `personal_inside`, `no_time`, `no_duration`). Fix each one by moving the task named in `task` or writing its missing time or duration, then re-run until it exits 0. If `calendar not read` appears in `warnings`, the report must say meetings were not checked.

**Hook `after-check`:** run what each overlay lists, for example saving state that must only be saved once the plan is written.

**Complete when:** `check_plan.py` exits 0 and every `after-check` hook succeeded. If a hook fails, say so in the report.

## 6. Report, with hook: report

```text
Plan written and verified (check_plan: clean).
Calendar: N calendars read · failed: <list or none> · meetings Xh
Committed:  N deep (HH:MM–HH:MM), by priority
Riding along: N quick · N routine · N from overlays
Backlog (timed after committed): <p task HH:MM–HH:MM, ...>
Moved past today's gaps: <list or none>
Untimed: none
Budget: delivery budget Yh (daily_delivery_h − meetings) · planned @delivery Ah @capability Bh @coordination Ch
  Flag: <0h capability, ~100% delivery, unlabelled work tasks>
<one line per overlay, as its HOOKS.md defines>
Changed times: task: old → new
```

The budget lines apply only if you use the `delivery` / `capability` / `coordination` labels; otherwise omit them. Target frame: about 63% delivery, 20% capability, 15% coordination of a 40 h week. Stop delivery when the day's budget is spent, not when the backlog is empty.

Complete the plan-the-day control task after the report is written.
