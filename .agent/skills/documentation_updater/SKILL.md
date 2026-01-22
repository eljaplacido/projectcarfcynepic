---
description: Update CURRENT_STATUS.md, AGENTS.md, and task tracking documents for Project CARF
---

# CARF Documentation Updater Skill

## Purpose
Enforce the CARF rule: **"ALWAYS update CURRENT_STATUS.md before starting any feature work."**

Updates multiple documentation files atomically to keep project status synchronized.

## When to Use
- Before starting new feature work
- After completing a feature or phase
- When marking tasks as complete
- When adding new decisions or architectural changes

## Files to Update

| File | Purpose | Update Trigger |
|------|---------|----------------|
| `CURRENT_STATUS.md` | Living status doc | Any status change |
| `AGENTS.md` | AI coding context | Logic/phase changes |
| `task.md` (if agentic) | Task checklist | Task completion |

## Execution Steps

### 1. Update CURRENT_STATUS.md

**Location:** `c:\Users\35845\Desktop\DIGICISU\projectcarf\CURRENT_STATUS.md`

**Update the following sections:**

#### Recent Decisions
Add new decision at the top of the list with date:
```markdown
## Recent Decisions
- 2026-01-17: [Your decision/change description]
- 2026-01-16: Backend test coverage increased from 51% to 64%
```

#### Active Task / Status
Update the active task header:
```markdown
## Active Task: [New Task Description]

### Status: [IN PROGRESS | COMPLETE | BLOCKED]
```

#### Completed Steps
When a phase item is done, add it to the appropriate phase:
```markdown
### Phase 6 - Enhanced UIX (In Progress)
- [x] New completed item ✅
- [ ] Pending item
```

### 2. Update AGENTS.md (If Logic Changes)

**Location:** `c:\Users\35845\Desktop\DIGICISU\projectcarf\AGENTS.md`

**Update when:**
- New nodes added to LangGraph workflow
- New services added to `/src/services/`
- New testing commands added
- Phase changes

**Sections to update:**
- `## Current Phase` section
- `## Directory Structure` if new folders added
- `## Testing Commands` if new test patterns

### 3. Update Session Log

Add entry to session log table:
```markdown
## Session Log
| Timestamp | Action | Agent/Human |
|-----------|--------|-------------|
| 2026-01-17 | [Action description] | AI Architect |
```

## Template: Feature Completion Update

When completing a feature, use this checklist:

```markdown
## Recent Decisions
- YYYY-MM-DD: [Feature name] - [Brief description of what was implemented]

## Completed Steps
### Phase N - [Phase Name]
- [x] [Feature item] ✅

## Next Steps
- [ ] [Follow-up item 1]
- [ ] [Follow-up item 2]
```

## Critical Rules

> [!CAUTION]
> **DO NOT TOUCH** the following without human review:
> - `src/core/state.py` - Immutable EpistemicState schema
> - `config/policies.yaml` - Safety policies
> - `.github/workflows/` - CI/CD changes

## Validation

After updating, verify:
1. Markdown renders correctly (no broken links)
2. Checkbox syntax is correct (`- [x]` not `- [X]`)
3. Dates are in YYYY-MM-DD format
4. Session log entries are chronological
