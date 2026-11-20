---
name: expert-review
description: Review a diff through expert lenses picked by its scope. Use when the user asks for a security, performance or other specialist review, or when another skill needs focused reviewers.
---

# Expert review

An **expert** is a reviewer with one lens. Each expert is one file under [`experts/`](experts/), and the file is its whole brief. This skill picks experts, runs each in a fresh sub-agent, and returns their findings side by side.

## 1. Pin the diff

Take the fixed point from the user or the calling skill: a branch, commit, tag or MR. Capture `git diff <fixed-point>...HEAD` and `git log <fixed-point>..HEAD --oneline`. Confirm the ref resolves and the diff is non-empty before you spawn anything.

## 2. Pick the experts

If the user or caller named experts, use exactly those. Otherwise read the `use-when` line of every file in `experts/`, and pick each expert it matches against the changed paths and hunks. Pick at least one. State each pick with a one-line reason before you run them.

## 3. Run each expert in a fresh sub-agent

Spawn every picked expert in parallel, each in a fresh context, so it judges the diff without the reasoning that produced it. An expert may name an external skill in its `skill:` field. Before the sub-agent starts, make that skill available:

- If it is not installed, run `npx skills add <skill> -g -y`, for example `npx skills add anthropics/skills@frontend-design -g -y`.
- If the install fails, the expert reports `skill not installed: <skill>` with the install command, and the round does not count as clean.

Give each sub-agent:

- the diff command and commit list
- the external skill to load first, when the expert names one. The skill supplies the domain guidance, and the expert file decides what to review against it.
- the full text of the expert file
- the spec or ticket, when one exists
- the report format below

## 4. Report

Each expert returns findings in this shape:

```
- [blocker|major|minor] path:line: what is wrong. Why it matters. Suggested fix.
```

A finding carries a location and a reason a reviewer could check. An expert with nothing to report says `No findings` and names what it checked.

Present the findings under one heading per expert, kept separate and in each expert's order. End with a one-line count per expert.

To add an expert, see [ADDING-EXPERTS.md](ADDING-EXPERTS.md).
