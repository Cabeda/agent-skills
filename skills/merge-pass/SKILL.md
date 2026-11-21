---
name: merge-pass
description: Merge a repo's factory PRs that are safe to merge on their own, and flag the rest for a person. Use for the daily factory run, or to clear a repo's finished factory PRs.
---

# Merge pass

Merge only **two-way doors**: changes that one revert undoes completely, so merging them needs no person. The `forge` skill decides which are; this skill acts on its verdict. It covers one repo.

## 1. List

Run `prs` and keep the PRs whose branch starts with `factory/`.

## 2. Decide each PR

Run `check`, and act on its `verdict`:

- `merge`: run `merge` with the `head_sha` that this same `check` returned.
- `wait`: leave it. Something resolves itself, such as pending checks or a review not yet recorded.
- `human`: a person has to decide. When `needs-human` is not in the PR's `labels`, add it with `label` and comment the `reasons` once with `comment`.
- `off`: leave it. Auto-merge is off for the repo, or the PR is not the factory's.

A refusal from `merge` (exit `3`) stands. Report its reasons and move on.

## 3. Report

List each PR as merged, waiting (with why), flagged for a person (with why), or left alone.
