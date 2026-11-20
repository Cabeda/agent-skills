---
name: expert-review
description: Review a change or a whole codebase through expert lenses picked by its scope. Use when the user asks for a security, performance or other specialist review, a full app review, or when another skill needs focused reviewers.
---

# Expert review

An **expert** is a reviewer with one lens. Each expert is one file under [`experts/`](experts/), and the file is its whole brief. This skill picks experts, runs each in a fresh sub-agent, merges the findings, and returns one report.

## 1. Pin the scope

Take the scope from the user or the calling skill. It is one of two kinds:

- **Change**: a fixed point (a branch, commit, tag or MR base). Capture `git diff <fixed-point>...HEAD` and `git log <fixed-point>..HEAD --oneline`. The scope is the changed paths and hunks. Confirm the ref resolves and the diff is non-empty before you spawn anything.
- **Codebase**: the whole repository at HEAD. Capture the file list with `git ls-files`, and drop anything the repo marks as vendored or generated (its `AGENTS.md`, `CONTRIBUTING.md`, or ignore files say which). Confirm the list is non-empty.

## 2. Pick the experts

If the user or caller named experts, use exactly those. Otherwise read the `use-when` line of every file in `experts/`, and pick each expert it matches. In a change, match against the changed paths and hunks. In a codebase, match against the file list. Pick at least one, and state each pick with a one-line reason.

## 3. Run each expert in a fresh sub-agent

Spawn every picked expert in parallel, each in a fresh context, so it judges the code without the reasoning that produced it. An expert may name an external skill in its `skill:` field. Before the sub-agent starts, make that skill available:

- If it is not installed, run `npx skills add <skill> -g -y`, for example `npx skills add anthropics/skills@frontend-design -g -y`.
- If the install fails, the expert reports `skill not installed: <skill>` with the install command, and the round does not count as clean.

Give each sub-agent:

- the scope: the diff command and commit list for a change, or the file list for a codebase
- the external skill to load first, when the expert names one
- the full text of the expert file
- the spec or ticket, when one exists
- the finding format in step 4

On a codebase, the sub-agent reads the files it needs and reports only findings in files on the list.

## 4. Finding format

Each finding has these fields, in this order:

- **Severity**: `blocker`, `major` or `minor`.
- **Title**: one line that names the problem, such as "Retry loop has no timeout on the deploy poll".
- **Location**: `path:line`, or `path` for a whole-file finding.
- **Evidence**: what the code does, quoted or described, and why that is wrong. A reviewer must be able to check it.
- **Fix**: the change that would resolve it, in one or two sentences.
- **Acceptance**: a command, test or observable result that shows the problem is gone.
- **Fingerprint**: `<path>|<lens>|<normalised claim>`. The claim is the title in lower case, with punctuation and numbers removed. The same problem found on another day gets the same fingerprint.

A finding without a location, evidence and an acceptance check is not finished. Send it back to the expert once, and drop it if it still lacks them.

An expert with nothing to report says `No findings` and names what it checked.

## 5. Merge and report

Merge findings within the run. Two findings with the same fingerprint are one finding: keep the more severe, and list every lens that raised it. Do not merge findings that only share a location.

Present one report, grouped by severity, then by location. Each entry shows its title, lens or lenses, location, and fingerprint. End with a one-line count per expert and the total after merging.

To add an expert, see [ADDING-EXPERTS.md](ADDING-EXPERTS.md).
