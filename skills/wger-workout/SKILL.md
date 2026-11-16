---
name: wger-workout
description: "Retrieve the user's today's workout from wger. Use when the user asks for today's routine, training, workout, or wger integration."
metadata:
  version: 1.0.0
  category: health
  requires:
    bins: [curl, jq]
    env: [WGER_API_KEY]
---

# Wger Workout

Retrieve the authenticated user's routine from the wger REST API. Do not invent a workout when the API cannot authenticate.

## Authentication

`WGER_API_KEY` may contain either:
- a JWT access token: send `Authorization: Bearer $WGER_API_KEY`
- a permanent wger API key: send `Authorization: Token $WGER_API_KEY`

Try Bearer first, then Token only when the first request returns 401/403. Never print the token. If both fail, stop and ask the user to mint a new token at wger User settings → API key, then add it to `~/env` as `WGER_API_KEY`.

## Retrieve today's routine

```bash
source ~/env 2>/dev/null
TODAY="$(date +%F)"
BASE='https://wger.de/api/v2'

# Validate auth and list the user's routines.
curl -fsS -H "Accept: application/json" \
  -H "Authorization: Bearer $WGER_API_KEY" \
  "$BASE/routine/?limit=100"

# For each active routine id, request today's sequence.
curl -fsS -H "Accept: application/json" \
  -H "Authorization: Bearer $WGER_API_KEY" \
  "$BASE/routine/<ROUTINE_ID>/date-sequence-display/?start=$TODAY&end=$TODAY"

# Use the routine structure endpoint when the sequence references day/slot ids.
curl -fsS -H "Accept: application/json" \
  -H "Authorization: Bearer $WGER_API_KEY" \
  "$BASE/routine/<ROUTINE_ID>/structure/"
```

Prefer the routine's date-sequence endpoint for “today”; use the structure endpoint to expand the day's slots into exercises, sets, reps, and weights. Show the routine name, day, exercises, prescribed sets/reps, and any notes. If there is no scheduled session today, say so.

## Integration with Todoist Today

When planning the day, read the user's workout task in Todoist if one exists (ask for its name once). If the user asks to move today's workout, use the recurrence-preserving Todoist reschedule command; never destroy the task's recurrence. Keep the workout after the user's work commitments and before dinner unless the user specifies another window.

## Safety

This skill retrieves and schedules the user's existing routine. It must not diagnose injury, prescribe medical treatment, or silently replace a wger routine with generated exercises.

## API reference

- https://wger.readthedocs.io/en/latest/api/api.html
- https://wger.de/api/v2/schema
