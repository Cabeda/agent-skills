---
name: codebase-audit
description: Read-only audit of a repository against its stated goal, filing new findings as tickets. Use for a scheduled daily review of a repo, or a full app review that should produce tickets instead of fixes.
---

# Codebase audit

Find what stands between one repository and its **goal**, and file each as a ticket. The audit is **read-only**: its only writes are tickets. Across several repos, audit one at a time, and carry on past a repo that fails.

## 1. Set up

Audit the default branch at HEAD with a clean working tree. Skip any repo that has uncommitted work or sits on another branch, and say why.

## 2. Find the goal

Read the repo's `README.md`, then `AGENTS.md`. The goal is what the project is for and who it serves. A goal is **clear** when you can state, in two sentences, who the project is for and what outcome counts as success for them. A description of what the code is made of is not a goal.

When the goal is not clear, audit nothing. Run `forge file` once for the repo, with the fingerprint `<repo>|goal|no clear goal`, label `needs-info`, and a body that quotes what you found and asks the owner to write the goal at the top of the README and to run `grill-me` on it. A repo that already has that ticket open gets no second one.

## 3. Review

Call the Skill tool with `expert-review` on the **codebase** scope, giving it the goal and the experts the repo's config names (all of them when it names none). The result is one merged report in `expert-review`'s finding format.

Keep a finding when its **Goal** line names a real way it holds the goal back. Drop a minor finding that has no honest link to the goal. Keep every blocker and major finding, and make its Goal line say what harm it does to the goal.

## 4. File what is new

For each kept finding, run `forge file` with the finding's fingerprint. It refuses a finding that already has an open ticket, so a refusal is a normal result, and it reopens nothing. Report a finding whose earlier ticket is closed (`closed_before` in the result) as *back*, and name that ticket in the new one.

The ticket body holds the finding's title, location, evidence, fix, acceptance check and goal, then its lens and severity. Write it so someone who has not seen the report can act on it. `forge file` labels it `factory`.

`to-tickets` supports GitHub, GitLab and local files, and Codeberg is none of them, so tickets go through `forge file` on both forges.

## 5. Report

For each repo: the goal you used, the experts that ran, findings found, filed (with links) and skipped as already filed, and any expert that could not run. A repo with nothing new is a clean result: file nothing and say so.
