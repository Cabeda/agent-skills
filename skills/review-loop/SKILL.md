---
name: review-loop
description: Relentless adversarial review loop on a branch or draft MR, fixing and re-reviewing until a clean round. Use after implementing a change, or when the user asks to keep reviewing until the reviewer is happy. For a read-only daily audit of a whole repo, use codebase-audit instead.
---

# Review loop

Hand the human code that reviewers have already failed to break. Each **round** runs every chosen reviewer on the current head, triages what they find, and fixes it. The loop has no round limit. It ends when a round finds nothing new, or when it stops making progress.

## 0. Set up

Pin the branch or MR, and its base. Note the ticket when there is one, because triage decides scope against it.

## 1. Choose the reviewers

Choose once, and change the choice only when the diff's scope changes.

- Call the Skill tool with `code-review`, for documented standards and fit to the ticket.
- Call the Skill tool with `expert-review`, with the experts whose lens the diff needs. Name them, with one line on why.
- If the MR has a review bot (a CI job or app that posts review notes), add it. The repo's `AGENTS.md`, `CONTRIBUTING.md` or CI config says how to trigger it.

Reviewers run in fresh sub-agents or on the server, never as you. You wrote the code, so you are the one reviewer who cannot find its blind spots.

## 2. Run a round

Push first, so every reviewer sees the same commit. Run every reviewer on the current head. Trigger a review bot on the new head, and wait for its new notes with the harness's PR watch when there is one.

A reviewer that fails to run (job error, model unavailable, runner interrupted) has not reviewed. Retry it once. If it fails again, the round is not clean: record it and tell the user.

## 3. Triage every finding

Give each finding exactly one outcome:

- **Fix**: the finding is right. Fix the cause, not the symptom the reviewer quoted, and look for the same mistake elsewhere in the diff.
- **Reject**: the finding is wrong. Reply with the evidence: a file and line, a test, upstream source.
- **Park**: the fix needs a decision only the human can make, such as a design choice, a behaviour change, or scope outside the ticket. Record it and keep fixing the rest.

A finding is **new** unless it repeats one you already fixed, rejected or parked, matched by its fingerprint. A finding that returns after two fixes is not converging: park it.

## 4. Verify and commit

Run the repo's checks (lint, types, the tests that cover what you touched), and commit the round on its own, through the repo's hooks, with a message that names what it fixed.

Reply to each bot thread you fixed or rejected, citing the commit or the evidence, and resolve the bot's threads you fixed. Reply to human threads, and leave resolving them to the human.

Start the next round at step 2.

## 5. Stop and hand over

Stop at the first of:

- a **clean round**: every reviewer ran on the current head and found nothing new. Done.
- **no progress**: a round made no commit and produced no new finding that needs a decision. Done, with the findings that remain stated.
- only parked findings remain: done, with decisions pending.

There is no round limit. Each round either changes the code or finds something new, so the loop ends. If a round changes the code and still finds only findings you already fixed or parked, stop and report it.

Leave the MR in draft. Report to the human:

- rounds run, and the reviewers in each
- findings fixed, rejected (with the reason) and parked (with the decision needed)
- anything no reviewer could check, such as behaviour that needs a live environment
