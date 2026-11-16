---
name: meal-planner
description: "Plan meals and schedule them on Google Calendar from Notion."
version: 2.0.0
author: José Cabeda
license: MIT
metadata:
  version: 2.0.0
  category: productivity
  requires:
    bins: [gws, curl, jq]
    env: [NOTION_API_TOKEN, NOTION_RECIPES_DATASOURCE, NOTION_PANTRY_DATASOURCE]
  hermes:
    category: productivity
    tags: [notion, google-calendar, meal-planning, shopping-list]
required_environment_variables:
  - name: NOTION_API_TOKEN
    prompt: Notion integration token
    help: Create an integration at https://www.notion.so/my-integrations and share the recipe book and pantry databases with it.
    required_for: querying Notion
  - name: NOTION_RECIPES_DATASOURCE
    prompt: Notion recipe book data source ID
    required_for: querying recipes
  - name: NOTION_PANTRY_DATASOURCE
    prompt: Notion pantry / shopping-list data source ID
    required_for: querying the pantry and updating the shopping list
---

# Meal Planner

Plan meals by combining your Notion recipe book, pantry/shopping list, and Google Calendar.

## When to Use

Use when the user asks to plan meals for a period, check what's in the pantry or on the shopping list, schedule a recipe on Google Calendar, or add a new recipe to the Notion recipe book. Trigger phrases: "plan meals", "what's for dinner", "meal prep", "shopping list", "add recipe".

## Prerequisites

```bash
source ~/env 2>/dev/null
# Required env vars:
# NOTION_API_TOKEN           — Notion integration token
# NOTION_RECIPES_DATASOURCE  — data source ID for recipe book (recipe book)
# NOTION_PANTRY_DATASOURCE   — data source ID for pantry/shopping list
```

`gws` CLI must be authenticated (`gws auth login`). Both Notion databases must be shared with the integration.

## Database Schema

### Pantry / Shopping List

| Property | Type | Description |
|----------|------|-------------|
| `Name` | title | Item name |
| `Stock` | select | `Yes` (in stock), `No` (buy), `Não ignorar` (out of stock, don't buy) |
| `Quantity` | rich_text | Amount to buy (e.g. "2x", "500g") |

Shopping list = items where `Stock` = `No`. Items with `Não ignorar` are explicitly excluded.

### Recipe Book

| Property | Type | Description |
|----------|------|-------------|
| `Name` | title | Recipe name |
| `Tags` | multi_select | `Peixe`, `Carne`, `Vegetariano`, `Sobremesa`, `Entrada`, `pequeno-almoço` |
| `Duração` | rich_text | Cooking time |
| `Dificuldade` | select | Difficulty (e.g. `Fácil`) |
| `Doses` | number | Servings |
| `Link` | url | External recipe URL |

Recipe pages contain block children: `heading_2` "Ingredientes" + `bulleted_list_item` blocks, then `heading_2` "Preparação" + `numbered_list_item` blocks.

### Tag → Meal Slot

| Tag | Slot |
|-----|------|
| `pequeno-almoço` | Breakfast |
| `Peixe`, `Carne`, `Vegetariano` | Lunch or Dinner |
| `Entrada` | Starter |
| `Sobremesa` | Dessert |

## Workflow

### 1. Determine planning window

Ask: "Plan meals for which period? (current week / next week / custom range)"

### 2. Fetch calendar availability

```bash
gws calendar events list \
  --params '{"calendarId":"primary","timeMin":"START","timeMax":"END","singleEvents":true,"orderBy":"startTime","maxResults":50}' \
  --format json
```

### 3. Query pantry

```bash
source ~/env
# In-stock items
curl -s -X POST "https://api.notion.com/v1/data_sources/$NOTION_PANTRY_DATASOURCE/query" \
  -H "Authorization: Bearer $NOTION_API_TOKEN" -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"page_size":100,"filter":{"property":"Stock","select":{"equals":"Yes"}}}' | jq

# Shopping list (out of stock)
curl -s -X POST "https://api.notion.com/v1/data_sources/$NOTION_PANTRY_DATASOURCE/query" \
  -H "Authorization: Bearer $NOTION_API_TOKEN" -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"page_size":100,"filter":{"property":"Stock","select":{"equals":"No"}}}' | jq
```

### 4. Query recipes + ingredients

```bash
# All recipes
curl -s -X POST "https://api.notion.com/v1/data_sources/$NOTION_RECIPES_DATASOURCE/query" \
  -H "Authorization: Bearer $NOTION_API_TOKEN" -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" -d '{"page_size":100}' | jq

# Recipe ingredients (per page)
curl -s "https://api.notion.com/v1/blocks/{page_id}/children?page_size=100" \
  -H "Authorization: Bearer $NOTION_API_TOKEN" -H "Notion-Version: 2025-09-03" | jq
```

### 5. Plan meals

For each day, assign breakfast + lunch + dinner.

**Rules:**
- Rotate between `Peixe`, `Carne`, `Vegetariano` for variety
- Don't repeat meals within the planning window
- Prefer recipes with more in-stock ingredients
- Prefer `Fácil`/quick recipes on busy days
- If no suitable recipe exists, propose a new one and ask user

### 6. Present plan for confirmation

Table format with: Day | Meal | Recipe | Missing Ingredients | Action Needed

Consolidated shopping list below. Ask: "Proceed? I will create calendar events, add missing items to shopping list, add new recipes (if any)."

**Wait for explicit confirmation before any writes.**

### 7. Create calendar events

```bash
gws calendar events insert \
  --params '{"calendarId":"primary"}' \
  --json '{
    "summary": "🍽️ Lunch: Recipe Name",
    "description": "Recipe: <notion_page_url>",
    "start": {"dateTime":"YYYY-MM-DDTHH:MM:00","timeZone":"<IANA tz, e.g. Europe/Lisbon>"},
    "end": {"dateTime":"YYYY-MM-DDTHH:MM:00","timeZone":"<IANA tz>"},
    "colorId": "2",
    "reminders": {"useDefault": false, "overrides": []}
  }'
```

**Event format:** `🍽️ {MealType}: {RecipeName}` — MealType in English, recipe name in Portuguese.

**Default time slots:** Breakfast 08:00–08:30, Lunch 12:30–13:30, Dinner 20:00–21:00.

### 8. Add new recipes (if confirmed)

```bash
curl -s -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_TOKEN" -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"data_source_id": "'$NOTION_RECIPES_DATASOURCE'"},
    "properties": { ... },
    "children": [ ... ]
  }' | jq
```

### 9. Update shopping list

For missing ingredients not already in pantry:
```bash
curl -s -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_TOKEN" -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"data_source_id": "'$NOTION_PANTRY_DATASOURCE'"},
    "properties": {
      "Name": {"title": [{"text": {"content": "ITEM"}}]},
      "Stock": {"select": {"name": "No"}},
      "Quantity": {"rich_text": [{"text": {"content": "QTY"}}]}
    }
  }' | jq
```

Don't touch items with `Stock` = `Não ignorar`.

## Notes

- These databases use **data sources** (multi-data-source). Use data source ID for queries and `{"data_source_id": "..."}` as parent for page creation.
- Always check `has_more` / `next_cursor` for pagination.
- Rate limit: ~3 req/s for Notion — space batch requests ~400ms apart.
- Recipe page URL is in the `.url` field of query results.
- Language: Notion data is Portuguese. Calendar events use English meal type prefix + Portuguese recipe name.
- Always ask confirmation before creating events, pages, or updating pantry.
