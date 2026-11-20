---
name: expert-review
description: Review a diff through one or more expert lenses (security, tests, reliability, performance, and any expert added under experts/). Use when the user asks for a security, test, performance or other specialist review, or when another skill needs focused reviewers picked by the scope of a change.
---

# Expert review

An **expert** is a reviewer with one lens. Each expert lives in its own file under [`experts/`](experts/), and the file is the whole brief: what to look for, and what to leave to other experts. This skill picks experts, runs each one as a fresh sub-agent, and returns their findings side by side.

## 1. Pin the diff

Take the fixed point from the user or the calling skill: a branch, commit, tag or MR. Capture `git diff <fixed-point>...HEAD` and `git log <fixed-point>..HEAD --oneline`. Confirm the ref resolves and the diff is non-empty before you spawn anything.

## 2. Pick the experts

If the user or caller named experts, use exactly those. Otherwise read the frontmatter of every file in `experts/` and pick each expert whose `use-when` matches the diff. Read the changed paths and the hunks, not just the commit messages. Pick at least one. State the picks and the one-line reason for each before you run them.

## 3. Run each expert in a fresh sub-agent

Spawn every picked expert in parallel, each with a fresh context. Never review as yourself: the expert must not have seen the reasoning that produced the code. Give each one:

- the diff command and commit list
- the full text of its expert file
- the spec or ticket, when one exists
- the report format below

## 4. Report

Each expert returns findings in this shape, and you present them under one heading per expert, unmerged and unranked across experts:

```
- [blocker|major|minor] path:line: what is wrong. Why it matters. Suggested fix.
```

A finding needs a location and a reason a reviewer could check. An expert with nothing to report says `No findings` and names what it checked. End with a one-line count per expert.

## Adding an expert

Copy any file in `experts/` and change it. The frontmatter decides when the expert is picked:

```markdown
---
name: <expert-name>
use-when: <the kinds of change this expert should see, in plain words>
---
```

The body is the brief. Keep it to what this lens catches, and name the neighbouring expert that owns anything near the edge, so two experts do not report the same finding.
