---
description: Generate why-based explanations for UI components (CynefinRouter, BayesianPanel, CausalDAG)
---

# CARF Explainability Generator Skill

## Purpose
Generate human-readable explanations for all analysis components, answering "Why?" for every decision and metric displayed.

## When to Use
- Adding "Why this classification?" to CynefinRouter
- Explaining uncertainty in BayesianPanel
- Providing node/edge explanations in CausalDAG
- Generating improvement suggestions

## Component Explanation Templates

### CynefinRouter Explanation

**Data Required from Backend:**
```typescript
interface CynefinExplanation {
  domain: CynefinDomain;
  confidence: number;
  keyIndicators: string[];
  alternativeDomains: {
    domain: CynefinDomain;
    confidence: number;
    reason: string; // Why NOT this domain
  }[];
  decisionPath: string;
}
```

**Template:**
```
Domain: {domain} ({confidence}%)

📖 Why this classification?

Key indicators detected:
• {indicator_1}
• {indicator_2}
• {indicator_3}

Why not {alternative_domain}?
• {reason}
```

### BayesianPanel Explanation

**Data Available (from BayesianResult):**
- `epistemic_uncertainty`: Model doesn't have enough data
- `aleatoric_uncertainty`: Natural randomness (cannot reduce)
- `recommended_probe`: Suggested action to reduce uncertainty

**Template:**
```
Uncertainty Breakdown

📊 Why this matters:

Epistemic ({epistemic}%): Model doesn't have enough data.
↳ {recommendation to reduce}

Aleatoric ({aleatoric}%): Natural randomness in the system.
↳ Cannot reduce with more data.

💡 Recommended Probe:
"{recommended_probe}"
```

### CausalDAG Node Explanation

**Data Required:**
```typescript
interface DAGNodeExplanation {
  role: 'treatment' | 'outcome' | 'confounder' | 'mediator';
  whyIncluded: string;
  dataEvidence: string;
  canIntervene: boolean;
  whatIf: string;
}
```

**Template:**
```
Node: {label} ({role})

📊 Why included?
{whyIncluded}

📈 Data Evidence:
Correlation: {correlation}, p={pValue}

🎯 Can you intervene?
{canIntervene ? "Yes - this is actionable" : "No - this is a confounding factor"}

🔮 What if changed by 10%?
{whatIf}
```

## LLM Prompt for Dynamic Explanations

```
You are a CARF explainability assistant. Given the analysis result:

Domain: {domain}
Confidence: {confidence}
Entropy: {entropy}
Key Variables: {variables}

Generate a human-readable explanation for:
1. Why this domain classification (2-3 key indicators)
2. Why NOT the nearest alternative domain
3. One concrete suggestion to improve confidence
```

## Backend Alignment

| Explanation Need | Backend Source | Status |
|------------------|----------------|--------|
| Domain confidence | `domain_confidence` in QueryResponse | ✅ Available |
| Domain entropy | `domain_entropy` in QueryResponse | ✅ Available |
| Epistemic uncertainty | `bayesian_result.epistemic_uncertainty` | ✅ Available |
| Aleatoric uncertainty | `bayesian_result.aleatoric_uncertainty` | ✅ Available |
| Recommended probe | `bayesian_result.recommended_probe` | ✅ Available |
| Why classification | - | ⚠️ Need LLM generation |
| Why not alternatives | - | ⚠️ Need LLM generation |
| DAG node roles | DAG structure | ✅ Available |

## Frontend Types Alignment

From `carf.ts`:
```typescript
export interface BayesianBeliefState {
  epistemicUncertainty: number; // 0-1 ✅
  aleatoricUncertainty: number; // 0-1 ✅
  totalUncertainty: number;     // 0-1 ✅
  recommendedProbe?: string;    // ✅
}
```

## Verification

After implementing explanations:
1. Submit query → check CynefinRouter shows "Why?" section
2. Check BayesianPanel shows epistemic vs aleatoric breakdown
3. Click DAG node → verify explanation popup appears
4. Verify LLM-generated explanations are contextual
