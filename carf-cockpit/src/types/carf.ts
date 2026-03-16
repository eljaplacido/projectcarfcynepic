// Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
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
export type SlashCommand = '/analyze' | '/question' | '/query' | '/analysis' | '/history' | '/help' | '/benchmark' | '/summary' | '/goto';

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

// Phase 7: View Modes (+ Phase 16: Governance)
export type ViewMode = 'analyst' | 'developer' | 'executive' | 'governance';

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

// Phase 16: Governance Types
export interface ContextTriple {
    triple_id: string;
    subject: string;
    predicate: string;
    object: string;
    domain_source: string;
    domain_target: string;
    confidence: number;
    evidence_type: string;
    session_id?: string;
    created_at?: string;
}

export interface GovernanceDomain {
    domain_id: string;
    display_name: string;
    description: string;
    owner_email: string;
    policy_namespace: string;
    tags: string[];
    color: string;
}

export interface FederatedPolicyRule {
    rule_id: string;
    name: string;
    condition: Record<string, unknown>;
    constraint: Record<string, unknown>;
    message: string;
    severity: string;
}

export interface FederatedPolicyInfo {
    policy_id: string;
    name: string;
    domain_id: string;
    namespace: string;
    description: string;
    rules: FederatedPolicyRule[];
    priority: number;
    is_active: boolean;
    version: string;
    tags: string[];
}

export interface PolicyConflict {
    conflict_id: string;
    policy_a_id: string;
    policy_a_name: string;
    policy_a_domain: string;
    policy_b_id: string;
    policy_b_name: string;
    policy_b_domain: string;
    conflict_type: string;
    severity: string;
    description: string;
    resolution?: string | null;
    resolved_at?: string | null;
}

export interface CostBreakdownItem {
    category: string;
    label: string;
    amount: number;
    unit: string;
    details: Record<string, unknown>;
}

export interface CostBreakdown {
    session_id?: string;
    llm_token_cost: number;
    llm_tokens_used: number;
    llm_input_tokens: number;
    llm_output_tokens: number;
    llm_provider: string;
    compute_time_ms: number;
    risk_exposure_score: number;
    opportunity_cost: number;
    total_cost: number;
    breakdown_items: CostBreakdownItem[];
}

export interface ComplianceArticle {
    article_id: string;
    title: string;
    score: number;
    status: string;
    evidence: string[];
    gaps: string[];
}

export interface ComplianceScore {
    framework: string;
    overall_score: number;
    articles: ComplianceArticle[];
    gaps: string[];
    recommendations: string[];
}

export interface GovernanceAuditEntry {
    entry_id: string;
    event_type: string;
    actor: string;
    affected_domains: string[];
    details: Record<string, unknown>;
    session_id?: string;
    timestamp: string;
}

export interface GovernanceHealth {
    enabled: boolean;
    neo4j_available: boolean;
    domains_count: number;
    policies_count: number;
    active_conflicts: number;
    triples_count: number;
    status: string;
}

export interface GovernanceSemanticNode {
    node_id: string;
    label: string;
    node_type: 'domain' | 'policy' | 'concept' | string;
    domain_id?: string | null;
    metadata?: Record<string, unknown>;
}

export interface GovernanceSemanticEdge {
    edge_id: string;
    source: string;
    target: string;
    relation: string;
    confidence: number;
    metadata?: Record<string, unknown>;
}

export interface GovernanceSemanticGraph {
    generated_at: string;
    board_id?: string | null;
    session_id?: string | null;
    nodes: GovernanceSemanticNode[];
    edges: GovernanceSemanticEdge[];
    stats: Record<string, unknown>;
    explainability: {
        why_this?: string;
        how_confident?: number;
        based_on?: string[];
    };
}

// Phase 17: Governance Board Types
export interface BoardMember {
    user_id: string;
    name: string;
    email: string;
    role: 'owner' | 'approver' | 'member' | 'observer';
}

export interface ComplianceFrameworkConfig {
    framework: string;
    enabled: boolean;
    target_score: number;
    custom_articles: ComplianceArticle[];
    custom_weights: Record<string, number>;
}

export interface GovernanceBoard {
    board_id: string;
    name: string;
    description: string;
    template_id?: string | null;
    domain_ids: string[];
    policy_namespaces: string[];
    compliance_configs: ComplianceFrameworkConfig[];
    members: BoardMember[];
    tags: string[];
    is_active: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface BoardTemplate {
    template_id: string;
    name: string;
    description: string;
    domain_ids: string[];
    frameworks: string[];
    tags: string[];
}

export interface PolicyExtractionResult {
    source_name: string;
    target_domain?: string | null;
    rules_extracted: number;
    methodology?: string;
    extraction_confidence_avg?: number;
    explainability?: {
        why_this?: string;
        how_confident?: number;
        based_on?: string[];
    };
    rules: Array<{
        name: string;
        condition: Record<string, unknown>;
        constraint: Record<string, unknown>;
        message: string;
        severity: string;
        confidence?: number;
        rationale?: string;
        evidence?: string[];
    }>;
    error?: string | null;
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

// =============================================================================
// Phase 17: Causal World Models, Counterfactual Reasoning, Neurosymbolic AI
// =============================================================================

// Counterfactual Reasoning
export interface CounterfactualEvidence {
    factualOutcome: string;
    counterfactualOutcome: string;
    interventionDescription: string;
    causalAttributions: CausalAttribution[];
    confidence: number;
    narrative: string;
    reasoningSteps: string[];
}

export interface CausalAttribution {
    cause: string;
    importance: number; // 0-1
    butForResult: boolean; // Would outcome change without this cause?
    description: string;
}

export interface CounterfactualRequest {
    query: string;
    context?: Record<string, unknown>;
    datasetId?: string;
}

export interface CounterfactualResponse {
    factual_outcome: string;
    counterfactual_outcome: string;
    causal_attribution: CausalAttribution[];
    confidence: number;
    narrative: string;
    reasoning_steps: string[];
}

export interface ScenarioComparisonRequest {
    base_query: string;
    alternative_interventions: Record<string, number>[];
    outcome_variable: string;
    context?: Record<string, unknown>;
}

export interface ScenarioComparisonResponse {
    scenarios: ScenarioOutcome[];
    best_scenario_index: number;
    ranking_rationale: string;
    outcome_range: [number, number];
}

export interface ScenarioOutcome {
    intervention: Record<string, number>;
    predicted_outcome: number;
    confidence: number;
    narrative: string;
}

// World Model Simulation
export interface WorldModelSimulationRequest {
    query: string;
    initial_conditions: Record<string, number>;
    interventions: Record<string, number>;
    steps: number;
    dataset_id?: string;
    context?: Record<string, unknown>;
}

export interface WorldModelSimulationResponse {
    trajectory: Record<string, number>[];
    variables: string[];
    interventions_applied: Record<string, number>;
    model_confidence: number;
    interpretation: string;
}

// Neurosymbolic Reasoning
export interface NeurosymbolicEvidence {
    conclusion: string;
    derivedFactsCount: number;
    rulesFired: string[];
    shortcutWarnings: string[];
    groundingSource: string;
    iterations: number;
    confidence: number;
}

export interface SymbolicFact {
    entity: string;
    attribute: string;
    value: string;
    confidence: number;
    source: string;
}

export interface NeurosymbolicReasoningRequest {
    query: string;
    context?: Record<string, unknown>;
    use_knowledge_graph?: boolean;
    max_iterations?: number;
}

export interface NeurosymbolicReasoningResponse {
    conclusion: string;
    derived_facts: SymbolicFact[];
    rule_chain: string[];
    shortcut_warnings: string[];
    iterations: number;
    confidence: number;
    symbolic_grounding: SymbolicFact[];
}

// Deep Analysis (combined pipeline)
export interface DeepAnalysisRequest {
    query: string;
    context?: Record<string, unknown>;
    include_counterfactual?: boolean;
    include_neurosymbolic?: boolean;
    include_simulation?: boolean;
}

export interface DeepAnalysisResponse {
    query: string;
    carf?: {
        domain: CynefinDomain;
        domain_confidence: number;
        response: string | null;
        verdict: string | null;
        confidence: string;
        causal_evidence?: CausalAnalysisResult;
        bayesian_evidence?: BayesianBeliefState;
    };
    counterfactual?: {
        factual: string;
        counterfactual: string;
        confidence: number;
        narrative: string;
        error?: string;
    };
    neurosymbolic?: {
        conclusion: string;
        derived_facts_count: number;
        shortcut_warnings: string[];
        iterations: number;
        confidence: number;
        error?: string;
    };
    simulation?: {
        trajectory_length: number;
        variables: string[];
        confidence: number;
        interpretation: string;
        error?: string;
    };
}

// =============================================================================
// Phase 18: Monitoring Types
// =============================================================================

export interface DriftSnapshot {
  timestamp: string;
  window_size: number;
  current_distribution: Record<string, number>;
  baseline_distribution: Record<string, number>;
  kl_divergence: number;
  max_domain_shift: number;
  shifted_domain: string;
  drift_detected: boolean;
  alert_reason: string;
}

export interface DriftStatus {
  total_observations: number;
  baseline_established: boolean;
  baseline_distribution: Record<string, number>;
  current_distribution: Record<string, number>;
  alert_count: number;
  snapshot_count: number;
  last_snapshot: DriftSnapshot | null;
  config: { baseline_window: number; detection_window: number; kl_threshold: number; domain_shift_threshold: number };
}

export interface BiasReport {
  timestamp: string;
  total_entries: number;
  domain_distribution: Record<string, number>;
  domain_percentages: Record<string, number>;
  chi_squared_statistic: number;
  chi_squared_p_value: number;
  distribution_biased: boolean;
  quality_by_domain: Record<string, { mean: number; count: number; min: number; max: number }>;
  quality_disparity: number;
  quality_biased: boolean;
  verdict_by_domain: Record<string, Record<string, number>>;
  approval_rate_disparity: number;
  overall_bias_detected: boolean;
  findings: string[];
}

export interface ConvergenceResult {
  epoch: number;
  accuracy_delta: number;
  converged: boolean;
  regressed: boolean;
  plateau_detected: boolean;
  recommendation: string;
  history: Array<{ epoch: number; accuracy: number; timestamp: string }>;
}

export interface ConvergenceStatus {
  total_epochs: number;
  convergence: ConvergenceResult;
  config: { epsilon: number; max_plateau_epochs: number };
}

export interface MonitoringStatus {
  drift: DriftStatus;
  bias: { overall_bias_detected: boolean; findings_count: number; findings: string[] };
  convergence: ConvergenceStatus;
}
