---
name: review-loop
description: Relentless adversarial review of a branch or draft MR. Runs reviewers, fixes what they find, and re-requests review until a clean round or 10 rounds. Use after implementing a change, before a human reviews it, or when the user asks to loop on review until the reviewer is happy.
---

# Review loop

Hand the human an MR that reviewers have already failed to break. Each **round** runs every chosen reviewer on the current head, triages what they find, fixes it, and pushes. The loop ends on a **clean round**: every reviewer ran on the current head and reported nothing to fix.

## 0. Set up

Pin the target: the MR or branch, its base, and the spec or ticket. Read the ticket now, because reviewers check against it. The round cap is **10** unless the user sets another.

## 1. Choose the reviewers

Choose once, and change the choice only when the scope of the diff changes.

- Always call the Skill tool with `code-review`. It covers documented standards and fit to the spec.
- Call the Skill tool with `expert-review` for the experts whose lens the diff needs. Name them, with one line on why.
- If the MR has a review bot (a CI job or app that posts review notes), it is one more reviewer. Look for it in the repo's `AGENTS.md`, `CONTRIBUTING.md` or CI config.

Reviewers run in fresh sub-agents or on the server, never as you. You wrote the code, so you are the one reviewer who cannot find its blind spots.

## 2. Run a round

Push the current head first, so every reviewer sees the same commit. Then run every reviewer on it. For a review bot, trigger it on the new head and wait for its new notes. Use the harness's PR watch when there is one, not a sleep loop.

A reviewer that fails to run (job error, model unavailable, runner interrupted) has not reviewed. Retry it once. If it fails again, the round is not clean: record it and tell the user.

## 3. Triage every finding

Give each finding exactly one outcome:

- **Fix**: the finding is right. Fix the cause, not the symptom the reviewer quoted, and look for the same mistake elsewhere in the diff.
- **Reject**: the finding is wrong. Reply with the evidence (a file and line, a test, upstream source). A rejected finding that comes back is not new; point to the earlier reply.
- **Park**: the fix needs a decision only the human can make (a design choice, a behaviour change, scope outside the ticket). Record it and keep fixing the rest.

If a finding comes back after you fixed it twice, park it: the fix is not converging, and the human should see it.

## 4. Fix, verify, push

Make the fixes. Run the repo's checks (lint, types, the tests that cover what you touched) before you push. Commit each round on its own, with a message that names what the round fixed. Never skip hooks.

On the MR, reply to each bot thread you fixed or rejected, citing the commit or evidence. Resolve the bot's threads you fixed. Reply to human threads, but leave resolving them to the human.

Then start the next round at step 2.

## 5. Stop and hand over

Stop at the first of:

- a **clean round**: done.
- only parked findings remain: done, with decisions pending.
- the round cap: stop, and say what the last round still found.

Leave the MR in draft. Report to the human:

- rounds run, and the reviewers in each
- findings fixed, rejected (with the reason) and parked (with the decision needed)
- anything no reviewer could check, such as behaviour that needs a live environment
