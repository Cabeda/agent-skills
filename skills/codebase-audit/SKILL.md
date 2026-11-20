---
name: codebase-audit
description: Read-only audit of a whole repository. Runs the expert reviewers over the codebase, skips findings that already have a ticket, and turns the rest into tickets. Use for a scheduled daily run across repos, or when the user asks for a full app review that should produce tickets rather than fixes.
---

# Codebase audit

Look for ways to improve a repository and file each one as a ticket for a person to triage. This skill never changes the repo: it makes no commits, no branches and no pushes. Its only output is tickets.

Each run covers one repository. A run across several repos does one repo at a time, and a failure in one repo does not stop the others.

## 1. Set up

Confirm the repo's working tree is clean and at its default branch's HEAD. If it is not, record that and skip the repo for this run. Never audit uncommitted work.

Find the tracker the repo uses, from its `AGENTS.md`, `CONTRIBUTING.md` or the tracker setup that `to-tickets` reads. If none is configured, stop for this repo and record that.

## 2. Review the codebase

Call the Skill tool with `expert-review`, with the **codebase** scope. Let it pick the experts by the file list, unless the repo's config names some. Expert findings arrive as one merged report, with a title, location, evidence, fix, acceptance check and fingerprint for each.

Add `code-review` for documented standards, using the codebase scope rather than a ticket.

## 3. Drop what is already filed

For each finding, look for an existing ticket in the repo's tracker with the same fingerprint. The fingerprint appears in the ticket body, on a line the audit writes:

```
Fingerprint: <path>|<lens>|<normalised claim>
```

- An **open** ticket with the fingerprint: drop the finding. It is already tracked.
- A **closed** ticket with the fingerprint, where the problem is still present: reopen it, or file a new one that links the old one, as the tracker allows.
- A **closed** ticket where the problem is gone: drop the finding.
- No ticket: keep the finding.

This step is the only tracker lookup. Tracker specifics belong to the repo, and this skill does not hard-code any tracker.

## 4. Turn the rest into tickets

Hand the kept findings to the Skill tool with `to-tickets`. Give it the findings as the plan, one ticket per finding. For each ticket, the body must include:

- the title, location, evidence, fix and acceptance check from the finding
- the fingerprint line from step 3
- the lens or lenses that raised it, and the severity

Mark each ticket as proposed, using the repo's tracker convention, such as a `proposed` label. A person decides which proposed tickets become work.

If no findings are kept, file nothing and say so.

## 5. Report

Report for the repo:

- the scope and the experts that ran
- findings found, dropped as already filed, and filed as new tickets, with each ticket's link
- any expert that could not run, and why

A run that finds nothing new is a clean result. Say so, and file nothing.
