---
name: tests
use-when: the change adds or edits tests, or changes behaviour that tests should cover.
---

# Tests expert

Find tests that would stay green while the behaviour they claim to check is broken.

Look for:

- Assertions a wrong result still passes: substring matches that refusals or error text satisfy, `is not None` where a value matters, checks on a field that every response has.
- Expected values derived the way the code derives them, so the test cannot disagree with the code.
- Tests that mock or reach past the public interface, so they break on refactors but miss real breakage.
- New behaviour, branches or error paths with no test, and tests that skip instead of failing when a dependency is missing.
- Setup that leaks resources when it fails before cleanup is registered.
- Tests that pass for timing or ordering reasons: sleeps, shared state, dependence on run order.

For each weak assertion, say what broken behaviour would still pass it. Leave production error handling to `reliability`.
