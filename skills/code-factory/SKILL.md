---
name: code-factory
description: Run one day of the code factory over every repo in a folder, merging what is safe, updating dependencies, auditing against each repo's goal and implementing open issues. Use for the scheduled daily run, or to run the whole factory once by hand.
---

# Code factory

One run moves every repo in the working folder one step forward with no one watching. It only sequences other skills, and each of them runs alone too. To set it up, see [SETUP.md](SETUP.md).

## 1. Find the repos

Run `forge repos` in the working folder. Say which repos it found, whether each is in dry run, and which folders it skipped. Stop and report the error when `factory.toml` is invalid.

## 2. Run each repo in turn

One repo at a time, and a failure in one never stops the next. Skip a repo whose working tree has uncommitted changes, and say so. Otherwise fetch, and fast-forward its default branch. Then:

1. Call the Skill tool with `merge-pass`. Finishing yesterday's PRs frees slots for today's.
2. Call the Skill tool with `dependency-update`. Name its branches `factory/deps-<package>`, push them with `forge push`, open its PRs with `forge open-pr`, and run `mark-reviewed` after its review loop ends clean. Manifests and lockfiles are one-way doors, so these PRs always wait for a person to merge them.
3. Call the Skill tool with `codebase-audit`, with the repo's `experts` setting. An empty setting runs every expert.
4. Call the Skill tool with `issue-worker`. It picks up the tickets the audit just filed.

A step that fails is recorded, and the next step still runs.

In a dry run (`dry-run` is true for the repo), say so to each step. `merge-pass` and `codebase-audit` run as they are, because `forge` reports their writes without making them. `dependency-update` stops after the policy verdict for each candidate, and `issue-worker` stops after judging each issue.

## 3. Report

Lead with what needs a person: PRs flagged `needs-human`, issues asked about, and anything that failed. Then, for each repo, the PRs merged and waiting, dependency updates opened, tickets filed, issues implemented, and what was skipped, each with its reason.
