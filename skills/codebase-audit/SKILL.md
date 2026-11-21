---
name: codebase-audit
description: Read-only audit of a whole repository that files new findings as proposed tickets. Use for a scheduled daily review of a repo, or a full app review that should produce tickets instead of fixes.
---

# Codebase audit

Find ways to improve one repository and file each as a **proposed** ticket for a person to triage. The audit is **read-only**: its only writes go to the tracker. Across several repos, audit one at a time, and carry on past a repo that fails.

## 1. Set up

Audit the default branch at HEAD with a clean working tree. Skip any repo that has uncommitted work or sits on another branch, and say why.

Find the repo's tracker from its `AGENTS.md`, `CONTRIBUTING.md` or the setup `to-tickets` reads. Skip the repo when it has none.

## 2. Review

Call the Skill tool with `expert-review` on the **codebase** scope, with the experts the repo's config names, or else the ones it picks. The result is one merged report in `expert-review`'s finding format.

## 3. Drop what is already filed

Tickets the audit files carry their finding's fingerprint on its own line:

```
Fingerprint: <path>|<lens>|<claim>
```

Search the tracker for each finding's fingerprint:

- **open** ticket: drop the finding, it is tracked
- **closed** ticket, and the problem is still present: reopen it, or file a new one linking it, as the tracker allows
- **closed** ticket, and the problem is gone: drop the finding
- no ticket: keep the finding

## 4. File the rest

Call the Skill tool with `to-tickets`, one ticket per kept finding. Each body holds the finding's title, location, evidence, fix, acceptance, lenses and severity, and the fingerprint line. Mark each ticket proposed by the tracker's convention, such as a `proposed` label.

## 5. Report

For each repo: the experts that ran, findings found, dropped as already filed, and filed (with links), and any expert that could not run. A repo with nothing new is a clean result: file nothing and say so.
