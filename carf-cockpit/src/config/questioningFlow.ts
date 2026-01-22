/**
 * Socratic Questioning Flow Configuration
 *
 * Defines the step-by-step questioning process that guides users
 * through understanding CARF analysis results.
 */

export type HighlightTarget =
  | 'cynefin-panel'
  | 'causal-panel'
  | 'bayesian-panel'
  | 'guardian-panel'
  | 'dag-viewer'
  | 'domain-badge'
  | 'confidence-indicator'
  | 'effect-estimate'
  | 'uncertainty-chart'
  | 'policy-list';

export interface QuestioningStep {
  id: string;
  phase: 'orientation' | 'exploration' | 'deepening' | 'synthesis';
  question: string;
  hint?: string;
  highlightTargets: HighlightTarget[];
  expectedTopics: string[];
  followUpQuestions: string[];
  conceptExplanation: string;
  relatedPanels: string[];
}

export interface QuestioningFlow {
  id: string;
  name: string;
  description: string;
  triggerConditions: {
    domain?: string;
    hasUncertainty?: boolean;
    hasCausalAnalysis?: boolean;
    hasBayesianAnalysis?: boolean;
  };
  steps: QuestioningStep[];
}

// Main questioning flows for different analysis types
export const QUESTIONING_FLOWS: QuestioningFlow[] = [
  {
    id: 'cynefin-orientation',
    name: 'Understanding Domain Classification',
    description: 'Guides users through understanding why their query was classified in a specific Cynefin domain',
    triggerConditions: {},
    steps: [
      {
        id: 'domain-intro',
        phase: 'orientation',
        question: "I've classified your question into a specific domain. Before I explain why, what do you think makes a problem 'complex' versus 'complicated'?",
        hint: "Think about whether experts can reliably predict outcomes",
        highlightTargets: ['cynefin-panel', 'domain-badge'],
        expectedTopics: ['predictability', 'expertise', 'cause-effect'],
        followUpQuestions: [
          "What role does uncertainty play in your thinking?",
          "Can you think of examples from your own experience?"
        ],
        conceptExplanation: "Complex problems have emergent outcomes that can't be predicted even by experts, while complicated problems have knowable solutions that experts can figure out.",
        relatedPanels: ['cynefin']
      },
      {
        id: 'domain-confidence',
        phase: 'exploration',
        question: "Notice the confidence level shown. What factors do you think might make me more or less certain about a classification?",
        hint: "Consider the clarity and specificity of the question",
        highlightTargets: ['confidence-indicator', 'cynefin-panel'],
        expectedTopics: ['ambiguity', 'context', 'specificity'],
        followUpQuestions: [
          "How might missing context affect this confidence?",
          "What additional information would help?"
        ],
        conceptExplanation: "Classification confidence depends on query clarity, available context, and how well the question maps to known domain patterns.",
        relatedPanels: ['cynefin']
      }
    ]
  },
  {
    id: 'causal-exploration',
    name: 'Understanding Causal Analysis',
    description: 'Guides users through interpreting causal effect estimates and their limitations',
    triggerConditions: {
      hasCausalAnalysis: true
    },
    steps: [
      {
        id: 'effect-meaning',
        phase: 'orientation',
        question: "We've estimated a causal effect. What do you think 'causal' means here - how is it different from correlation?",
        hint: "Think about whether changing X actually causes Y to change",
        highlightTargets: ['causal-panel', 'effect-estimate', 'dag-viewer'],
        expectedTopics: ['causation', 'correlation', 'intervention'],
        followUpQuestions: [
          "What would need to be true for this to be a real causal effect?",
          "What could make us wrong about causality?"
        ],
        conceptExplanation: "Causal effects tell us what happens when we intervene and change something, not just what tends to occur together. We use techniques to rule out confounding factors.",
        relatedPanels: ['causal', 'dag']
      },
      {
        id: 'uncertainty-bands',
        phase: 'exploration',
        question: "Look at the confidence interval around the effect. What does the width of this interval tell you about our certainty?",
        hint: "Wider intervals mean more uncertainty",
        highlightTargets: ['causal-panel', 'uncertainty-chart'],
        expectedTopics: ['confidence interval', 'uncertainty', 'sample size'],
        followUpQuestions: [
          "What would make these intervals narrower?",
          "How should this uncertainty affect decisions?"
        ],
        conceptExplanation: "Confidence intervals show the range of plausible effect sizes. Wider intervals suggest we need more data or have more variability in our observations.",
        relatedPanels: ['causal', 'bayesian']
      },
      {
        id: 'confounders',
        phase: 'deepening',
        question: "The DAG shows potential confounders. Why is it important to account for these other variables?",
        hint: "Confounders can create fake associations",
        highlightTargets: ['dag-viewer', 'causal-panel'],
        expectedTopics: ['confounding', 'bias', 'adjustment'],
        followUpQuestions: [
          "Can you think of a confounder we might have missed?",
          "How does adjusting for confounders change our estimate?"
        ],
        conceptExplanation: "Confounders are variables that affect both the treatment and outcome, creating spurious associations. We must control for them to get unbiased causal estimates.",
        relatedPanels: ['causal', 'dag']
      }
    ]
  },
  {
    id: 'bayesian-reasoning',
    name: 'Understanding Uncertainty',
    description: 'Guides users through Bayesian uncertainty quantification',
    triggerConditions: {
      hasBayesianAnalysis: true
    },
    steps: [
      {
        id: 'prior-posterior',
        phase: 'orientation',
        question: "We started with prior beliefs and updated them with data. What do you think should inform those initial beliefs?",
        hint: "Think about expert knowledge and previous studies",
        highlightTargets: ['bayesian-panel', 'uncertainty-chart'],
        expectedTopics: ['prior', 'beliefs', 'evidence', 'updating'],
        followUpQuestions: [
          "How much should prior beliefs matter compared to new data?",
          "What if experts disagree on the prior?"
        ],
        conceptExplanation: "Bayesian analysis combines prior knowledge (what we believed before) with new evidence to form posterior beliefs. This lets us incorporate domain expertise while remaining data-driven.",
        relatedPanels: ['bayesian']
      },
      {
        id: 'epistemic-aleatoric',
        phase: 'exploration',
        question: "We distinguish two types of uncertainty. What's the difference between uncertainty from limited data versus inherent randomness?",
        hint: "One can be reduced with more data, one cannot",
        highlightTargets: ['bayesian-panel', 'uncertainty-chart'],
        expectedTopics: ['epistemic', 'aleatoric', 'reducible', 'irreducible'],
        followUpQuestions: [
          "Which type of uncertainty is more relevant for your decision?",
          "How would more data change each type?"
        ],
        conceptExplanation: "Epistemic uncertainty comes from limited knowledge and can be reduced with more data. Aleatoric uncertainty is inherent randomness in the system that cannot be eliminated.",
        relatedPanels: ['bayesian']
      }
    ]
  },
  {
    id: 'guardian-policies',
    name: 'Understanding Guardrails',
    description: 'Explains why certain recommendations are flagged or modified',
    triggerConditions: {},
    steps: [
      {
        id: 'policy-purpose',
        phase: 'orientation',
        question: "The Guardian layer applies policies to recommendations. Why do you think automated analysis needs human-defined guardrails?",
        hint: "Think about edge cases and values that algorithms can't encode",
        highlightTargets: ['guardian-panel', 'policy-list'],
        expectedTopics: ['safety', 'ethics', 'oversight', 'limitations'],
        followUpQuestions: [
          "What kinds of decisions should always have human oversight?",
          "How do we balance automation with caution?"
        ],
        conceptExplanation: "Guardian policies ensure recommendations align with organizational values, ethical constraints, and domain-specific requirements that pure statistical analysis might miss.",
        relatedPanels: ['guardian']
      }
    ]
  },
  {
    id: 'synthesis-reflection',
    name: 'Synthesizing Understanding',
    description: 'Helps users integrate insights from multiple analysis components',
    triggerConditions: {
      hasCausalAnalysis: true,
      hasBayesianAnalysis: true
    },
    steps: [
      {
        id: 'integration',
        phase: 'synthesis',
        question: "We've looked at domain classification, causal effects, and uncertainty. How do these pieces fit together to inform your decision?",
        hint: "Each component addresses a different aspect of the question",
        highlightTargets: ['cynefin-panel', 'causal-panel', 'bayesian-panel'],
        expectedTopics: ['integration', 'decision-making', 'trade-offs'],
        followUpQuestions: [
          "Which insights are most relevant to your specific situation?",
          "What additional information would change your thinking?"
        ],
        conceptExplanation: "CARF provides multiple perspectives: domain classification tells you what kind of problem you have, causal analysis estimates effects, and Bayesian analysis quantifies uncertainty.",
        relatedPanels: ['cynefin', 'causal', 'bayesian', 'guardian']
      }
    ]
  }
];

// Helper to find applicable flows based on query result
export function getApplicableFlows(result: {
  domain?: string;
  hasCausalAnalysis?: boolean;
  hasBayesianAnalysis?: boolean;
  hasUncertainty?: boolean;
}): QuestioningFlow[] {
  return QUESTIONING_FLOWS.filter(flow => {
    const conditions = flow.triggerConditions;

    if (conditions.domain && conditions.domain !== result.domain) {
      return false;
    }
    if (conditions.hasCausalAnalysis && !result.hasCausalAnalysis) {
      return false;
    }
    if (conditions.hasBayesianAnalysis && !result.hasBayesianAnalysis) {
      return false;
    }
    if (conditions.hasUncertainty && !result.hasUncertainty) {
      return false;
    }

    return true;
  });
}

// Get the next step in a flow
export function getNextStep(
  flow: QuestioningFlow,
  currentStepId?: string
): QuestioningStep | null {
  if (!currentStepId) {
    return flow.steps[0] || null;
  }

  const currentIndex = flow.steps.findIndex(s => s.id === currentStepId);
  if (currentIndex === -1 || currentIndex >= flow.steps.length - 1) {
    return null;
  }

  return flow.steps[currentIndex + 1];
}

export default QUESTIONING_FLOWS;
