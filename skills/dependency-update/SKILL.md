---
name: dependency-update
description: Update a repository's dependencies safely, one draft PR per update, like Dependabot. Use when the user asks to bump, upgrade or update dependencies, fix a vulnerable package, or set up automated dependency PRs.
---

# Dependency update

Keep a repository's dependencies current without letting an update become the way in. Each update lands as its own **draft PR** that passes the repo's checks and explains what changed. The **policy** below decides which updates are allowed, and the repo's own **dependency rules** override it.

## 1. Read the repo's rules

Collect the dependency rules before you look at any version. They live in `AGENTS.md`, `CONTRIBUTING.md`, the manifests' tool config (for example `[tool.uv]` with `exclude-newer`), `.npmrc`, and any `renovate.json` or `.github/dependabot.yml`. They cover things like pinned versions, release-age windows, allowed registries and licences, and packages that must not move. A rule that blocks an update wins: skip the update and report the rule.

Find each ecosystem from its manifest and lockfile, including CI: workflow actions, container base images, and pre-commit hooks.

## 2. List the candidates

Use each ecosystem's own outdated and audit commands, such as `npm outdated` with `npm audit`, `uv lock --upgrade-package` with `pip-audit`, or `osv-scanner` across all of them. Order the candidates: known vulnerabilities first, then patch, minor, and major updates.

## 3. Apply the policy

An update is allowed only when every rule holds:

- **Release age**: the version is at least 7 days old, or the repo's own window if it sets one. A fix for a known vulnerability may skip the wait; record the advisory id.
- **Exact pins and a committed lockfile**: manifests pin exact versions where the ecosystem allows, and CI installs from the lockfile (`npm ci`, `uv sync --locked`).
- **Same package, same source**: the name matches what the repo already uses, character for character, and the package's repository and publisher are unchanged. A new install-time script (such as `postinstall`) blocks the update until a human approves it.
- **Pinned by digest**: CI actions and container images are pinned to a commit SHA or image digest, with the tag in a comment.
- **Licence**: the licence is unchanged, or allowed by the repo's rules.

## 4. Open one PR per update

For each allowed update, or each group the repo's config groups together:

1. Branch from the default branch.
2. Change the version and regenerate the lockfile with the ecosystem's tool. Edit the lockfile only through that tool.
3. Run the repo's full checks through its hooks. If they fail and the changelog names a migration, apply that migration. Otherwise drop the update and report the failure.
4. Open a draft PR. Its body holds: old and new version; the changelog and breaking changes, read from the release notes; advisories fixed; the policy checks it passed; and the commands that verified it.

Keep updates out of feature branches, and keep feature code out of update PRs. Majors always get their own PR. Use a token scoped to opening PRs on this repo, and keep it out of PR bodies and logs. To harden a PR before a human reviews it, run `review-loop` on it.

## 5. Automate it

When the repo has no Renovate or Dependabot config, propose one that encodes this policy, as its own draft PR:

- **Renovate**: `minimumReleaseAge` (with `internalChecksFilter: "strict"`), `rangeStrategy: "pin"`, `pinDigests: true`, `vulnerabilityAlerts`, and `packageRules` for grouping and majors.
- **Dependabot**: `cooldown.default-days`, a `groups` block for minor and patch updates, and an entry for `github-actions` as well as each package ecosystem.

Leave auto-merge off unless the repo's rules turn it on.

## 6. Report

List each update: PR opened (with its link), skipped by a rule (naming the rule), or dropped after failing checks (with the failure). Then list any update the policy blocked that needs a human decision.
