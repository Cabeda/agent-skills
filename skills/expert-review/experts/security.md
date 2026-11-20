---
name: security
use-when: the scope handles input from users or the network, authentication, authorisation, secrets, file paths, shell or SQL commands, or IAM or access policy.
skill: getsentry/skills@security-review
---

# Security expert

Review the scope against the loaded `security-review` skill. That skill covers injection, XSS, authentication, authorisation and cryptography. Apply it, then add the checks below, which a generic skill cannot know.

Also look for:

- Access policies broader than the code needs: wildcard actions or resources, public buckets, open network rules.
- Secrets in committed config, test fixtures or log output, including values passed as environment variables into a container.
- Data a user can see or change that belongs to another user.

Leave error handling and cleanup to `reliability`, missing tests to `tests`, and dependency versions and pinning to `dependencies`.
