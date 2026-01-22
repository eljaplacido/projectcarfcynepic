import type { DAGNode, DAGEdge, CausalAnalysisResult, BayesianBeliefState, GuardianDecision, QueryResponse, ScenarioMetadata } from '../types/carf';

// Scenario Registry (matching backend demo/scenarios.json)
export const MOCK_SCENARIOS: ScenarioMetadata[] = [
    {
        id: 'scope3_attribution',
        name: 'Scope 3 Attribution',
        description: 'Analyze causal drivers of supplier Scope 3 emissions',
        payloadPath: 'demo/payloads/scope3_attribution.json',
        emoji: '🌍',
        domain: 'complicated',
    },
    {
        id: 'causal_discount_churn',
        name: 'Discount vs. Churn',
        description: 'Causal estimation of discount impact on customer churn',
        payloadPath: 'demo/payloads/causal_discount_churn.json',
        emoji: '💰',
        domain: 'complicated',
    },
    {
        id: 'grid_stability',
        name: 'Grid Stability',
        description: 'Complex systems analysis of power grid stability',
        payloadPath: 'demo/payloads/grid_stability.json',
        emoji: '⚡',
        domain: 'complex',
    },
    {
        id: 'marketing_budget',
        name: 'Marketing Budget',
        description: 'Causal attribution of marketing spend to revenue',
        payloadPath: 'demo/payloads/marketing_budget.json',
        emoji: '📈',
        domain: 'complicated',
    },
    {
        id: 'risk_exposure',
        name: 'Risk Exposure',
        description: 'Complex risk scenario analysis and mitigation',
        payloadPath: 'demo/payloads/risk_exposure.json',
        emoji: '🛡️',
        domain: 'complex',
    },
];

// Suggested queries per scenario
export const SCENARIO_QUERIES: Record<string, string[]> = {
    scope3_attribution: [
        'What drives our Scope 3 emissions?',
        'Which suppliers contribute most to emissions?',
        'How effective are supplier sustainability programs?',
    ],
    causal_discount_churn: [
        'Do discounts reduce churn?',
        'What is the causal effect of promotions?',
        'Which customers respond best to discounts?',
    ],
    grid_stability: [
        'What factors affect grid stability?',
        'How do renewable sources impact reliability?',
        'What is the optimal energy mix?',
    ],
    marketing_budget: [
        'Which channels drive the most revenue?',
        'What is the ROI of digital marketing?',
        'How should we allocate marketing spend?',
    ],
    risk_exposure: [
        'What are our key risk exposures?',
        'How do different risks correlate?',
        'What mitigation strategies are most effective?',
    ],
};

// Mock Causal DAG for Scope 3 scenario
export const MOCK_CAUSAL_DAG = {
    nodes: [
        { id: '1', label: 'Supplier Programs', type: 'intervention' as const, position: { x: 50, y: 100 } },
        { id: '2', label: 'Engagement', type: 'variable' as const, position: { x: 200, y: 50 } },
        { id: '3', label: 'Industry', type: 'confounder' as const, position: { x: 200, y: 150 } },
        { id: '4', label: 'Technology', type: 'variable' as const, position: { x: 350, y: 75 } },
        { id: '5', label: 'Scope 3 Emissions', type: 'outcome' as const, position: { x: 500, y: 100 } },
    ] as DAGNode[],
    edges: [
        { id: 'e1-2', source: '1', target: '2', effectSize: 0.42, pValue: 0.003, validated: true },
        { id: 'e2-4', source: '2', target: '4', effectSize: 0.31, pValue: 0.012, validated: true },
        { id: 'e3-2', source: '3', target: '2', effectSize: 0.18, pValue: 0.045, validated: true },
        { id: 'e3-5', source: '3', target: '5', effectSize: 0.22, pValue: 0.028, validated: true },
        { id: 'e4-5', source: '4', target: '5', effectSize: -0.38, pValue: 0.001, validated: true },
        { id: 'e1-5', source: '1', target: '5', effectSize: -0.42, pValue: 0.002, validated: true },
    ] as DAGEdge[],
};

// Mock Causal Analysis Result
export const MOCK_CAUSAL_RESULT: CausalAnalysisResult = {
    effect: -0.42,
    unit: 'tons CO2e',
    pValue: 0.002,
    confidenceInterval: [-0.68, -0.16],
    description: 'Supplier sustainability programs significantly reduce Scope 3 emissions',
    refutationsPassed: 4,
    refutationsTotal: 5,
    refutationDetails: [
        { name: 'Placebo Treatment', passed: true, pValue: 0.823 },
        { name: 'Random Common Cause', passed: true, pValue: 0.912 },
        { name: 'Data Subset Validation', passed: true, pValue: 0.876 },
        { name: 'Unobserved Confounder', passed: true, pValue: 0.654 },
        { name: 'Bootstrap Refutation', passed: false, pValue: 0.043 },
    ],
    confoundersControlled: [
        { name: 'Industry Type', controlled: true },
        { name: 'Supplier Size', controlled: true },
        { name: 'Geographic Region', controlled: false },
    ],
    evidenceBase: 'Analysis of 247 supplier relationships across 12 industries',
    metaAnalysis: false,
    studies: 1,
    treatment: 'Supplier Programs',
    outcome: 'Scope 3 Emissions',
};

// Mock Bayesian Belief State
export const MOCK_BAYESIAN_RESULT: BayesianBeliefState = {
    variable: 'Emission Reduction Effectiveness',
    priorMean: 0.25,
    priorStd: 0.15,
    posteriorMean: 0.42,
    posteriorStd: 0.08,
    confidenceLevel: 'high',
    interpretation: 'Strong evidence that supplier programs reduce emissions by ~42%',
    epistemicUncertainty: 0.19,
    aleatoricUncertainty: 0.12,
    totalUncertainty: 0.31,
    recommendedProbe: 'Collect data from 30 more suppliers in manufacturing sector',
};

// Mock Guardian Decision
export const MOCK_GUARDIAN_DECISION: GuardianDecision = {
    overallStatus: 'pass',
    proposedAction: {
        type: 'investment',
        target: 'Supplier Sustainability Program',
        amount: 500000,
        unit: 'USD',
        expectedEffect: '-0.42 tons CO2e per supplier',
    },
    policies: [
        {
            id: 'pol-001',
            name: 'Financial Threshold Check',
            description: 'Investment below $1M threshold',
            status: 'passed',
            version: 'v2.1',
        },
        {
            id: 'pol-002',
            name: 'Confidence Requirement',
            description: 'Statistical confidence above 80%',
            status: 'passed',
            version: 'v2.1',
            details: 'p-value: 0.002, Confidence: 99.8%',
        },
    ],
    requiresHumanApproval: false,
};

// Complete Mock Query Response for Scope 3
export const MOCK_QUERY_RESPONSE: QueryResponse = {
    sessionId: 'session_mock_12345',
    domain: 'complicated',
    domainConfidence: 0.87,
    domainEntropy: 0.32,
    guardianVerdict: 'approved',
    response: 'Based on causal analysis of 247 supplier relationships, implementing sustainability programs reduces Scope 3 emissions by approximately 0.42 tons CO2e per supplier (95% CI: [-0.68, -0.16], p=0.002). The effect is statistically significant and passed 4 out of 5 refutation tests.',
    requiresHuman: false,
    reasoningChain: [
        { node: 'Router', action: 'Classified as Complicated domain', confidence: 'high', timestamp: '2025-01-20T10:00:00Z', durationMs: 120 },
        { node: 'Causal Analyst', action: 'Discovered DAG with 5 nodes, 6 edges', confidence: 'high', timestamp: '2025-01-20T10:00:01Z', durationMs: 450 },
        { node: 'Causal Analyst', action: 'Estimated treatment effect', confidence: 'high', timestamp: '2025-01-20T10:00:02Z', durationMs: 380 },
        { node: 'Guardian', action: 'Policy check passed', confidence: 'high', timestamp: '2025-01-20T10:00:03Z', durationMs: 50 },
    ],
    causalResult: MOCK_CAUSAL_RESULT,
    bayesianResult: MOCK_BAYESIAN_RESULT,
    guardianResult: MOCK_GUARDIAN_DECISION,
    error: null,
    keyInsights: [
        'Supplier programs have significant causal effect on emissions',
        'Industry type is key confounder requiring control',
        'Effect robust across 4/5 refutation tests',
    ],
    nextSteps: [
        'Expand program to additional suppliers',
        'Collect data from manufacturing sector for better precision',
    ],
};

// ============================================================================
// SCENARIO-SPECIFIC MOCK DATA
// ============================================================================

// --- Discount vs Churn Scenario ---
const CHURN_CAUSAL_DAG = {
    nodes: [
        { id: '1', label: 'Discount Offered', type: 'intervention' as const, position: { x: 50, y: 100 } },
        { id: '2', label: 'Customer Tenure', type: 'confounder' as const, position: { x: 200, y: 50 } },
        { id: '3', label: 'Purchase History', type: 'variable' as const, position: { x: 200, y: 150 } },
        { id: '4', label: 'Engagement Score', type: 'variable' as const, position: { x: 350, y: 75 } },
        { id: '5', label: 'Churn', type: 'outcome' as const, position: { x: 500, y: 100 } },
    ] as DAGNode[],
    edges: [
        { id: 'e1-4', source: '1', target: '4', effectSize: 0.28, pValue: 0.008, validated: true },
        { id: 'e2-3', source: '2', target: '3', effectSize: 0.45, pValue: 0.001, validated: true },
        { id: 'e2-5', source: '2', target: '5', effectSize: -0.33, pValue: 0.004, validated: true },
        { id: 'e3-4', source: '3', target: '4', effectSize: 0.22, pValue: 0.031, validated: true },
        { id: 'e4-5', source: '4', target: '5', effectSize: -0.41, pValue: 0.002, validated: true },
        { id: 'e1-5', source: '1', target: '5', effectSize: -0.18, pValue: 0.023, validated: true },
    ] as DAGEdge[],
};

const CHURN_CAUSAL_RESULT: CausalAnalysisResult = {
    effect: -0.18,
    unit: 'probability points',
    pValue: 0.023,
    confidenceInterval: [-0.31, -0.05],
    description: 'Discount offers reduce churn probability by 18 percentage points',
    refutationsPassed: 5,
    refutationsTotal: 5,
    refutationDetails: [
        { name: 'Placebo Treatment', passed: true, pValue: 0.891 },
        { name: 'Random Common Cause', passed: true, pValue: 0.934 },
        { name: 'Data Subset Validation', passed: true, pValue: 0.812 },
        { name: 'Unobserved Confounder', passed: true, pValue: 0.723 },
        { name: 'Bootstrap Refutation', passed: true, pValue: 0.067 },
    ],
    confoundersControlled: [
        { name: 'Customer Tenure', controlled: true },
        { name: 'Purchase History', controlled: true },
        { name: 'Product Category', controlled: true },
    ],
    evidenceBase: 'Analysis of 15,847 customer accounts over 24 months',
    metaAnalysis: false,
    studies: 1,
    treatment: 'Discount Offered',
    outcome: 'Customer Churn',
};

const CHURN_BAYESIAN_RESULT: BayesianBeliefState = {
    variable: 'Discount Effectiveness on Retention',
    priorMean: 0.10,
    priorStd: 0.08,
    posteriorMean: 0.18,
    posteriorStd: 0.04,
    confidenceLevel: 'high',
    interpretation: 'Strong evidence that discounts reduce churn by ~18%',
    epistemicUncertainty: 0.14,
    aleatoricUncertainty: 0.21,
    totalUncertainty: 0.35,
    recommendedProbe: 'A/B test with 5% vs 10% discount tiers to optimize ROI',
};

const CHURN_GUARDIAN_DECISION: GuardianDecision = {
    overallStatus: 'pass',
    proposedAction: {
        type: 'campaign',
        target: 'At-Risk Customer Discount Program',
        amount: 250000,
        unit: 'USD',
        expectedEffect: '-18% churn probability for targeted segment',
    },
    policies: [
        {
            id: 'pol-001',
            name: 'Budget Allocation Check',
            description: 'Campaign budget within quarterly limits',
            status: 'passed',
            version: 'v2.1',
        },
        {
            id: 'pol-002',
            name: 'Statistical Confidence',
            description: 'Effect estimate confidence above threshold',
            status: 'passed',
            version: 'v2.1',
            details: 'p-value: 0.023, All refutations passed',
        },
    ],
    requiresHumanApproval: false,
};

const CHURN_QUERY_RESPONSE: QueryResponse = {
    sessionId: 'session_churn_67890',
    domain: 'complicated',
    domainConfidence: 0.91,
    domainEntropy: 0.28,
    guardianVerdict: 'approved',
    response: 'Causal analysis of 15,847 customer accounts shows that offering discounts reduces churn probability by 18 percentage points (95% CI: [-0.31, -0.05], p=0.023). The effect passed all 5 refutation tests, indicating a robust causal relationship. Customer tenure is the strongest confounder.',
    requiresHuman: false,
    reasoningChain: [
        { node: 'Router', action: 'Classified as Complicated domain', confidence: 'high', timestamp: '2025-01-20T10:05:00Z', durationMs: 110 },
        { node: 'Causal Analyst', action: 'Discovered DAG with 5 nodes, 6 edges', confidence: 'high', timestamp: '2025-01-20T10:05:01Z', durationMs: 420 },
        { node: 'Causal Analyst', action: 'Estimated ATE using propensity score matching', confidence: 'high', timestamp: '2025-01-20T10:05:02Z', durationMs: 390 },
        { node: 'Guardian', action: 'All policies passed', confidence: 'high', timestamp: '2025-01-20T10:05:03Z', durationMs: 45 },
    ],
    causalResult: CHURN_CAUSAL_RESULT,
    bayesianResult: CHURN_BAYESIAN_RESULT,
    guardianResult: CHURN_GUARDIAN_DECISION,
    error: null,
    keyInsights: [
        'Discounts causally reduce churn by 18 percentage points',
        'Effect strongest for customers with 6-12 months tenure',
        'Engagement score mediates 60% of the discount effect',
    ],
    nextSteps: [
        'Implement targeted discount program for at-risk segment',
        'Test different discount levels (5%, 10%, 15%) for ROI optimization',
    ],
};

// --- Grid Stability Scenario ---
const GRID_CAUSAL_DAG = {
    nodes: [
        { id: '1', label: 'Renewable %', type: 'intervention' as const, position: { x: 50, y: 100 } },
        { id: '2', label: 'Weather Variance', type: 'confounder' as const, position: { x: 200, y: 50 } },
        { id: '3', label: 'Storage Capacity', type: 'variable' as const, position: { x: 200, y: 150 } },
        { id: '4', label: 'Load Balancing', type: 'variable' as const, position: { x: 350, y: 75 } },
        { id: '5', label: 'Grid Stability', type: 'outcome' as const, position: { x: 500, y: 100 } },
    ] as DAGNode[],
    edges: [
        { id: 'e1-4', source: '1', target: '4', effectSize: -0.25, pValue: 0.015, validated: true },
        { id: 'e2-1', source: '2', target: '1', effectSize: 0.35, pValue: 0.003, validated: true },
        { id: 'e2-5', source: '2', target: '5', effectSize: -0.28, pValue: 0.009, validated: true },
        { id: 'e3-4', source: '3', target: '4', effectSize: 0.52, pValue: 0.001, validated: true },
        { id: 'e4-5', source: '4', target: '5', effectSize: 0.61, pValue: 0.001, validated: true },
        { id: 'e1-5', source: '1', target: '5', effectSize: -0.15, pValue: 0.045, validated: false },
    ] as DAGEdge[],
};

const GRID_CAUSAL_RESULT: CausalAnalysisResult = {
    effect: -0.15,
    unit: 'stability index points',
    pValue: 0.045,
    confidenceInterval: [-0.29, -0.01],
    description: 'Each 10% increase in renewable energy reduces grid stability by 0.15 index points',
    refutationsPassed: 3,
    refutationsTotal: 5,
    refutationDetails: [
        { name: 'Placebo Treatment', passed: true, pValue: 0.756 },
        { name: 'Random Common Cause', passed: true, pValue: 0.821 },
        { name: 'Data Subset Validation', passed: false, pValue: 0.038 },
        { name: 'Unobserved Confounder', passed: true, pValue: 0.512 },
        { name: 'Bootstrap Refutation', passed: false, pValue: 0.041 },
    ],
    confoundersControlled: [
        { name: 'Weather Variance', controlled: true },
        { name: 'Peak Load Hours', controlled: true },
        { name: 'Maintenance Schedule', controlled: false },
    ],
    evidenceBase: 'Analysis of 3 years of grid operation data across 45 substations',
    metaAnalysis: false,
    studies: 1,
    treatment: 'Renewable Energy Percentage',
    outcome: 'Grid Stability Index',
};

const GRID_BAYESIAN_RESULT: BayesianBeliefState = {
    variable: 'Renewable Impact on Stability',
    priorMean: -0.20,
    priorStd: 0.12,
    posteriorMean: -0.15,
    posteriorStd: 0.07,
    confidenceLevel: 'medium',
    interpretation: 'Moderate evidence of negative impact, but storage capacity can compensate',
    epistemicUncertainty: 0.31,
    aleatoricUncertainty: 0.24,
    totalUncertainty: 0.55,
    recommendedProbe: 'Pilot increased storage at 5 substations to validate mitigation effect',
};

const GRID_GUARDIAN_DECISION: GuardianDecision = {
    overallStatus: 'pending',
    proposedAction: {
        type: 'infrastructure',
        target: 'Grid Modernization with Storage',
        amount: 15000000,
        unit: 'USD',
        expectedEffect: 'Maintain stability with 40% renewable mix',
    },
    policies: [
        {
            id: 'pol-001',
            name: 'Infrastructure Investment Threshold',
            description: 'Requires board approval for investments > $10M',
            status: 'warning',
            version: 'v2.1',
        },
        {
            id: 'pol-002',
            name: 'Statistical Robustness',
            description: 'Only 3/5 refutation tests passed',
            status: 'warning',
            version: 'v2.1',
            details: 'Recommend additional validation before major investment',
        },
    ],
    requiresHumanApproval: true,
};

const GRID_QUERY_RESPONSE: QueryResponse = {
    sessionId: 'session_grid_11111',
    domain: 'complex',
    domainConfidence: 0.78,
    domainEntropy: 0.45,
    guardianVerdict: 'requires_human_approval',
    response: 'Analysis of 3 years of grid data shows increasing renewable energy percentage has a small negative effect on stability (-0.15 index points per 10%, p=0.045). However, this effect is moderated by storage capacity - substations with adequate storage show no stability degradation. Recommend pilot program before large-scale investment.',
    requiresHuman: true,
    reasoningChain: [
        { node: 'Router', action: 'Classified as Complex domain (emergent behavior)', confidence: 'medium', timestamp: '2025-01-20T10:10:00Z', durationMs: 130 },
        { node: 'Bayesian Explorer', action: 'High epistemic uncertainty detected', confidence: 'medium', timestamp: '2025-01-20T10:10:02Z', durationMs: 850 },
        { node: 'Causal Analyst', action: 'Identified storage as key moderator', confidence: 'medium', timestamp: '2025-01-20T10:10:03Z', durationMs: 620 },
        { node: 'Guardian', action: 'Escalating for human review', confidence: 'high', timestamp: '2025-01-20T10:10:04Z', durationMs: 60 },
    ],
    causalResult: GRID_CAUSAL_RESULT,
    bayesianResult: GRID_BAYESIAN_RESULT,
    guardianResult: GRID_GUARDIAN_DECISION,
    error: null,
    keyInsights: [
        'Renewable energy has modest negative effect on stability without storage',
        'Storage capacity is key moderating factor (+0.52 correlation with stability)',
        'Weather variance is strongest confounder - must be controlled',
    ],
    nextSteps: [
        'Pilot storage upgrades at 5 substations before full rollout',
        'Collect more data during high weather variance periods',
    ],
};

// --- Marketing Budget Scenario ---
const MARKETING_CAUSAL_DAG = {
    nodes: [
        { id: '1', label: 'Digital Spend', type: 'intervention' as const, position: { x: 50, y: 75 } },
        { id: '2', label: 'TV Spend', type: 'intervention' as const, position: { x: 50, y: 150 } },
        { id: '3', label: 'Brand Awareness', type: 'variable' as const, position: { x: 250, y: 50 } },
        { id: '4', label: 'Web Traffic', type: 'variable' as const, position: { x: 250, y: 125 } },
        { id: '5', label: 'Conversions', type: 'variable' as const, position: { x: 400, y: 100 } },
        { id: '6', label: 'Revenue', type: 'outcome' as const, position: { x: 550, y: 100 } },
    ] as DAGNode[],
    edges: [
        { id: 'e1-4', source: '1', target: '4', effectSize: 0.68, pValue: 0.001, validated: true },
        { id: 'e1-5', source: '1', target: '5', effectSize: 0.45, pValue: 0.002, validated: true },
        { id: 'e2-3', source: '2', target: '3', effectSize: 0.55, pValue: 0.001, validated: true },
        { id: 'e3-4', source: '3', target: '4', effectSize: 0.32, pValue: 0.012, validated: true },
        { id: 'e4-5', source: '4', target: '5', effectSize: 0.41, pValue: 0.003, validated: true },
        { id: 'e5-6', source: '5', target: '6', effectSize: 0.78, pValue: 0.001, validated: true },
    ] as DAGEdge[],
};

const MARKETING_CAUSAL_RESULT: CausalAnalysisResult = {
    effect: 3.2,
    unit: 'ROI multiplier',
    pValue: 0.001,
    confidenceInterval: [2.4, 4.0],
    description: 'Each $1 of digital marketing spend generates $3.20 in revenue',
    refutationsPassed: 5,
    refutationsTotal: 5,
    refutationDetails: [
        { name: 'Placebo Treatment', passed: true, pValue: 0.923 },
        { name: 'Random Common Cause', passed: true, pValue: 0.887 },
        { name: 'Data Subset Validation', passed: true, pValue: 0.912 },
        { name: 'Unobserved Confounder', passed: true, pValue: 0.834 },
        { name: 'Bootstrap Refutation', passed: true, pValue: 0.076 },
    ],
    confoundersControlled: [
        { name: 'Seasonality', controlled: true },
        { name: 'Competitor Activity', controlled: true },
        { name: 'Product Launches', controlled: true },
    ],
    evidenceBase: 'Marketing mix model on 36 months of campaign data',
    metaAnalysis: false,
    studies: 1,
    treatment: 'Digital Marketing Spend',
    outcome: 'Revenue',
};

const MARKETING_BAYESIAN_RESULT: BayesianBeliefState = {
    variable: 'Digital Marketing ROI',
    priorMean: 2.5,
    priorStd: 0.8,
    posteriorMean: 3.2,
    posteriorStd: 0.4,
    confidenceLevel: 'high',
    interpretation: 'Digital marketing delivers 3.2x ROI, exceeding industry benchmarks',
    epistemicUncertainty: 0.12,
    aleatoricUncertainty: 0.18,
    totalUncertainty: 0.30,
    recommendedProbe: 'Test 20% budget increase in top-performing channels',
};

const MARKETING_GUARDIAN_DECISION: GuardianDecision = {
    overallStatus: 'pass',
    proposedAction: {
        type: 'budget_reallocation',
        target: 'Shift 15% from TV to Digital',
        amount: 450000,
        unit: 'USD',
        expectedEffect: '+$1.44M incremental revenue',
    },
    policies: [
        {
            id: 'pol-001',
            name: 'Budget Reallocation Limit',
            description: 'Within 20% reallocation threshold',
            status: 'passed',
            version: 'v2.1',
        },
        {
            id: 'pol-002',
            name: 'Statistical Confidence',
            description: 'High confidence in effect estimate',
            status: 'passed',
            version: 'v2.1',
            details: 'All 5 refutation tests passed, p < 0.001',
        },
    ],
    requiresHumanApproval: false,
};

const MARKETING_QUERY_RESPONSE: QueryResponse = {
    sessionId: 'session_mktg_22222',
    domain: 'complicated',
    domainConfidence: 0.93,
    domainEntropy: 0.21,
    guardianVerdict: 'approved',
    response: 'Marketing mix analysis of 36 months of campaign data shows digital marketing delivers a 3.2x ROI (95% CI: [2.4, 4.0], p<0.001). TV advertising shows 1.8x ROI through brand awareness lift. Recommend shifting 15% of TV budget to digital channels for +$1.44M incremental revenue.',
    requiresHuman: false,
    reasoningChain: [
        { node: 'Router', action: 'Classified as Complicated domain', confidence: 'high', timestamp: '2025-01-20T10:15:00Z', durationMs: 115 },
        { node: 'Causal Analyst', action: 'Built marketing attribution DAG', confidence: 'high', timestamp: '2025-01-20T10:15:01Z', durationMs: 480 },
        { node: 'Causal Analyst', action: 'Estimated channel-level ROI', confidence: 'high', timestamp: '2025-01-20T10:15:02Z', durationMs: 410 },
        { node: 'Guardian', action: 'Budget reallocation approved', confidence: 'high', timestamp: '2025-01-20T10:15:03Z', durationMs: 55 },
    ],
    causalResult: MARKETING_CAUSAL_RESULT,
    bayesianResult: MARKETING_BAYESIAN_RESULT,
    guardianResult: MARKETING_GUARDIAN_DECISION,
    error: null,
    keyInsights: [
        'Digital marketing ROI (3.2x) significantly exceeds TV (1.8x)',
        'Web traffic is key mediator - 68% of digital effect flows through it',
        'Seasonality controlled - results stable across quarters',
    ],
    nextSteps: [
        'Implement 15% budget shift from TV to digital',
        'Set up incrementality testing for ongoing optimization',
    ],
};

// --- Risk Exposure Scenario ---
const RISK_CAUSAL_DAG = {
    nodes: [
        { id: '1', label: 'Market Risk', type: 'variable' as const, position: { x: 50, y: 50 } },
        { id: '2', label: 'Credit Risk', type: 'variable' as const, position: { x: 50, y: 150 } },
        { id: '3', label: 'Liquidity', type: 'confounder' as const, position: { x: 200, y: 100 } },
        { id: '4', label: 'Hedging', type: 'intervention' as const, position: { x: 350, y: 50 } },
        { id: '5', label: 'Portfolio VaR', type: 'outcome' as const, position: { x: 500, y: 100 } },
    ] as DAGNode[],
    edges: [
        { id: 'e1-3', source: '1', target: '3', effectSize: -0.35, pValue: 0.004, validated: true },
        { id: 'e1-5', source: '1', target: '5', effectSize: 0.52, pValue: 0.001, validated: true },
        { id: 'e2-3', source: '2', target: '3', effectSize: -0.28, pValue: 0.011, validated: true },
        { id: 'e2-5', source: '2', target: '5', effectSize: 0.38, pValue: 0.002, validated: true },
        { id: 'e3-5', source: '3', target: '5', effectSize: -0.22, pValue: 0.023, validated: true },
        { id: 'e4-5', source: '4', target: '5', effectSize: -0.45, pValue: 0.001, validated: true },
    ] as DAGEdge[],
};

const RISK_CAUSAL_RESULT: CausalAnalysisResult = {
    effect: -0.45,
    unit: 'VaR reduction %',
    pValue: 0.001,
    confidenceInterval: [-0.58, -0.32],
    description: 'Hedging strategy reduces portfolio VaR by 45%',
    refutationsPassed: 4,
    refutationsTotal: 5,
    refutationDetails: [
        { name: 'Placebo Treatment', passed: true, pValue: 0.912 },
        { name: 'Random Common Cause', passed: true, pValue: 0.856 },
        { name: 'Data Subset Validation', passed: true, pValue: 0.789 },
        { name: 'Unobserved Confounder', passed: false, pValue: 0.042 },
        { name: 'Bootstrap Refutation', passed: true, pValue: 0.067 },
    ],
    confoundersControlled: [
        { name: 'Liquidity Conditions', controlled: true },
        { name: 'Interest Rate Environment', controlled: true },
        { name: 'Counterparty Exposure', controlled: false },
    ],
    evidenceBase: 'Analysis of 5 years of portfolio data across market regimes',
    metaAnalysis: false,
    studies: 1,
    treatment: 'Hedging Strategy',
    outcome: 'Portfolio Value at Risk',
};

const RISK_BAYESIAN_RESULT: BayesianBeliefState = {
    variable: 'Hedging Effectiveness',
    priorMean: -0.30,
    priorStd: 0.15,
    posteriorMean: -0.45,
    posteriorStd: 0.07,
    confidenceLevel: 'high',
    interpretation: 'Strong evidence hedging reduces VaR by 45%, robust across regimes',
    epistemicUncertainty: 0.18,
    aleatoricUncertainty: 0.25,
    totalUncertainty: 0.43,
    recommendedProbe: 'Stress test against 2008-style correlation breakdown',
};

const RISK_GUARDIAN_DECISION: GuardianDecision = {
    overallStatus: 'pass',
    proposedAction: {
        type: 'risk_management',
        target: 'Expand Hedging Program',
        amount: 2500000,
        unit: 'USD hedge notional',
        expectedEffect: '-45% portfolio VaR',
    },
    policies: [
        {
            id: 'pol-001',
            name: 'Risk Limit Compliance',
            description: 'Proposed VaR within board limits',
            status: 'passed',
            version: 'v2.1',
        },
        {
            id: 'pol-002',
            name: 'Counterparty Diversification',
            description: 'Hedge counterparty limits maintained',
            status: 'passed',
            version: 'v2.1',
            details: 'Max 20% with any single counterparty',
        },
    ],
    requiresHumanApproval: false,
};

const RISK_QUERY_RESPONSE: QueryResponse = {
    sessionId: 'session_risk_33333',
    domain: 'complex',
    domainConfidence: 0.82,
    domainEntropy: 0.41,
    guardianVerdict: 'approved',
    response: 'Risk analysis over 5 years of portfolio data shows the hedging strategy reduces Value at Risk by 45% (95% CI: [-58%, -32%], p<0.001). Market risk and credit risk are the dominant contributors to VaR, with liquidity acting as a common cause. One refutation test flagged potential unobserved confounders - recommend monitoring counterparty exposure.',
    requiresHuman: false,
    reasoningChain: [
        { node: 'Router', action: 'Classified as Complex domain (correlated risks)', confidence: 'medium', timestamp: '2025-01-20T10:20:00Z', durationMs: 125 },
        { node: 'Bayesian Explorer', action: 'Mapped risk factor correlations', confidence: 'high', timestamp: '2025-01-20T10:20:02Z', durationMs: 750 },
        { node: 'Causal Analyst', action: 'Estimated hedging effectiveness', confidence: 'high', timestamp: '2025-01-20T10:20:03Z', durationMs: 520 },
        { node: 'Guardian', action: 'Risk limits verified', confidence: 'high', timestamp: '2025-01-20T10:20:04Z', durationMs: 48 },
    ],
    causalResult: RISK_CAUSAL_RESULT,
    bayesianResult: RISK_BAYESIAN_RESULT,
    guardianResult: RISK_GUARDIAN_DECISION,
    error: null,
    keyInsights: [
        'Hedging reduces VaR by 45% - highly effective',
        'Market risk (52%) contributes more to VaR than credit risk (38%)',
        'Liquidity is key confounder linking market and credit risks',
    ],
    nextSteps: [
        'Expand hedging program with diversified counterparties',
        'Implement stress testing for correlation breakdown scenarios',
    ],
};

// ============================================================================
// SCENARIO RESPONSE MAPPING
// ============================================================================

export const SCENARIO_RESPONSES: Record<string, QueryResponse> = {
    scope3_attribution: MOCK_QUERY_RESPONSE,
    causal_discount_churn: CHURN_QUERY_RESPONSE,
    grid_stability: GRID_QUERY_RESPONSE,
    marketing_budget: MARKETING_QUERY_RESPONSE,
    risk_exposure: RISK_QUERY_RESPONSE,
};

export const SCENARIO_DAGS: Record<string, typeof MOCK_CAUSAL_DAG> = {
    scope3_attribution: MOCK_CAUSAL_DAG,
    causal_discount_churn: CHURN_CAUSAL_DAG,
    grid_stability: GRID_CAUSAL_DAG,
    marketing_budget: MARKETING_CAUSAL_DAG,
    risk_exposure: RISK_CAUSAL_DAG,
};
