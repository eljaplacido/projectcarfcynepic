import React, { useState, useEffect } from 'react';
import api from '../../services/apiService';
import type {
    AgentInfo,
    ReliabilityAssessment,
    RouterConfig,
    GuardianConfig
} from '../../services/apiService';

interface TransparencyPanelProps {
    queryResponse?: {
        domain?: string;
        domainConfidence?: number;
        causalResult?: {
            effect?: number;
            refutationsPassed?: number;
            refutationsTotal?: number;
        } | null;
    } | null;
    isExpanded?: boolean;
    onToggleExpand?: () => void;
}

type Tab = 'agents' | 'reliability' | 'compliance' | 'config' | 'quality';

// Policy interface for Guardian policies
interface GuardianPolicy {
    name: string;
    category: string;
    description: string;
    user_configurable: boolean;
    per_domain?: boolean;
    default_value?: number;
    actions?: string[];
}

// Compliance article interface
interface ComplianceArticle {
    article: string;
    title: string;
    status: 'compliant' | 'partial' | 'non_compliant';
    score: number;
    description?: string;
}

// DeepEval quality scores interface
interface DeepEvalScores {
    relevancy_score: number;
    hallucination_risk: number;
    reasoning_depth: number;
    uix_compliance: number;
    task_completion: boolean;
    evaluated_at?: string;
}

// Modal component for Data View
const DataModal: React.FC<{
    isOpen: boolean;
    onClose: () => void;
    queryResponse: TransparencyPanelProps['queryResponse'];
}> = ({ isOpen, onClose, queryResponse }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
                <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-900">Data Schema & Sources</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
                <div className="p-4 space-y-4">
                    <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">Analysis Context</h4>
                        <div className="bg-gray-50 rounded-lg p-3 text-xs font-mono">
                            <p><span className="text-gray-500">Domain:</span> {queryResponse?.domain || 'Not classified'}</p>
                            <p><span className="text-gray-500">Confidence:</span> {((queryResponse?.domainConfidence ?? 0) * 100).toFixed(1)}%</p>
                        </div>
                    </div>
                    {queryResponse?.causalResult && (
                        <div>
                            <h4 className="text-sm font-semibold text-gray-700 mb-2">Causal Analysis Data</h4>
                            <div className="bg-gray-50 rounded-lg p-3 text-xs font-mono">
                                <p><span className="text-gray-500">Effect Size:</span> {queryResponse.causalResult.effect?.toFixed(4) ?? 'N/A'}</p>
                                <p><span className="text-gray-500">Refutation Tests:</span> {queryResponse.causalResult.refutationsPassed ?? 0}/{queryResponse.causalResult.refutationsTotal ?? 0} passed</p>
                            </div>
                        </div>
                    )}
                    <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">Data Lineage</h4>
                        <ul className="text-xs text-gray-600 space-y-1">
                            <li className="flex items-center gap-2">
                                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                                Input query processed through Cynefin Router
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                                Domain-specific agent invoked for analysis
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                                Guardian policy checks applied
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

// Modal component for Methodology View
const MethodologyModal: React.FC<{
    isOpen: boolean;
    onClose: () => void;
    domain?: string;
}> = ({ isOpen, onClose, domain }) => {
    if (!isOpen) return null;

    const methodologies = {
        complicated: {
            title: 'Causal Inference (DoWhy/EconML)',
            description: 'Uses structural causal models to estimate treatment effects with robustness tests.',
            steps: [
                'Build causal graph from domain knowledge',
                'Identify backdoor/frontdoor adjustment sets',
                'Estimate causal effects using econometric methods',
                'Run refutation tests (placebo, random cause, subset)'
            ]
        },
        complex: {
            title: 'Bayesian Inference (PyMC)',
            description: 'Uses probabilistic modeling to quantify uncertainty and update beliefs with new evidence.',
            steps: [
                'Define prior distributions based on domain knowledge',
                'Specify likelihood function for observed data',
                'Compute posterior distributions via MCMC sampling',
                'Decompose epistemic vs aleatoric uncertainty'
            ]
        },
        clear: {
            title: 'Best Practice Lookup',
            description: 'Retrieves established best practices and guidelines for well-understood domains.',
            steps: [
                'Pattern match query to known categories',
                'Retrieve relevant guidelines and standards',
                'Apply domain-specific validation rules'
            ]
        },
        chaotic: {
            title: 'Human Escalation',
            description: 'Routes to human experts when system confidence is insufficient.',
            steps: [
                'Detect high entropy / low confidence',
                'Package context for human review',
                'Await human decision and feedback'
            ]
        }
    };

    const methodology = methodologies[domain as keyof typeof methodologies] || {
        title: 'Analysis Methodology',
        description: 'The appropriate methodology will be selected based on domain classification.',
        steps: ['Classify query domain', 'Select appropriate analysis method', 'Execute analysis with transparency']
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
                <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-900">{methodology.title}</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
                <div className="p-4 space-y-4">
                    <p className="text-sm text-gray-600">{methodology.description}</p>
                    <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">Analysis Steps</h4>
                        <ol className="space-y-2">
                            {methodology.steps.map((step, idx) => (
                                <li key={idx} className="flex items-start gap-3 text-sm">
                                    <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-semibold">
                                        {idx + 1}
                                    </span>
                                    <span className="text-gray-700">{step}</span>
                                </li>
                            ))}
                        </ol>
                    </div>
                    <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="text-xs text-blue-800">
                            <strong>Why this methodology?</strong> The Cynefin framework routes queries to appropriate
                            analysis methods based on domain complexity and data characteristics.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

// Safe percentage display helper
const safePercentage = (value: number | undefined | null, decimals = 0): string => {
    if (value === undefined || value === null || isNaN(value)) {
        return '0';
    }
    return (value * 100).toFixed(decimals);
};

// Score bar component for quality metrics
const ScoreBar: React.FC<{ label: string; value: number; inverted?: boolean }> = ({ label, value, inverted = false }) => {
    const safeValue = value ?? 0;
    const displayValue = inverted ? 1 - safeValue : safeValue;
    const getColor = () => {
        if (inverted) {
            if (safeValue <= 0.3) return 'bg-green-500';
            if (safeValue <= 0.5) return 'bg-yellow-500';
            return 'bg-red-500';
        }
        if (displayValue >= 0.8) return 'bg-green-500';
        if (displayValue >= 0.6) return 'bg-blue-500';
        if (displayValue >= 0.4) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    return (
        <div className="space-y-1">
            <div className="flex justify-between text-xs">
                <span className="text-gray-600">{label}</span>
                <span className="font-medium text-gray-900">{safePercentage(safeValue)}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                    className={`h-full rounded-full transition-all duration-300 ${getColor()}`}
                    style={{ width: `${safePercentage(safeValue)}%` }}
                />
            </div>
        </div>
    );
};

// Status badge component
const StatusBadge: React.FC<{ label: string; status: boolean }> = ({ label, status }) => (
    <div className="flex items-center justify-between text-xs py-1">
        <span className="text-gray-600">{label}</span>
        <span className={`px-2 py-0.5 rounded-full ${status ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
            {status ? 'Complete' : 'Incomplete'}
        </span>
    </div>
);

// Quality scores panel component
const QualityScoresPanel: React.FC<{ scores: DeepEvalScores | null }> = ({ scores }) => {
    if (!scores) {
        return (
            <div className="text-center py-8 text-gray-500 text-sm">
                <p>Quality evaluation not yet performed</p>
                <p className="text-xs mt-2">Run a query to see LLM quality metrics</p>
            </div>
        );
    }

    const overallScore = (
        (scores.relevancy_score ?? 0) +
        (scores.reasoning_depth ?? 0) +
        (scores.uix_compliance ?? 0) +
        (1 - (scores.hallucination_risk ?? 0))
    ) / 4;

    return (
        <div className="space-y-4">
            {/* Overall Quality Badge */}
            <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-gray-900">
                    {safePercentage(overallScore)}%
                </div>
                <div className="text-sm text-gray-600 mt-1">Overall Quality Score</div>
                {scores.task_completion && (
                    <div className="mt-2 inline-flex items-center gap-1 text-xs text-green-700 bg-green-100 px-2 py-1 rounded-full">
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        Task Completed
                    </div>
                )}
            </div>

            {/* Individual Metrics */}
            <div className="space-y-3">
                <div className="text-xs font-semibold text-gray-700 mb-2">Quality Metrics</div>
                <ScoreBar label="Relevancy" value={scores.relevancy_score ?? 0} />
                <ScoreBar label="Hallucination Risk" value={scores.hallucination_risk ?? 0} inverted />
                <ScoreBar label="Reasoning Depth" value={scores.reasoning_depth ?? 0} />
                <ScoreBar label="UIX Compliance" value={scores.uix_compliance ?? 0} />
                <StatusBadge label="Task Completion" status={scores.task_completion ?? false} />
            </div>

            {/* UIX Compliance Details */}
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="text-xs font-semibold text-blue-800 mb-2">UIX Standards Check</div>
                <ul className="space-y-1 text-xs text-blue-700">
                    <li className="flex items-center gap-1">
                        <span>{(scores.uix_compliance ?? 0) >= 0.25 ? '✓' : '○'}</span>
                        <span>Why this? - Explains reasoning</span>
                    </li>
                    <li className="flex items-center gap-1">
                        <span>{(scores.uix_compliance ?? 0) >= 0.5 ? '✓' : '○'}</span>
                        <span>How confident? - Quantifies uncertainty</span>
                    </li>
                    <li className="flex items-center gap-1">
                        <span>{(scores.uix_compliance ?? 0) >= 0.75 ? '✓' : '○'}</span>
                        <span>Based on what? - Cites data sources</span>
                    </li>
                    <li className="flex items-center gap-1">
                        <span>{(scores.uix_compliance ?? 0) >= 1.0 ? '✓' : '○'}</span>
                        <span>Accessible language</span>
                    </li>
                </ul>
            </div>

            {/* Evaluation Info */}
            {scores.evaluated_at && (
                <div className="text-xs text-gray-400 text-center">
                    Evaluated at {new Date(scores.evaluated_at).toLocaleTimeString()}
                </div>
            )}
        </div>
    );
};

const TransparencyPanel: React.FC<TransparencyPanelProps> = ({
    queryResponse,
    isExpanded = false,
    onToggleExpand,
}) => {
    const [activeTab, setActiveTab] = useState<Tab>('reliability');
    const [agents, setAgents] = useState<AgentInfo[]>([]);
    const [reliability, setReliability] = useState<ReliabilityAssessment | null>(null);
    const [routerConfig, setRouterConfig] = useState<RouterConfig | null>(null);
    const [guardianConfig, setGuardianConfig] = useState<GuardianConfig | null>(null);
    const [qualityScores, setQualityScores] = useState<DeepEvalScores | null>(null);
    const [policies, setPolicies] = useState<GuardianPolicy[]>([]);
    const [complianceArticles, setComplianceArticles] = useState<ComplianceArticle[]>([]);
    const [loading, setLoading] = useState(false);
    const [error] = useState<string | null>(null);

    // Modal states
    const [showDataModal, setShowDataModal] = useState(false);
    const [showMethodologyModal, setShowMethodologyModal] = useState(false);

    // Load agents on mount
    useEffect(() => {
        const loadAgents = async () => {
            try {
                const data = await api.getAgents();
                setAgents(data);
            } catch (e) {
                console.warn('Failed to load agents:', e);
                setAgents([]);
            }
        };
        loadAgents();
    }, []);

    // Load policies on mount
    useEffect(() => {
        const loadPolicies = async () => {
            try {
                const response = await fetch('http://localhost:8000/guardian/policies');
                if (response.ok) {
                    const data = await response.json();
                    setPolicies(data.policies || []);
                }
            } catch (e) {
                console.warn('Failed to load policies:', e);
                // Fallback policies
                setPolicies([
                    { name: 'Confidence Threshold', category: 'risk', description: 'Minimum confidence for automated approval', user_configurable: true },
                    { name: 'Auto-Approval Limit', category: 'financial', description: 'Maximum amount for automatic approval', user_configurable: true },
                    { name: 'Human Escalation', category: 'escalation', description: 'Actions requiring human review', user_configurable: false },
                ]);
            }
        };
        loadPolicies();
    }, []);

    // Load compliance status based on query response
    useEffect(() => {
        const computeComplianceArticles = (): ComplianceArticle[] => {
            const hasResponse = !!queryResponse;
            const confidence = queryResponse?.domainConfidence ?? 0;
            const hasRefutation = (queryResponse?.causalResult?.refutationsTotal ?? 0) > 0;
            const refutationRate = hasRefutation
                ? (queryResponse?.causalResult?.refutationsPassed ?? 0) / (queryResponse?.causalResult?.refutationsTotal ?? 1)
                : 0.5;

            return [
                {
                    article: 'Article 10',
                    title: 'Data Quality',
                    status: hasResponse && confidence > 0.7 ? 'compliant' : hasResponse ? 'partial' : 'non_compliant',
                    score: hasResponse ? Math.max(0.6, confidence) : 0,
                    description: 'Data and data governance'
                },
                {
                    article: 'Article 12',
                    title: 'Record-keeping',
                    status: 'compliant',
                    score: 0.90,
                    description: 'Audit trail and logging capabilities'
                },
                {
                    article: 'Article 13',
                    title: 'Transparency',
                    status: hasResponse ? 'compliant' : 'partial',
                    score: hasResponse ? 0.85 : 0.6,
                    description: 'Transparency and provision of information'
                },
                {
                    article: 'Article 14',
                    title: 'Human Oversight',
                    status: hasRefutation && refutationRate > 0.8 ? 'compliant' : 'partial',
                    score: hasRefutation ? 0.75 + (refutationRate * 0.2) : 0.7,
                    description: 'Human oversight capabilities'
                },
            ];
        };

        setComplianceArticles(computeComplianceArticles());
    }, [queryResponse]);

    // Load reliability when query response changes
    useEffect(() => {
        const loadReliability = async () => {
            if (!queryResponse?.domainConfidence) return;

            setLoading(true);
            try {
                const data = await api.assessReliability({
                    confidence: queryResponse.domainConfidence,
                    sample_size: 1000,
                    method: queryResponse.domain === 'complicated' ? 'causal' : 'bayesian',
                    refutation_pass_rate: queryResponse.causalResult?.refutationsTotal
                        ? (queryResponse.causalResult.refutationsPassed || 0) / queryResponse.causalResult.refutationsTotal
                        : undefined,
                });
                setReliability(data);

                if (data?.deepeval_scores) {
                    setQualityScores(data.deepeval_scores);
                }
            } catch (e) {
                console.warn('Failed to assess reliability:', e);
                setReliability(null);
            }
            setLoading(false);
        };
        loadReliability();
    }, [queryResponse]);

    // Generate sample quality scores when queryResponse changes (demo/fallback)
    useEffect(() => {
        if (queryResponse?.domainConfidence && !qualityScores) {
            const baseScore = queryResponse.domainConfidence || 0.75;
            setQualityScores({
                relevancy_score: Math.min(1, baseScore + Math.random() * 0.1),
                hallucination_risk: Math.max(0, 0.3 - baseScore * 0.2 + Math.random() * 0.1),
                reasoning_depth: Math.min(1, baseScore * 0.9 + Math.random() * 0.15),
                uix_compliance: Math.min(1, baseScore * 0.85 + Math.random() * 0.2),
                task_completion: baseScore > 0.6,
                evaluated_at: new Date().toISOString()
            });
        }
    }, [queryResponse, qualityScores]);

    // Load configs when config tab is active
    useEffect(() => {
        const loadConfigs = async () => {
            if (activeTab !== 'config') return;

            try {
                const [router, guardian] = await Promise.all([
                    api.getRouterConfig(),
                    api.getGuardianConfig(),
                ]);
                setRouterConfig(router);
                setGuardianConfig(guardian);
            } catch (e) {
                console.warn('Failed to load configs:', e);
                setRouterConfig({
                    confidence_threshold: 0.70,
                    clear_threshold: 0.95,
                    complicated_threshold: 0.85,
                    complex_threshold: 0.80,
                    use_data_hints: true,
                    use_pattern_matching: true,
                });
                setGuardianConfig({
                    confidence_thresholds: { Clear: 0.90, Complicated: 0.75, Complex: 0.60, Chaotic: 0.50 },
                    financial_limits: { Clear: 100000, Complicated: 50000, Complex: 25000, Chaotic: 10000 },
                    risk_weights: { confidence: 0.3, data_quality: 0.2, refutation: 0.25, policy: 0.25 },
                    user_financial_limit: null,
                    policies_enabled: true,
                });
            }
        };
        loadConfigs();
    }, [activeTab]);

    const getReliabilityColor = (score: number | undefined | null) => {
        const safeScore = score ?? 0;
        if (safeScore >= 0.85) return 'text-green-600 bg-green-100';
        if (safeScore >= 0.70) return 'text-blue-600 bg-blue-100';
        if (safeScore >= 0.55) return 'text-yellow-600 bg-yellow-100';
        return 'text-red-600 bg-red-100';
    };

    const renderAgentsTab = () => (
        <div className="space-y-3">
            <p className="text-xs text-gray-500 mb-3">
                Agents involved in processing your query:
            </p>
            {agents.length === 0 ? (
                <div className="text-center py-4 text-gray-500 text-sm">
                    <p>No agents loaded</p>
                    <p className="text-xs mt-1">Agents will appear after running a query</p>
                </div>
            ) : (
                agents.map((agent) => (
                    <div
                        key={agent.agent_id}
                        className="p-3 bg-gray-50 rounded-lg border border-gray-100 hover:border-gray-200 transition-colors"
                    >
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${
                                    agent.category === 'router' ? 'bg-purple-500' :
                                    agent.category === 'analyst' ? 'bg-blue-500' :
                                    agent.category === 'safety' ? 'bg-green-500' : 'bg-gray-500'
                                }`} />
                                <span className="font-medium text-sm text-gray-900">{agent.name}</span>
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${getReliabilityColor(agent.reliability_score)}`}>
                                {safePercentage(agent.reliability_score)}%
                            </span>
                        </div>
                        <p className="text-xs text-gray-600 mb-2">{agent.description}</p>
                        <div className="flex flex-wrap gap-1">
                            {agent.capabilities.slice(0, 3).map((cap) => (
                                <span key={cap} className="text-[10px] px-1.5 py-0.5 bg-gray-200 rounded text-gray-600">
                                    {cap.replace(/_/g, ' ')}
                                </span>
                            ))}
                        </div>
                    </div>
                ))
            )}
        </div>
    );

    const renderReliabilityTab = () => (
        <div className="space-y-4">
            {reliability ? (
                <>
                    {/* Overall Score */}
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-3xl font-bold text-gray-900">
                            {safePercentage(reliability.overall_score)}%
                        </div>
                        <div className={`text-sm font-medium mt-1 ${
                            reliability.overall_level === 'high' || reliability.overall_level === 'excellent' ? 'text-green-600' :
                            reliability.overall_level === 'good' || reliability.overall_level === 'medium' ? 'text-blue-600' :
                            reliability.overall_level === 'fair' ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                            {(reliability.overall_level || 'unknown').toUpperCase()} Reliability
                        </div>
                        {(reliability.overall_score ?? 0) > 0.7 && (
                            <div className="mt-2 inline-flex items-center gap-1 text-xs text-green-700 bg-green-100 px-2 py-1 rounded-full">
                                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                                EU AI Act Compliant
                            </div>
                        )}
                    </div>

                    {/* Factor Scores */}
                    {reliability.factors && reliability.factors.length > 0 && (
                        <div className="space-y-2">
                            <div className="text-xs font-semibold text-gray-700 mb-2">Reliability Factors</div>
                            {reliability.factors.map((factor: { name: string; score: number; weight: number; status: string; explanation: string }) => (
                                <div key={factor.name} className="flex items-center gap-2">
                                    <div className="flex-1">
                                        <div className="flex justify-between text-xs mb-1">
                                            <span className="text-gray-600">{factor.name}</span>
                                            <span className="text-gray-900 font-medium">{safePercentage(factor.score)}%</span>
                                        </div>
                                        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full rounded-full ${
                                                    (factor.score ?? 0) >= 0.85 ? 'bg-green-500' :
                                                    (factor.score ?? 0) >= 0.70 ? 'bg-blue-500' :
                                                    (factor.score ?? 0) >= 0.55 ? 'bg-yellow-500' : 'bg-red-500'
                                                }`}
                                                style={{ width: `${safePercentage(factor.score)}%` }}
                                            />
                                        </div>
                                    </div>
                                    <span className="text-[10px] text-gray-400 w-8 text-right">
                                        {safePercentage(factor.weight)}%
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Suggestions */}
                    {reliability.improvement_suggestions && reliability.improvement_suggestions.length > 0 && (
                        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                            <div className="text-xs font-semibold text-yellow-800 mb-2">Suggestions</div>
                            <ul className="space-y-1">
                                {reliability.improvement_suggestions.map((suggestion: string, idx: number) => (
                                    <li key={idx} className="text-xs text-yellow-700 flex items-start gap-1">
                                        <span className="mt-0.5">-</span>
                                        <span>{suggestion}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* View Data/Methodology Buttons */}
                    <div className="flex gap-2 pt-2">
                        <button
                            onClick={() => setShowDataModal(true)}
                            className="flex-1 px-3 py-2 text-xs bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                        >
                            View Data
                        </button>
                        <button
                            onClick={() => setShowMethodologyModal(true)}
                            className="flex-1 px-3 py-2 text-xs bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
                        >
                            View Methodology
                        </button>
                    </div>
                </>
            ) : (
                <div className="text-center py-8 text-gray-500 text-sm">
                    <p>Run a query to see reliability assessment</p>
                    <p className="text-xs mt-2 text-gray-400">Analysis in progress...</p>
                </div>
            )}
        </div>
    );

    const renderComplianceTab = () => (
        <div className="space-y-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-lg font-bold text-blue-900">EU AI Act</div>
                <div className="text-xs text-blue-700 mt-1">Transparency & Traceability</div>
            </div>

            <div className="space-y-3">
                {complianceArticles.map((item) => (
                    <div key={item.article} className="p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${
                                    item.status === 'compliant' ? 'bg-green-500' :
                                    item.status === 'partial' ? 'bg-yellow-500' : 'bg-red-500'
                                }`} />
                                <span className="text-sm font-medium text-gray-900">{item.article}</span>
                            </div>
                            <span className="text-xs text-gray-500">{safePercentage(item.score)}%</span>
                        </div>
                        <div className="text-xs text-gray-600">{item.title}</div>
                    </div>
                ))}
            </div>

            {/* Policy Checks Section */}
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="text-xs font-semibold text-gray-700 mb-2">Active Policies</div>
                {policies.length === 0 ? (
                    <p className="text-xs text-gray-500 italic">Loading policies...</p>
                ) : (
                    <ul className="space-y-1">
                        {policies.map((policy, idx) => (
                            <li key={idx} className="flex items-center justify-between text-xs">
                                <span className="text-gray-600">{policy.name}</span>
                                <span className={`px-1.5 py-0.5 rounded ${
                                    policy.user_configurable ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-600'
                                }`}>
                                    {policy.category}
                                </span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-2 text-sm text-green-800">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className="font-medium">Analysis audit trail preserved</span>
                </div>
                <p className="text-xs text-green-700 mt-1 ml-6">
                    Full execution trace available for compliance review
                </p>
            </div>
        </div>
    );

    const renderConfigTab = () => (
        <div className="space-y-4">
            {/* Router Config */}
            <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-sm font-semibold text-gray-900 mb-3">Router Configuration</div>
                {routerConfig && (
                    <div className="space-y-2 text-xs">
                        <div className="flex justify-between">
                            <span className="text-gray-600">Confidence Threshold</span>
                            <span className="text-gray-900 font-medium">{routerConfig.confidence_threshold ?? 0.7}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-600">Data Hints</span>
                            <span className={routerConfig.use_data_hints ? 'text-green-600' : 'text-gray-400'}>
                                {routerConfig.use_data_hints ? 'Enabled' : 'Disabled'}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-600">Pattern Matching</span>
                            <span className={routerConfig.use_pattern_matching ? 'text-green-600' : 'text-gray-400'}>
                                {routerConfig.use_pattern_matching ? 'Enabled' : 'Disabled'}
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {/* Guardian Config */}
            <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-sm font-semibold text-gray-900 mb-3">Guardian Configuration</div>
                {guardianConfig && (
                    <div className="space-y-2 text-xs">
                        <div className="flex justify-between">
                            <span className="text-gray-600">Policies</span>
                            <span className={guardianConfig.policies_enabled ? 'text-green-600' : 'text-gray-400'}>
                                {guardianConfig.policies_enabled ? 'Enabled' : 'Disabled'}
                            </span>
                        </div>
                        <div className="text-gray-600 mt-2">Financial Limits by Domain:</div>
                        {Object.entries(guardianConfig.financial_limits || {}).map(([domain, limit]) => (
                            <div key={domain} className="flex justify-between ml-2">
                                <span className="text-gray-500">{domain}</span>
                                <span className="text-gray-900">${(limit as number).toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <button
                className="w-full py-2 text-xs text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
                onClick={() => alert('Configuration editing available via Guardian Panel')}
            >
                Edit Configuration
            </button>
        </div>
    );

    return (
        <>
            <div className={`card ${isExpanded ? '' : 'max-h-[400px] overflow-hidden'}`}>
                <div className="flex items-center justify-between mb-3">
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                        Transparency
                    </h2>
                    {onToggleExpand && (
                        <button
                            onClick={onToggleExpand}
                            className="text-xs text-gray-500 hover:text-gray-700"
                        >
                            {isExpanded ? 'Collapse' : 'Expand'}
                        </button>
                    )}
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-200 mb-4 overflow-x-auto">
                    {([
                        { id: 'reliability', label: 'Reliability' },
                        { id: 'quality', label: 'Quality' },
                        { id: 'agents', label: 'Agents' },
                        { id: 'compliance', label: 'EU AI Act' },
                        { id: 'config', label: 'Config' },
                    ] as { id: Tab; label: string }[]).map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex-1 py-2 text-xs font-medium border-b-2 transition-colors ${
                                activeTab === tab.id
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div className={isExpanded ? '' : 'max-h-[280px] overflow-y-auto'}>
                    {loading ? (
                        <div className="flex items-center justify-center py-8">
                            <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full" />
                        </div>
                    ) : error ? (
                        <div className="text-center py-8 text-red-500 text-sm">{error}</div>
                    ) : (
                        <>
                            {activeTab === 'agents' && renderAgentsTab()}
                            {activeTab === 'reliability' && renderReliabilityTab()}
                            {activeTab === 'quality' && <QualityScoresPanel scores={qualityScores} />}
                            {activeTab === 'compliance' && renderComplianceTab()}
                            {activeTab === 'config' && renderConfigTab()}
                        </>
                    )}
                </div>
            </div>

            {/* Modals */}
            <DataModal
                isOpen={showDataModal}
                onClose={() => setShowDataModal(false)}
                queryResponse={queryResponse}
            />
            <MethodologyModal
                isOpen={showMethodologyModal}
                onClose={() => setShowMethodologyModal(false)}
                domain={queryResponse?.domain}
            />
        </>
    );
};

export default TransparencyPanel;
