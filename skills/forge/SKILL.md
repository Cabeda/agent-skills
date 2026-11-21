---
name: forge
description: One command for GitHub and Codeberg that enforces the code factory's safety rules. Use to list issues or PRs, file tickets, push factory branches, open PRs or merge on either forge.
---

# Forge

`scripts/forge.py` in this skill's folder (Python 3.11+) is the only way the factory reads or writes a forge. The rules that must hold unattended live in the script, so a prompt cannot talk past them.

Run `python3 <this folder>/scripts/forge.py --root <factory folder> <verb> ...`. TARGET is a repo's folder name under the root. Every verb prints JSON. Exit `0` is done (or a dry run), `1` an error, `3` refused by a rule, and a refusal lists every rule that stopped it. Do not retry a refusal; report it.

## Verbs

| Verb | What it does |
|---|---|
| `repos` | Repos under the root on GitHub or Codeberg, with their settings, and the folders it skipped and why. |
| `issues TARGET` | Open issues the factory may work on: oldest first, up to the free PR slots, by trusted authors, with no PR on them yet. Also `untrusted`, `skipped` and `truncated`. |
| `issue TARGET N` | One issue with its comments. The author and each comment carry `trusted`. |
| `prs TARGET` | Open PRs. |
| `check TARGET N [--sha S]` | Whether PR N may merge. Returns a `verdict` (`merge`, `wait`, `human` or `off`) and every reason. Writes nothing. |
| `mark-reviewed TARGET N --sha S` | Records that the review loop ended clean at head S. |
| `merge TARGET N --sha S` | Squash-merges when every gate passes, taking the PR out of draft first. |
| `push TARGET --branch factory/X` | Pushes that branch to origin. Never another branch, never forced. |
| `open-pr TARGET --head B --base B --title T --body-file F` | Opens a draft PR from a factory branch. |
| `ready TARGET N` | Takes a factory PR out of draft. |
| `comment TARGET N --body-file F` | Comments on an issue or PR. |
| `label TARGET N NAME` | Adds a label, creating it when missing. |
| `find TARGET --fingerprint T` | Issues, open or closed, filed for that fingerprint. |
| `file TARGET --title T --body-file F --fingerprint T [--label L]` | Files an issue labelled `factory`, with the fingerprint. Refuses when one is still open or the backlog is full. |

A fingerprint is the raw `<path>|<lens>|<claim>` from a finding.

## Rules in the script

- **Dry run first.** Every write reports what it would do until the repo sets `dry-run = false`.
- **Trust.** `issues` returns only issues by the signed-in user, `trusted-authors`, or people with write access. An unknown author is never trusted, and `issue` marks each comment the same way.
- **Merging.** `merge` needs `auto-merge = true`, a `factory/` branch, a passing check (a repo with no CI is not green), a head with a recorded clean review, no conflicts, a size under the limits, and no path from the one-way list (workflows, migrations, infrastructure, manifests, lockfiles, licences and the like). A repo can add one-way paths, and never remove one.
- **Pushes and PRs.** Only `factory/` branches, never the default branch. PRs open as drafts.
- **Limits.** `max-open-prs` caps PRs the factory has open, and `max-open-issues` caps its open tickets.

Settings come from `factory.toml` in the root. See [`code-factory/factory.example.toml`](../code-factory/factory.example.toml).
