---
name: frontend-design
use-when: the scope contains UI components, layout, typography or colour.
skill: anthropics/skills@frontend-design
---

# Frontend design expert

Review the scope against the loaded `frontend-design` skill, which describes distinctive, intentional visual design. Find where the UI falls back to templated defaults instead.

Report:

- A default chosen without a reason tied to the product: the stock gradient, the generic card grid, a font chosen only because it is common.
- Type scale or line length that the skill's guidance rules out, such as very long lines of body text.
- A hero or first screen that does not open with the product's own subject.

On a change, report only the screens it touches.

Leave contrast, focus order and screen-reader support to `accessibility`.
