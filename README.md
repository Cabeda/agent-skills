# agent-skills

Personal agent skills, published for [skills.sh](https://skills.sh). Each folder under `skills/` is one skill with a `SKILL.md`.

| Skill | What it does |
|---|---|
| [`jarbas`](skills/jarbas) | Plan, time-block, replan and review your day in Todoist and Google Calendar. Config-driven, with overlay hooks. |
| [`jarbas-hourly-review`](skills/jarbas-hourly-review) | Hourly progress check and next-action recommendation. |
| [`anytype`](skills/anytype) | Read and write a local Anytype vault over its HTTP API. |
| [`gamenative`](skills/gamenative) | Drive GameNative (Wine on Android) over `adb`. |
| [`listen-once`](skills/listen-once) | Write explanations that work when heard once. |
| [`meal-planner`](skills/meal-planner) | Plan meals from Notion recipes and put them on Google Calendar. |
| [`review-loop`](skills/review-loop) | Review, fix and re-review a branch, draft MR or whole codebase until no issues are found. |
| [`expert-review`](skills/expert-review) | Review a diff through chosen expert lenses. Add an expert by adding one file. |
| [`tmdb`](skills/tmdb) | Look up movies and TV shows with the TMDB CLI. |
| [`wger-workout`](skills/wger-workout) | Fetch today's routine from wger. |

## Install

```bash
# Everything, for the agents installed on this machine
npx skills add Cabeda/agent-skills --skill '*' -g -y

# One skill, one agent
npx skills add Cabeda/agent-skills --skill jarbas -g -a kiro-cli

# Hermes
npx skills add Cabeda/agent-skills --skill '*' -g -a hermes-agent -y

# Try one without installing
npx skills use Cabeda/agent-skills@jarbas
```

Update with `npx skills update -g`.

## Review skills

`review-loop` runs reviewers, fixes what they find, and re-requests review until a round comes back clean. Its reviewers are other skills, and each one also runs on its own:

- [`code-review`](https://github.com/mattpocock/skills) from Matt Pocock's skills, for standards and fit to the spec. Install it alongside: `npx skills add mattpocock/skills --skill code-review -g`.
- `expert-review`, for focused lenses. The experts live in [`skills/expert-review/experts/`](skills/expert-review/experts). Add one by copying a file there and editing its `use-when` line; the loop picks experts by that line.
- The MR's own review bot, when the repo has one. Document how to trigger it in the repo's `AGENTS.md` or `CONTRIBUTING.md`, and the loop uses it.

## Configuration

Skills read their settings from environment variables or a config file. Nothing personal is stored here. `jarbas` documents its config in [`skills/jarbas/config.example.json`](skills/jarbas/config.example.json) and its extension points in [`skills/jarbas/EXTENSIONS.md`](skills/jarbas/EXTENSIONS.md).

## Adding a skill

Create `skills/<name>/SKILL.md` with `name` and `description` frontmatter. Before you publish, search the file **and the git history** for names, IDs, hostnames and tokens that belong to you or an employer. Anything private goes in a separate private skill, loaded through an overlay.

## License

MIT
