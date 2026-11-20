# Adding an expert

Copy any file in [`experts/`](experts/) and edit it. The frontmatter decides when the expert is picked:

```markdown
---
name: <expert-name>
use-when: <the kinds of change this expert should see, in plain words>
---
```

`use-when` is matched against the changed paths and hunks, so name the things a diff contains: "database queries", "IAM policy", "React components". Vague lines like "important changes" match everything.

To wrap an external skill instead of writing the checklist yourself, add a `skill:` field with the install id from skills.sh (for example `anthropics/skills@frontend-design`). Then the body does two jobs the external skill cannot do: say what to review against the loaded skill, and name the neighbour expert that owns the edge. Keep any checks specific to this codebase in the body too, since they can't come from a generic skill.

The body is the brief. Open with one sentence on what the lens finds, list what to look for, and close with a `Leave ... to <expert>` line naming the neighbour that owns anything near the edge. That line keeps two experts from reporting the same finding.
