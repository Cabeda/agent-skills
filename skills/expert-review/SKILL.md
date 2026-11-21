---
name: expert-review
description: Review a change or a whole codebase through expert lenses. Use for a security, performance, dependency or other specialist review, or when another skill needs focused reviewers.
---

# Expert review

An **expert** is a reviewer with one **lens**. Each expert is one file under [`experts/`](experts/), and the file is its whole brief. This skill picks experts for a **scope**, runs each in a fresh sub-agent, and returns one merged report of **findings**.

## 1. Pin the scope

Take the scope from the user or the calling skill:

- **Change**: a fixed point (branch, commit, tag or MR base). Capture `git diff <fixed-point>...HEAD` and `git log <fixed-point>..HEAD --oneline`. Confirm the ref resolves and the diff is non-empty.
- **Codebase**: the repository at HEAD. Capture `git ls-files`, minus what the repo's `AGENTS.md`, `CONTRIBUTING.md` or ignore files mark as vendored or generated. Confirm the list is non-empty.

## 2. Pick the experts

Use exactly the experts the user or caller named. Otherwise pick each expert whose `use-when` line matches the scope: the changed paths and hunks for a change, the file list for a codebase. Pick at least one, and state each pick with a one-line reason.

## 3. Run the experts

Spawn the picked experts in parallel, each in a fresh context, so each judges the code without the reasoning that produced it. Give each one:

- the scope: the diff command and commit list, or the file list
- its expert file, in full
- the skill named in its `skill:` field, loaded first, when it has one
- the spec or ticket, when one exists, or the repo's goal when the caller gives one
- the finding format below

A `skill:` that is not installed gets `npx skills add <skill> -g -y`. If that fails, the expert reports `skill not installed: <skill>` with the command, and the run is not clean.

## 4. Finding format

Each finding carries, in order:

- **Severity**: `blocker`, `major` or `minor`.
- **Title**: one line naming the problem, such as "Deploy poll retries with no timeout".
- **Location**: `path:line`, or `path` for a whole file.
- **Evidence**: what the code does and why that is wrong, so a reviewer can check it.
- **Fix**: the change that resolves it, in one or two sentences.
- **Acceptance**: a command, test or observable result that shows it is gone.
- **Goal**: when the caller gave a goal, how fixing this serves it, in one sentence. Leave it out when no goal was given.
- **Fingerprint**: `<path>|<lens>|<claim>`, where the claim is the title lower-cased with punctuation and digits removed. The same problem on another day gets the same fingerprint.

Return a finding missing its location, evidence or acceptance to the expert once; drop it if it comes back incomplete. An expert with nothing to report says `No findings` and names what it checked.

## 5. Merge and report

Merge findings that share a fingerprint into one: keep the higher severity, and list every lens that raised it. Group the report by severity, then location, and end with a count per expert and the total after merging.

To add an expert, see [ADDING-EXPERTS.md](ADDING-EXPERTS.md).
