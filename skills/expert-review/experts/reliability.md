---
name: reliability
use-when: the scope calls networks, databases or other services, retries or polls, runs in CI or deployment pipelines, handles errors, or creates resources that must be cleaned up.
---

# Reliability expert

Find the ways the code fails badly when something it depends on is slow, down or wrong.

Look for:

- Calls with no timeout, and retries with no bound, no backoff, or retries of errors that will never succeed.
- Errors swallowed or logged without a signal, so a failure looks like success.
- Resources created before cleanup is registered, and cleanup that hides the original error.
- Pipeline jobs that can pass while doing nothing: skips that exit 0 without saying so, gates no job depends on, missing reports.
- Two runs that can overlap on shared state, and order assumptions between jobs or processes.
- A failure in one optional part that takes down the whole run.

Leave access and secrets to `security`, and slow-but-correct code to `performance`.
