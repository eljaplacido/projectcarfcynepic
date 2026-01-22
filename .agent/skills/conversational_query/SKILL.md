---
description: Conversational query handling with dialog flow, slash commands, and Socratic questioning
---

# CARF Conversational Query Skill

## Purpose
Handle multi-turn conversational query flows with slash commands, Socratic questioning, and context gathering before analysis execution.

## When to Use
- Implementing dialog-flow query experience
- Adding slash command handling to chat
- Building Socratic questioning mode
- Managing conversation context

## Slash Commands Reference

| Command | Action | Backend Endpoint |
|---------|--------|------------------|
| `/question` | Start Socratic questioning mode | Local LLM call |
| `/query` | Execute analysis query | `POST /query` |
| `/analysis` | Show last analysis snapshot | Local state |
| `/history` | Open analysis history panel | `localStorage` or future API |
| `/help` | Show available commands | Static content |

## Implementation Pattern

### Command Detection
```typescript
const parseSlashCommand = (input: string): SlashCommand | null => {
  const match = input.match(/^\/(\w+)\s*(.*)/);
  if (!match) return null;
  
  const [, command, args] = match;
  return { command, args };
};
```

### Socratic Mode Flow
```
User: /question
Bot: Let me help improve your analysis:

1. Context: Your current confidence is 72%.
   Question: Can you describe the business domain more specifically?

2. Data: I detected 3 confounders.
   Question: Are there industry-specific factors not captured?

3. Variables: The causal direction assumes X→Y.
   Question: Could Y→X also be plausible?

[User answers each question, updating context]
```

### Required Frontend State
```typescript
interface ConversationState {
  mode: 'normal' | 'socratic' | 'dialog-flow';
  currentStep?: number;
  gatheredContext: {
    domain?: string;
    variables?: string[];
    dataset?: string;
    hypothesis?: string;
  };
  lastAnalysis?: QueryResponse;
}
```

## Backend Integration

### Existing Endpoints
- `POST /query` - Main analysis (use for `/query` command)
- `GET /scenarios` - Demo scenarios (use for context suggestions)
- `GET /health` - System status

### API Gaps for Phase 7 (Planned)
| Endpoint | Purpose | Status |
|----------|---------|--------|
| `POST /what-if` | Counterfactual simulation | NOT IMPLEMENTED |
| `GET /sessions` | Analysis history | NOT IMPLEMENTED |
| `POST /sessions/{id}` | Save analysis session | NOT IMPLEMENTED |

## Socratic Prompts Library

### Quantify Uncertainty
```
Your confidence is {confidence}%.
What additional data would increase certainty?
- [ ] More samples from similar domains
- [ ] External validation data
- [ ] Expert review
```

### Probe Complexity
```
I identified {n} confounders: {confounders}.
Are there industry-specific factors not captured?
```

### Challenge Assumptions
```
The causal model assumes {treatment} → {outcome}.
Could the reverse direction be plausible?
```

### Suggest Improvements
```
Adding {n} more samples could reduce epistemic uncertainty by ~{reduction}%.
Would you like to:
- [ ] Upload additional data
- [ ] Generate synthetic test data
- [ ] Proceed with current confidence
```

## Troubleshooting

### Command Not Recognized
- Check for leading whitespace in input
- Verify command is lowercase
- Check for typos in command name

### Socratic Mode Not Advancing
- Ensure user input is captured before next step
- Check gatheredContext is being updated
- Verify LLM connection for dynamic questions
