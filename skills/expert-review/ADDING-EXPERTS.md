# Adding an expert

Copy any file in [`experts/`](experts/) and edit it. The frontmatter decides when the expert is picked:

```markdown
---
name: <expert-name>
use-when: <what a change or codebase contains that this lens should see>
skill: <optional skills.sh id, such as anthropics/skills@frontend-design>
---
```

`use-when` is matched against changed paths and hunks, or a codebase's file list, so name what those contain: "database queries", "IAM policy", "package manifests or lockfiles". A vague line like "important changes" matches everything.

The body is the brief:

1. One sentence on what the lens finds.
2. What to look for.
3. A closing `Leave ... to <expert>` line naming the neighbour that owns the edge, so two experts don't report the same finding.

With a `skill:`, the named skill supplies the domain knowledge and loads first. The body then says what to review against it and keeps any checks specific to your repos, which a generic skill cannot know.
