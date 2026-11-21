---
name: review-loop
description: Relentless review loop on a branch or draft MR, fixing and re-reviewing until a clean round. Use after implementing a change, or when the user wants review repeated until nothing new is found.
---

# Review loop

Hand the human an MR that reviewers have already failed to break. Each **round** runs every reviewer on the current head, triages the findings, and fixes them. The loop runs until a **clean round**, with no round limit.

## 1. Set up

Pin the branch or MR and its base. Note the ticket, because triage decides scope against it.

Choose the reviewers once, and change the choice only when the diff's scope changes:

- the Skill tool with `code-review`, for documented standards and fit to the ticket
- the Skill tool with `expert-review` on the change scope, naming the experts the diff needs, with one line on why
- the MR's review bot, when it has one. The repo's `AGENTS.md`, `CONTRIBUTING.md` or CI config says how to trigger it.

Every reviewer runs in a fresh sub-agent or on the server. You wrote the code, so its blind spots are yours too.

## 2. Run a round

Push, so every reviewer sees the same commit, then run every reviewer on it. Trigger the review bot on the new head and wait for its new notes, using the harness's PR watch when it has one.

A reviewer that fails to run (job error, model unavailable, runner interrupted) has not reviewed. Retry it once; if it fails again, the round is not clean, and you tell the user.

## 3. Triage every finding

A finding is **new** unless its fingerprint matches one already fixed, rejected or parked. Give each new finding one outcome:

- **Fix**: it is right. Fix the cause, not the quoted symptom, and look for the same mistake elsewhere in the diff.
- **Reject**: it is wrong. Reply with the evidence: a file and line, a test, upstream source.
- **Park**: it needs a decision only the human can make, such as a design choice, a behaviour change, or scope outside the ticket.

A finding that returns after two fixes is not converging: park it.

## 4. Verify and commit

Run the repo's lint, type checks and the tests covering what you touched. Commit the round on its own, through the repo's hooks, with a message naming what it fixed.

Reply to each bot thread you fixed or rejected, citing the commit or evidence, and resolve the bot's threads you fixed. Reply to human threads and leave resolving them to the human. Then start the next round.

## 5. Stop and hand over

Stop at the first of:

- a **clean round**: every reviewer ran on the current head and found nothing new
- **no progress**: the round made no commit
- only parked findings remain

Leave the MR in draft and report: the rounds and their reviewers; findings fixed, rejected with the reason, and parked with the decision needed; and anything no reviewer could check, such as behaviour that needs a live environment.
