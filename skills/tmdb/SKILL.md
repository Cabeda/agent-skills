---
name: tmdb
description: "Search movies and TV shows with the `npx @lorenzopant/tmdb` CLI: look up TMDB ids, ratings, cast, release info, trending and discover titles, and list a series' seasons and episode counts to spot missing seasons. Use when the user asks about a movie or show, wants a title's TMDB id, or asks which seasons/episodes a series has."
metadata:
  version: 1.0.0
  category: media
  requires:
    bins: [npx, jq]
---

# TMDB — movie & TV search CLI

`@lorenzopant/tmdb` ships a read-only `tmdb` CLI. It covers **search, movie, tv, person, trending, discover, config** — there is no season/episode subcommand, so episode-level data comes from `tv <id> --json` (season numbers + episode counts only).

## Credential (assume configured)

The CLI resolves the token in this order: `--token` > `TMDB_BEARER_TOKEN` > `TMDB_API_KEY` > config file. Check without leaking it:

```bash
npx -y @lorenzopant/tmdb config get   # prints path + masked credential, or "not set"
```

If it says "not set", stop and ask the user for a TMDB API Read Access Token. Do not paste tokens into output.

## Token efficiency (most important)

- The **default output is a compact table/summary** — use it for browsing. It is already the cheapest option.
- `--json` prints the **entire raw TMDB payload** (kilobytes). Never read it raw. Always filter with `jq -c` and select only the fields you need, then slice (`[:5]`).
- Prefer `--type movie|tv` over `multi` when you know what you want — smaller, cleaner results.
- One `search` call to get the id, then one detail call. Do not page through results unless needed.

```bash
TMDB="npx -y @lorenzopant/tmdb"   # reuse; npx caches, repeat calls are fast
```

## Search

```bash
$TMDB search "severance"                  # multi: movies + tv + people
$TMDB search "dune" --type movie --year 2021
$TMDB search "breaking bad" --type tv
$TMDB search "pedro pascal" --type person
```

Table columns: `ID  TYPE  TITLE  YEAR  RATING`. Footer shows page/results and the next-page flag.

To get just ids (cheap, machine-friendly):

```bash
$TMDB search "severance" --type tv --json \
  | jq -c '.results[:5][] | {id, name, year: .first_air_date[:4]}'
```

## Details

```bash
$TMDB movie 27205                    # title, tagline, genres, runtime, rating, director, cast, overview
$TMDB tv 1396                        # title, genres, season/episode counts, creators, networks, status, cast
$TMDB person 6193                    # biography, known-for
$TMDB movie 550 --append credits,videos
$TMDB tv 1396 --append aggregate_credits,content_ratings
```

`--append` adds data to the same request; the human view surfaces only a few of them, so use `--json | jq` for the rest. `--language it-IT` localizes titles/overviews.

## Missing seasons / episodes

The CLI exposes a series' season list (season number, episode count, air date) via `--json`. That is enough to list what exists and spot gaps. **Do not** attempt per-episode titles — the CLI cannot return them.

Full season map (season 0 = Specials):

```bash
$TMDB tv 1396 --json \
  | jq -r '.seasons[] | [.season_number, .episode_count, (.air_date // "TBA")] | @tsv'
```

Quick totals:

```bash
$TMDB tv 1396 --json \
  | jq -c '{seasons: .number_of_seasons, episodes: .number_of_episodes, status, last_air: .last_air_date}'
```

Seasons the user does **not** own — pass what they have as a comma list:

```bash
HAVE="1,2,3"
$TMDB tv 1396 --json \
  | jq -r --arg have "$HAVE" '
      ($have | split(",") | map(tonumber)) as $owned
      | .seasons[]
      | select(.season_number > 0)
      | .season_number as $s
      | select($owned | index($s) | not)
      | "S\($s) — \(.episode_count) eps — airs \(.air_date // "TBA")"
    '
```

Seasons not yet aired / unreleased (no complete episode set):

```bash
$TMDB tv 1396 --json \
  | jq -r '.seasons[] | select(.season_number > 0 and (.air_date == null or .air_date > (now | strftime("%Y-%m-%d")))) | "S\(.season_number) not yet aired"'
```

Report gaps as `S<n>: have X of Y` only when the user gives an episode count per season; otherwise report the TMDB counts and let them confirm.

## Trending & discover

```bash
$TMDB trending                       # today, all media
$TMDB trending movie --week
$TMDB discover movie -g "science fiction" -y 2014 -s rating
$TMDB discover tv -g "drama|crime" --min-rating 8
```

`-g "a,b"` = all genres, `-g "a|b"` = any. `-s`: popularity (default), rating, votes, date, title, revenue (movie).

## Useful `--json` field paths

| Need | jq path |
|------|---------|
| Movie essentials | `.id .title .release_date .runtime .vote_average .genres[].name .overview` |
| TV essentials | `.id .name .first_air_date .number_of_seasons .number_of_episodes .status .networks[].name` |
| Season list | `.seasons[] | {season_number, episode_count, air_date}` |
| Search results | `.results[] | {id, title: (.title // .name), year: (.release_date // .first_air_date)[:4]}` |

## Gotchas

- `--year` only works with `--type movie` or `--type tv`, not `multi`.
- `--append` is rejected on the curated list commands (`movie popular`, `tv top-rated`).
- Lists accept dashes: `top-rated`, `now-playing`, `on-the-air`, `airing_today`.
- `--json` bypasses all formatting and prints the raw API response — always pipe to `jq`.
- Specials are `season_number: 0`; exclude them when checking main-season completeness.
