---
description: Format and display execution traces, EFE metrics, and circuit breaker status for Developer View
---

# CARF Developer View Tracer Skill

## Purpose
Create real-time visualization of the 4-layer cognitive stack, execution traces, state inspection, and Active Inference metrics for AI Act compliance transparency.

## When to Use
- Implementing Developer View panels
- Adding execution trace timeline
- Displaying Active Inference EFE metrics
- Showing circuit breaker status

## Backend Data Sources

### From QueryResponse
```typescript
reasoningChain: ReasoningStep[] // Available ✅
```

### ReasoningStep Structure
```typescript
interface ReasoningStep {
  node: string;      // "Router", "Causal Analyst", "Guardian"
  action: string;    // "Classified as Complicated domain"
  confidence: string; // "high", "medium", "low"
  duration?: number;  // ms (PLANNED - not in current API)
  timestamp?: string; // ISO time (PLANNED - not in current API)
}
```

## Developer View Panels

### 1. Architecture Flow Panel
Map reasoning steps to 4-layer stack:

| Step Node | Layer | Color |
|-----------|-------|-------|
| Router | Layer 1: Sense-Making | Blue |
| Causal Analyst | Layer 2: Cognitive Mesh | Green |
| Bayesian Explorer | Layer 2: Cognitive Mesh | Purple |
| Guardian | Layer 4: Governance | Orange |
| Human Escalation | Layer 4: Governance | Red |

### 2. Execution Trace Panel
Format reasoning chain as timeline:

```typescript
const formatTrace = (step: ReasoningStep, index: number) => ({
  time: `${(index * 0.5).toFixed(1)}s`, // Simulated timing
  node: step.node,
  action: step.action,
  status: step.confidence === 'high' ? '✅' : '⚠️',
});
```

### 3. State Inspector Panel
Display EpistemicState fields:

| Field | Display | Source |
|-------|---------|--------|
| `cynefin_domain` | Badge | `domain` in response |
| `domain_confidence` | Progress bar | `domainConfidence` |
| `domain_entropy` | Heat indicator | `domainEntropy` |
| `causal_evidence` | Collapsible JSON | `causalResult` |
| `bayesian_evidence` | Collapsible JSON | `bayesianResult` |
| `guardian_verdict` | Status badge | `guardianVerdict` |

### 4. Circuit Breaker Panel
Monitor for Guardian/policy violations:

```typescript
const getCircuitBreakerStatus = (response: QueryResponse) => {
  if (response.guardianResult?.violations.length > 0) {
    return { status: 'TRIPPED', reason: response.guardianResult.violations[0] };
  }
  if (response.domainEntropy > 0.9) {
    return { status: 'WARNING', reason: 'High entropy detected' };
  }
  return { status: 'SAFE', reason: null };
};
```

### 5. Active Inference Metrics (Future)

| Metric | Formula | Display |
|--------|---------|---------|
| **EFE Score** | Pragmatic + Epistemic | Gauge 0-1 |
| **Pragmatic Value** | Risk term | Progress bar |
| **Epistemic Value** | Ambiguity term | Progress bar |
| **Belief Entropy** | $H(Q(s))$ | Heat indicator |

**Note:** Active Inference metrics require pymdp backend integration. Currently not exposed in API.

## AI Act Compliance Mapping

| Requirement | Developer View Feature |
|-------------|----------------------|
| Art. 12 Record-keeping | Execution trace + export |
| Art. 13 Transparency | Architecture flow + state inspector |
| Art. 14 Human oversight | Guardian panel + escalation status |

## API Enhancements Needed

To fully implement Developer View:

| Enhancement | Purpose | Priority |
|-------------|---------|----------|
| Add `duration_ms` to ReasoningStep | Timing info | HIGH |
| Add `timestamp` to ReasoningStep | Audit trail | HIGH |
| Expose Active Inference EFE | Metrics display | MEDIUM |
| Add `/audit-log` endpoint | Session persistence | MEDIUM |

## Sample ReactFlow Architecture

```typescript
const architectureNodes = [
  { id: 'router', data: { label: 'Router' }, position: { x: 100, y: 50 } },
  { id: 'mesh', data: { label: 'Cognitive Mesh' }, position: { x: 300, y: 50 } },
  { id: 'services', data: { label: 'Reasoning' }, position: { x: 500, y: 50 } },
  { id: 'guardian', data: { label: 'Guardian' }, position: { x: 400, y: 150 } },
];

const highlightActiveLayer = (currentStep: string) => {
  // Highlight the node corresponding to current step
};
```

## Troubleshooting

### Execution Trace Empty
- Check `reasoningChain` in QueryResponse
- Verify backend is returning steps

### Timing Information Missing
- Current API doesn't include duration
- Use simulated timing (0.5s per step)
