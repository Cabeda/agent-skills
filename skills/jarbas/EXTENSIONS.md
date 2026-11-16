# Extensions and overlays

This skill knows nothing about your employer, mailbox or repositories. Anything like that lives in a separate **overlay skill** that you keep private. The core and the overlay meet at two seams.

## 1. Extension commands (data)

In the config, `extensions` lists commands that `gather.py` runs after it has read Todoist:

```json
{ "extensions": [ { "name": "mr", "cmd": ["python3", "{here}/scripts/mr_sync.py", "diff", "--today", "{today}"] } ] }
```

- The command must print **one JSON object** on stdout. It should include `"ok": true|false`.
- Placeholders: `{date}` (YYYY-MM-DD), `{today}` (saved `td today` JSON), `{projects}` (saved `td project list` JSON), `{out}` (run directory). In a `config.d/*.json` overlay file, `{here}` is the file's real directory.
- A failure must not stop the plan: `gather.py` reports `{"ok": false, "error": ...}` under `extensions.<name>`.
- The result is saved to `<run_dir>/<name>.json`.

## 2. Hooks (instructions)

`overlays` in the config lists skill names. Each overlay skill ships a `HOOKS.md` with one section per hook point:

| Hook point | Mode | Runs |
|---|---|---|
| `pre-gather` | Morning plan, step 0 | Before the reads. Start anything slow or parallel. |
| `after-gather` | Morning plan, step 2 | After the summary. Turn extension output into tasks. |
| `after-check` | Morning plan, step 5 | After `check_plan.py` exits 0. Persist state. |
| `report` | Morning plan, step 6 | Add lines to the report. |

An overlay can also add `task_rules`, `work_projects` and more through its own `config.d` file. Config layering is described in `scripts/_common.py`.

## 3. Rules for overlays

- An overlay must be optional. If it is missing, the core plan must still work and say nothing about it.
- An overlay obeys every hard rule in `SKILL.md`, including no overlaps.
- Do not copy private data into this skill, its config example or its tests.
