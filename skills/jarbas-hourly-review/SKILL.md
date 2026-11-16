---
name: jarbas-hourly-review
description: "Review personal progress hourly and recommend the next best action, deferrals, or workflow improvements. Use for hourly reviews, progress checks, or 'what should I improve next?'"
metadata:
  version: 1.0.0
  category: productivity
  requires:
    bins: [td, gws]
---

# Jarbas Hourly Review

Review the current plan against reality and produce a small, actionable recommendation. This skill reads your own Todoist and Calendar state and leaves a narrow seam for an optional read-only snapshot from another domain, such as work.

## When to use

Use for an hourly check-in, “am I on track?”, “what should I do next?”, or a request to identify recurring workflow failures. Use `jarbas` for actual Todoist time, order, or completion mutations.

## Procedure

1. Read the current local state:
   - active Todoist Today tasks;
   - completed Todoist tasks for today;
   - current time and account timezone;
   - remaining Calendar commitments and available windows.
2. If a snapshot gateway is configured and available, read only its sanitized snapshot. If it is unavailable or unconfigured, label that domain's state **unknown** rather than assuming nothing is pending.
3. Classify the result:
   - completed since the previous review;
   - on track;
   - at risk;
   - blocked;
   - no longer relevant.
4. Recommend at most three actions, ordered by leverage:
   - the next concrete action;
   - one task to defer, simplify, or clarify if capacity is tight;
   - one workflow improvement when a repeated failure is evidenced.
5. Report the sources used and the data that was unavailable.

## Output

```text
Jarbas hourly review — <time> <timezone>

Done: <observable completed work>
At risk: <task or constraint, or “none known”>
Next: <one concrete action and why>
Adjust: <optional deferral/simplification>
Improve: <optional evidence-based workflow or skill proposal>
Sources: Todoist, Calendar, <snapshot or “snapshot unavailable”>
```

Keep the review concise. Do not produce a notification when nothing changed and no action is needed.

## Snapshot gateway seam

The gateway is an optional read-only adapter with a small interface:

```text
get_snapshot() -> sanitized snapshot
```

The adapter may expose statuses, assigned reviews, blockers, deadlines, and links. It must keep its own credentials on its own side, expose no arbitrary shell, and return only the minimum approved data. This skill does not install, configure, or call a gateway until the user explicitly enables it.

## Security and write policy

- Treat each data domain (personal, work) as separate.
- Do not copy raw documents from another domain, comments, tokens, or credentials into personal memory or logs.
- Fail closed: unavailable data is unknown, never evidence that the work is complete.
- Recommendations are proposals. Do not reschedule Todoist tasks, edit work systems, or modify skills during an hourly review without explicit approval.
- A proposed skill improvement must include the observed failure, the smallest change, and a verification plan.

## Verification

A review is complete only when it names the timestamp/timezone, separates active from completed work, distinguishes known from unknown state, cites the sources used, and ends with a concrete next action or explicitly states that no action is needed.
