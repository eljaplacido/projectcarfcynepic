// CARF TypeScript Type Definitions
// Aligned with backend API schemas

export type CynefinDomain = 'clear' | 'complicated' | 'complex' | 'chaotic' | 'disorder';
export type GuardianVerdict = 'approved' | 'rejected' | 'requires_human_approval';
export type ConfidenceLevel = 'high' | 'medium' | 'low';

export interface CynefinClassification {
    domain: CynefinDomain;
    confidence: number; // 0-1
    entropy: number; // 0-1
    solver: string;
    reasoning: string;
    scores: Record<CynefinDomain, number>;
}

export interface DAGNode {
    id: string;
    label: string;
    type: 'variable' | 'confounder' | 'intervention' | 'outcome';
    position: { x: number; y: number };
    value?: number;
    unit?: string;
}

export interface DAGEdge {
    id: string;
    source: string;
    target: string;
    effectSize: number;
    pValue: number;
    validated: boolean;
    confounders?: string[];
}

export interface CausalDAG {
    nodes: DAGNode[];
    edges: DAGEdge[];
    backdoorPaths?: string[][];
}

export interface RefutationTest {
    name: string;
    passed: boolean;
    pValue: number;
}

export interface Confounder {
    name: string;
    controlled: boolean;
}

export interface CausalAnalysisResult {
    effect: number;
    unit: string;
    pValue: number | null;
    confidenceInterval: [number, number];
    description: string;
    refutationsPassed: number;
    refutationsTotal: number;
    refutationDetails: RefutationTest[];
    confoundersControlled: Confounder[];
    evidenceBase: string;
    metaAnalysis: boolean;
    studies: number;
    treatment: string;
    outcome: string;
}

export interface BayesianBeliefState {
    variable: string;
    priorMean: number;
    priorStd: number;
    posteriorMean: number;
    posteriorStd: number;
    confidenceLevel: ConfidenceLevel;
    interpretation: string;
    epistemicUncertainty: number; // 0-1
    aleatoricUncertainty: number; // 0-1
    totalUncertainty: number; // 0-1
    observations?: Array<{ time: string; value: number }>;
    recommendedProbe?: string;
}

export interface PolicyViolation {
    id: string;
    name: string;
    description: string;
    status: 'passed' | 'failed' | 'warning';
    version: string;
    details?: string;
    severity?: 'low' | 'medium' | 'high' | 'critical';
}

export interface ProposedAction {
    type: string;
    target: string;
    amount: number;
    unit: string;
    expectedEffect: string;
}

export interface GuardianDecision {
    overallStatus: 'pass' | 'fail' | 'pending';
    proposedAction: ProposedAction;
    policies: PolicyViolation[];
    requiresHumanApproval: boolean;
    riskLevel?: 'low' | 'medium' | 'high';
    policiesPassed?: number;
    policiesTotal?: number;
}

export interface ReasoningStep {
    node: string;
    action: string;
    confidence: string;
    timestamp: string;
    durationMs: number;
    input?: Record<string, unknown>;
    output?: Record<string, unknown>;
    status?: 'completed' | 'in_progress' | 'pending';
}

export interface QueryResponse {
    sessionId: string;
    domain: CynefinDomain;
    domainConfidence: number;
    domainEntropy: number;
    guardianVerdict: GuardianVerdict | null;
    response: string | null;
    requiresHuman: boolean;
    reasoningChain: ReasoningStep[];
    causalResult: CausalAnalysisResult | null;
    bayesianResult: BayesianBeliefState | null;
    guardianResult: GuardianDecision | null;
    error: string | null;
    keyInsights?: string[];
    nextSteps?: string[];
    // Router transparency fields (Phase 11)
    routerReasoning?: string | null;
    routerKeyIndicators?: string[];
    domainScores?: Record<string, number>;
    triggeredMethod?: string | null;
    context?: Record<string, unknown>; // Analysis context for data layer inspection
}

export interface ScenarioMetadata {
    id: string;
    name: string;
    description: string;
    payload_path: string;
    emoji?: string;
    domain?: CynefinDomain;
    suggested_queries?: string[];
}

export interface ScenarioPayload {
    query: string;
    context?: Record<string, unknown>;
    causalEstimation?: Record<string, unknown>;
    bayesianInference?: Record<string, unknown>;
}

// Phase 7: Analysis History
export interface AnalysisSession {
    id: string;
    timestamp: string;
    query: string;
    scenarioId?: string;
    domain: CynefinDomain;
    confidence: number;
    result: QueryResponse;
    duration: number; // ms
    tags?: string[];
}

// Phase 7: Slash Commands
export type SlashCommand = '/analyze' | '/question' | '/query' | '/analysis' | '/history' | '/help' | '/benchmark';

export interface SlashCommandConfig {
    command: SlashCommand;
    description: string;
    usage: string;
    example: string;
}

// Phase 7: Counterfactual Intervention
export interface InterventionRequest {
    nodeId: string;
    newValue: number;
    currentValue: number;
    dag: CausalDAG;
}

// Phase 7: Developer View Extended Trace
export interface ExecutionTraceStep extends ReasoningStep {
    timestamp: string;
    durationMs: number;
    layer: 'router' | 'mesh' | 'services' | 'guardian';
    metadata?: Record<string, unknown>;
}

// Phase 7: View Modes
export type ViewMode = 'analyst' | 'developer' | 'executive';

// Phase 7: Cynefin Explanation
export interface CynefinExplanation {
    domain: CynefinDomain;
    keyIndicators: string[];
    alternativeDomains: {
        domain: CynefinDomain;
        confidence: number;
        reason: string;
    }[];
    decisionPath: string;
}

// Phase 7: Chat Message Types
export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    confidence?: ConfidenceLevel;
    linkedPanel?: string;
    isSlashCommand?: boolean;
    commandType?: SlashCommand;
}

// Phase 7: Socratic Mode State
export interface SocraticModeState {
    isActive: boolean;
    currentStep: number;
    totalSteps: number;
    questions: string[];
    answers: string[];
    suggestions: string[];
}
