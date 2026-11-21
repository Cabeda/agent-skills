---
name: dependencies
use-when: the scope contains package manifests, lockfiles, CI workflow actions, container base images, pre-commit hooks, or Renovate or Dependabot config.
skill: Cabeda/agent-skills@dependency-update
---

# Dependencies expert

Review the scope against the policy and dependency rules in the loaded `dependency-update` skill. Report what breaks them; each fix is a later `dependency-update` run, so this lens only reports.

Look for:

- Versions that break the policy: ranges instead of exact pins, a missing or uncommitted lockfile, CI installs that ignore the lockfile.
- Actions and images pinned by a moving tag instead of a SHA or digest.
- Dependencies with a known vulnerability, and dependencies far enough behind that the next update is a major.
- A new or renamed package whose name is close to a popular one, or that brings an install-time script.
- No Renovate or Dependabot config, or one with no release-age window, no digest pinning, or auto-merge on without a reason.
- A change that weakens the repo's own dependency rules, such as shortening its release-age window.

Leave secrets, access and other application code to `security`.
