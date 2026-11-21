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
| [`review-loop`](skills/review-loop) | Review, fix and re-review a branch or draft MR until a clean round. |
| [`codebase-audit`](skills/codebase-audit) | Read-only daily audit of a repo: run the experts, skip already-filed findings, file the rest as proposed tickets. |
| [`expert-review`](skills/expert-review) | Review a change or a codebase through expert lenses. Add an expert by adding one file. |
| [`dependency-update`](skills/dependency-update) | Update dependencies safely, one draft PR per update, under a release-age and pinning policy. |
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

These skills compose, and each also runs on its own:

- `expert-review` runs one or more experts on a change or a whole codebase, and returns findings with a fingerprint each. The experts live in [`skills/expert-review/experts/`](skills/expert-review/experts): security, tests, reliability, performance, dependencies, frontend design and accessibility. Add one by adding a file; see [`ADDING-EXPERTS.md`](skills/expert-review/ADDING-EXPERTS.md).
- `review-loop` reviews a branch or MR, fixes what reviewers find, and repeats until a clean round. Its reviewers are `expert-review`, [`code-review`](https://github.com/mattpocock/skills), and the MR's review bot when the repo documents one.
- `codebase-audit` is the read-only daily run: it reviews a whole repo with `expert-review`, drops findings already filed, and hands the rest to [`to-tickets`](https://github.com/mattpocock/skills) as proposed tickets.
- `dependency-update` applies dependency updates as draft PRs. The `dependencies` expert reports against its policy, so an audit finds what is out of date and `dependency-update` fixes it.

Some experts load a skill from another repo, installed on first use. Install the Matt Pocock skills alongside: `npx skills add mattpocock/skills --skill code-review --skill to-tickets -g`.

## Configuration

Skills read their settings from environment variables or a config file. Nothing personal is stored here. `jarbas` documents its config in [`skills/jarbas/config.example.json`](skills/jarbas/config.example.json) and its extension points in [`skills/jarbas/EXTENSIONS.md`](skills/jarbas/EXTENSIONS.md).

## Adding a skill

Create `skills/<name>/SKILL.md` with `name` and `description` frontmatter. Before you publish, search the file **and the git history** for names, IDs, hostnames and tokens that belong to you or an employer. Anything private goes in a separate private skill, loaded through an overlay.

## License

MIT
