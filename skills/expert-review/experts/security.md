---
name: security
use-when: the change handles input from users or the network, authentication, authorisation, secrets, file paths, shell or SQL commands, IAM or access policy, or dependencies.
skill: getsentry/skills@security-review
---

# Security expert

Review the diff against the loaded `security-review` skill. That skill covers injection, XSS, authentication, authorisation and cryptography. Apply it, then add the checks below, which are specific to this codebase and that skill does not know about.

Also look for:

- Access policies broader than the code needs: wildcard actions or resources, public buckets, open network rules.
- Secrets in committed config, test fixtures or log output, including values passed as environment variables into a container.
- New or changed dependencies: unpinned versions, unfamiliar or typo-like package names.
- Data a user can see or change that belongs to another user.

Leave error handling and cleanup to `reliability`, and missing tests to `tests`.
