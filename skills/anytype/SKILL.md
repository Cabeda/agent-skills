---
name: anytype
description: "Interact with the local Anytype API (localhost:31009) to read, search, and edit pages in your Anytype vault — including the Goals page. Use when the user mentions Anytype, their goals page, journal entries, or wants to read/write from their Anytype knowledge base."
metadata:
  version: 1.0.0
  category: productivity
  requires:
    bins: [curl, jq]
    env: [ANYTYPE_API_KEY]
---

# Anytype — Local API

Drive the user's local Anytype instance over its HTTP API (`http://localhost:31009`). The Anytype desktop app must be running and logged in. Authenticate with `ANYTYPE_API_KEY` as a Bearer token. Always send header `Anytype-Version: 2025-11-08`.

## Prerequisites

```bash
source ~/env 2>/dev/null
# ANYTYPE_API_KEY — personal Anytype API key (from desktop app Settings > API Keys)
```

Check the local server is up:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:31009/v1/auth/api_keys
```

## Auth

Key is **not** a JWT — it stays stable (no refresh/expiry like the docs' "Bearer format: JWT" suggests). Use it verbatim:

```bash
AUTH="Authorization: Bearer $ANYTYPE_API_KEY"
VERSION="Anytype-Version: 2025-11-08"
```

## Key IDs (user's vault)

Never hard-code vault IDs in this skill. Read them from the environment, and
discover them with the "List spaces" and "Search" calls below when unset:

| Thing | Env var |
|-------|---------|
| Default space | `ANYTYPE_SPACE_ID` |
| Goals page object | `ANYTYPE_GOALS_PAGE_ID` |

## Common Operations

### List spaces
```bash
curl -s -H "$AUTH" -H "$VERSION" "http://localhost:31009/v1/spaces" | jq '.data[] | {id,name}'
```

### List objects in space (paginated, 699+ objects)
```bash
curl -s -H "$AUTH" -H "$VERSION" \
  "http://localhost:31009/v1/spaces/{space_id}/objects?limit=50&offset=0" | jq
```
Override pagination with `offset`/`limit`. Check `.pagination.has_more` / `.pagination.total`. Response omits body; use the get-object endpoint for full markdown.

### Search (name + snippet only, all spaces)
```bash
curl -s -X POST -H "$AUTH" -H "$VERSION" -H "Content-Type: application/json" \
  -d '{"query":"goals"}' \
  "http://localhost:31009/v1/search?limit=20" | jq -r '.data[] | [.name, .id] | @tsv'
```
Filters via `types` (e.g. `["page"]`), `filters` (FilterExpression tree), `sort`.

### Get full object (markdown body)
```bash
curl -s -H "$AUTH" -H "$VERSION" \
  "http://localhost:31009/v1/spaces/{space_id}/objects/{object_id}" \
  | jq -r '.object.markdown'
```

### List types / templates
```bash
curl -s -H "$AUTH" -H "$VERSION" "http://localhost:31009/v1/spaces/{space_id}/types" | jq
curl -s -H "$AUTH" -H "$VERSION" "http://localhost:31009/v1/spaces/{space_id}/templates" | jq
```

## Goal page conventions

A Goals page is a normal `page` object. Anytype markdown may use trailing spaces on heading lines. Goals pages often have long-term and per-year sections with `- [ ]` checkboxes and bare `- ` bullets. Read the page first and preserve its structure exactly when editing (trailing spaces, checkbox syntax, separators).

## Editing

Requires full body read → modify markdown → **PATCH** back. Body is sent as raw markdown:

```bash
curl -s -X PATCH -H "$AUTH" -H "$VERSION" -H "Content-Type: application/json" \
  -d "{\"name\":\"Goals\",\"markdown\":$(jq -Rs . <<'MD'
## Example section
- Example goal
MD
  )}" \
  "http://localhost:31009/v1/spaces/{space_id}/objects/{object_id}" | jq
```

Write path: read full markdown → edit in place → PATCH the whole new body (PATCH is replace-style for `markdown`). **Ask for confirmation before ANY write to the vault.** Prefer additive/responsible edits; the key has full write access to the user's personal vault.

## Notes

- Uses `rtk` / `jq` for JSON parsing.
- Only name + snippet are searchable via `/v1/search` — deep body text is NOT indexed by search; iterate `list objects` or grep the get-object markdown.
- Pagination: `has_more:true` → bump `offset` until exhausted.