# Replan Now

Use this focused path whenever the user asks to adjust Todoist times during the day, raise the daily limit, add a task to today's commitment, or adapt when priorities change. Make the smallest requested change and finish with exact verification.

## Commitment changes (limit, add, swap)

Apply the daily commitment model in `SKILL.md`. Re-time affected tasks around the current clock and Calendar; never touch completed or in-progress tasks.

To see the current priority-ordered split (committed / backlog / exempt) at the current limit, reuse the deterministic selector:

```bash
python3 scripts/select_today.py --limit N --format json
```

The next backlog task to promote is the **first** entry of `backlog` (highest priority uncommitted); the candidate to bump on an overflowing swap is the **last** entry of `committed` (lowest priority committed), provided it is not already started or completed.

- **Raise the limit / "add one more" / "I can do more":** increase the daily limit by one (or by the number the user names), then move the next backlog task in strict priority order (p1 → p4, ties by due date then Today order) into the committed set and give it a due time and a duration around current commitments.
- **"add <task name>":** commit that specific task regardless of its priority rank; raise the limit by one to hold it. Give it a due time and a duration.
- **Priority changed / "drop X, do Y" / "something urgent came up":** commit the new task. If that exceeds the current limit, move the **lowest-priority still-incomplete** committed task back to the backlog. A bumped task keeps a start time and a duration: move it to the next free gap after the committed set. Never bump a completed or already-started task. Re-time the remaining committed set.

Report each commitment change as an explicit in ← / out → swap. The limit only changes here on an explicit request; morning planning never raises it.

**Complete when:** the committed set and daily limit match the request, bumped tasks sit in the backlog with a time and duration, and no completed or in-progress task was altered.

## 1. Determine the affected set

Follow the fresh-state rules in `SKILL.md`. Select only:

- tasks named by the user; or
- for “remaining tasks,” active tasks scheduled from now onward.

Preserve completed tasks and elapsed blocks.

Read upcoming Calendar events only when the user asks for a collision-free schedule or the shift depends on free time. An exact instruction such as “move X to 15:30” requires no Calendar pass. When a Calendar read is needed, use the exact `gws calendar events list` command documented in `MORNING-PLAN.md` step 1 (`calendarId` goes inside `--params`).

**Complete when:** the affected task IDs are known and tasks outside that set are marked unchanged.

## 2. Calculate the smallest change

Preserve task order, priority, labels, project, duration, and recurrence unless the request requires a specific change. Keep fixed Calendar commitments fixed. When shifting several tasks, maintain their relative order unless the user says otherwise.

This mode performs no review synchronization, classification, label maintenance, or task creation. It may change the daily limit and the committed set only as described in "Commitment changes" above, on explicit request.

**Complete when:** every affected task has one explicit target datetime and, only if requested, a target duration.

## 3. Write and verify

Apply due-time changes with the recurrence-preserving command:

```bash
td task reschedule id:TASK_ID YYYY-MM-DDT15:30:00 --json
```

Apply explicit duration changes separately:

```bash
td task update id:TASK_ID --duration 45m --json
```

When bumping a task to the backlog, do not clear its time. Move it to the next free gap with `reschedule` and make sure it has a duration. Never use `--no-due`.

Run the shared mutation contract in `SKILL.md` for every affected task. Compare before and after values, including recurrence.

**Complete when:** every requested target is present in re-fetched Todoist data, and no open task on Today lacks a start time or a duration. If no task changed, state why.

## 4. Report

```text
Todoist times adjusted and verified.
Committed changes:
- in ← pX New task (16:00, 45m)
- out → pX Bumped task (now backlog, 17:00, 30m)
Daily limit: 3 → 4
Changed times:
- Task A: 14:00 → 15:30, 45m
- Task B: 15:00 → 16:15, duration unchanged
Preserved: recurrence, priorities, labels, completed tasks
Unchanged: <tasks outside the requested set>
```

Report only verified changes, including every in/out swap and any limit change. A successful command with stale or mismatched re-fetched data is a failed adjustment, not a completed one.
