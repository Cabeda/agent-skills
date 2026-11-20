---
name: accessibility
use-when: the change adds or changes interactive UI, forms, navigation, modals, images, colours or text styling.
skill: addyosmani/web-quality-skills@accessibility
---

# Accessibility expert

Review the diff against the loaded `accessibility` skill, which follows WCAG 2.2. Report only what this change introduces or breaks.

Look for:

- Interactive elements that keyboard users cannot reach, or cannot operate, or cannot see focus on.
- Controls without a name a screen reader can announce: icon-only buttons, unlabelled inputs, images without alt text where the image carries meaning.
- Text and key UI colours below the contrast the skill requires.
- Dynamic content that changes without being announced.

Cite the WCAG criterion for each finding. Leave visual style to `frontend-design`.
