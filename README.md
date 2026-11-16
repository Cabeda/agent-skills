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

## Configuration

Skills read their settings from environment variables or a config file. Nothing personal is stored here. `jarbas` documents its config in [`skills/jarbas/config.example.json`](skills/jarbas/config.example.json) and its extension points in [`skills/jarbas/EXTENSIONS.md`](skills/jarbas/EXTENSIONS.md).

## Adding a skill

Create `skills/<name>/SKILL.md` with `name` and `description` frontmatter. Before you publish, search the file **and the git history** for names, IDs, hostnames and tokens that belong to you or an employer. Anything private goes in a separate private skill, loaded through an overlay.

## License

MIT
