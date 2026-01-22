---
description: Generate React components following the CARF design system (Tailwind, TypeScript, light theme)
---

# CARF Component Generator Skill

## Purpose
Generate TypeScript React components following the CARF design system for the Platform Cockpit.

## When to Use
- Adding new UI panels to the dashboard
- Creating modals, widgets, or cards
- Implementing Phase 6 Enhanced UIX components

## Design System Reference

### Theme Tokens

```css
/* Light Theme (Default) */
--background: #F8FAFC;      /* slate-50 */
--card-bg: #FFFFFF;
--card-border: #E2E8F0;     /* slate-200 */
--text-primary: #1E293B;    /* slate-800 */
--text-secondary: #64748B;  /* slate-500 */

/* Semantic Colors */
--primary: #3B82F6;         /* blue-500 */
--success: #22C55E;         /* green-500 */
--warning: #EAB308;         /* yellow-500 */
--danger: #EF4444;          /* red-500 */

/* Confidence Colors */
--confidence-high: #22C55E;    /* green */
--confidence-medium: #EAB308;  /* yellow */
--confidence-low: #EF4444;     /* red */
```

### Card Pattern

All panels should use this card structure:

```tsx
<div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
  <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wide mb-3">
    Panel Title
  </h3>
  {/* Content */}
</div>
```

## Component Template

### Basic Component Structure

```tsx
// src/components/carf/ComponentName.tsx
import React from 'react';

interface ComponentNameProps {
  // Define props with TypeScript
  data?: DataType;
  onAction?: (value: string) => void;
}

export const ComponentName: React.FC<ComponentNameProps> = ({
  data,
  onAction,
}) => {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
      <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wide mb-3">
        Component Title
      </h3>
      
      <div className="space-y-3">
        {/* Component content */}
      </div>
    </div>
  );
};
```

## Component Types

### Panel Component
Full-width dashboard panel (CausalAnalysisCard, BayesianPanel pattern):
- Fixed height or scrollable
- Section header with icon
- Expandable details

### Modal Component
Dialog overlay (MethodologyModal pattern):
- Backdrop with blur
- Close button in header
- Scrollable content area
- Action buttons in footer

### Widget Component
Small, focused element (SuggestedQuestions pattern):
- Clickable items
- Hover states
- Icon + text layout

## Execution Steps

### 1. Create Component File

**Location:** `c:\Users\35845\Desktop\DIGICISU\projectcarf\carf-cockpit\src\components\carf\[Name].tsx`

### 2. Define TypeScript Interface

Include proper typing for all props:

```tsx
interface [Name]Props {
  // Required props
  data: SomeType;
  
  // Optional props
  className?: string;
  onClose?: () => void;
}
```

### 3. Export Component

Add to component exports if creating index file, or import directly.

### 4. Integrate into DashboardLayout

If the component should appear in the main layout:

```tsx
// In DashboardLayout.tsx
import { ComponentName } from './ComponentName';

// Add to appropriate view mode
{viewMode === 'end-user' && (
  <ComponentName data={...} />
)}
```

## Existing Components Reference

| Component | Type | Purpose |
|-----------|------|---------|
| `BayesianPanel` | Panel | Posterior distributions, uncertainty |
| `CausalAnalysisCard` | Panel | Effect estimates, refutation tests |
| `CausalDAG` | Panel | Interactive react-flow graph |
| `ConversationalResponse` | Panel | Dialog-based results |
| `CynefinRouter` | Panel | Domain classification display |
| `DashboardHeader` | Layout | View mode selector, scenario picker |
| `DashboardLayout` | Layout | Main 3-6-3 grid layout |
| `ExecutionTrace` | Panel | Timeline of reasoning steps |
| `FloatingChatTab` | Widget | Persistent bottom-right chat |
| `GuardianPanel` | Panel | Policy checks, verdicts |
| `MethodologyModal` | Modal | Transparency drill-downs |
| `OnboardingOverlay` | Modal | First-run scenario selection |
| `QueryInput` | Widget | Query text input |
| `ResponsePanel` | Panel | Summary and insights |
| `SuggestedQuestions` | Widget | Clickable follow-ups |
| `WalkthroughManager` | Modal | Multi-track guided tours |

## Validation

After creating component:
1. Run `npm run build` to check TypeScript
2. Run `npm run lint` to check ESLint
3. Visually verify in browser at http://localhost:5173
