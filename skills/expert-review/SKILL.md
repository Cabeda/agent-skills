---
name: expert-review
description: Review a change or a whole codebase through expert lenses picked by its scope. Use when the user asks for a security, performance or other specialist review, a full app review, or when another skill needs focused reviewers.
---

# Expert review

An **expert** is a reviewer with one lens. Each expert is one file under [`experts/`](experts/), and the file is its whole brief. This skill picks experts, runs each in a fresh sub-agent, and returns their findings side by side.

## 1. Pin the scope

Take the scope from the user or the calling skill. It is one of two kinds:

- **Change**: a fixed point (a branch, commit, tag or MR base). Capture `git diff <fixed-point>...HEAD` and `git log <fixed-point>..HEAD --oneline`. The scope is the changed paths and hunks. Confirm the ref resolves and the diff is non-empty before you spawn anything.
- **Codebase**: the whole repository at HEAD. Capture the file list with `git ls-files`, and drop anything the repo marks as vendored or generated (its `AGENTS.md`, `CONTRIBUTING.md`, or ignore files say which). The scope is that file list. Confirm the list is non-empty.

## 2. Pick the experts

If the user or caller named experts, use exactly those. Otherwise read the `use-when` line of every file in `experts/`, and pick each expert it matches. In a change, match against the changed paths and hunks. In a codebase, match against the file list. Pick at least one. State each pick with a one-line reason before you run them.

## 3. Run each expert in a fresh sub-agent

Spawn every picked expert in parallel, each in a fresh context, so it judges the code without the reasoning that produced it. An expert may name an external skill in its `skill:` field. Before the sub-agent starts, make that skill available:

- If it is not installed, run `npx skills add <skill> -g -y`, for example `npx skills add anthropics/skills@frontend-design -g -y`.
- If the install fails, the expert reports `skill not installed: <skill>` with the install command, and the round does not count as clean.

Give each sub-agent:

- the scope: the diff command and commit list for a change, or the file list for a codebase
- the external skill to load first, when the expert names one. The skill supplies the domain guidance, and the expert file decides what to review against it.
- the full text of the expert file
- the spec or ticket, when one exists
- the report format below

On a codebase, the sub-agent reads the files it needs. It reports only findings in files on the list.

## 4. Report

Each expert returns findings in this shape:

```
- [blocker|major|minor] path:line: what is wrong. Why it matters. Suggested fix.
```

A finding carries a location and a reason a reviewer could check. On a change, a finding is about what the change adds or breaks. On a codebase, it is about the code as it stands. An expert with nothing to report says `No findings` and names what it checked.

Present the findings under one heading per expert, kept separate and in each expert's order. End with a one-line count per expert.

To add an expert, see [ADDING-EXPERTS.md](ADDING-EXPERTS.md).
