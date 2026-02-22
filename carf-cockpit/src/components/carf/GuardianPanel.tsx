import React, { useState, useEffect } from 'react';
import PolicyEditorModal from './PolicyEditorModal';
import type { GuardianDecision } from '../../types/carf';
import ExplainableWrapper from './ExplainableWrapper';

/** Shape returned by /guardian/config */
interface GuardianConfig {
    activePolicies: number;
    thresholds: { name: string; value: string }[];
    lastUpdated?: string;
}

/** Shape returned by /guardian/policies */
interface PolicyDescription {
    id: string;
    name: string;
    description: string;
    relevance: string;
    configControl: string;
    euAiActArticle?: string;
    euAiActMatchLevel?: 'full' | 'partial' | 'low';
}

interface GuardianPanelProps {
    decision: GuardianDecision | null;
    onViewAuditTrail?: () => void;
}

const GuardianPanel: React.FC<GuardianPanelProps> = ({ decision, onViewAuditTrail }) => {
    const [showPolicyEditor, setShowPolicyEditor] = useState(false);
    const [guardianConfig, setGuardianConfig] = useState<GuardianConfig | null>(null);
    const [policyDescriptions, setPolicyDescriptions] = useState<PolicyDescription[]>([]);
    const [, setConfigError] = useState(false);

    // 3A: Fetch guardian config for empty-state context
    useEffect(() => {
        const controller = new AbortController();
        const fetchConfig = async () => {
            try {
                const res = await fetch('http://localhost:8000/guardian/config', { signal: controller.signal });
                if (res.ok) {
                    const data = await res.json();
                    setGuardianConfig(data);
                } else {
                    setConfigError(true);
                }
            } catch {
                if (controller.signal.aborted) return;
                setConfigError(true);
                // Provide sensible defaults when backend is unavailable
                setGuardianConfig({
                    activePolicies: 4,
                    thresholds: [
                        { name: 'Max spend per action', value: '$50,000' },
                        { name: 'Min confidence', value: '0.70' },
                        { name: 'Mandatory human review', value: 'High-risk actions' },
                    ],
                });
            }
        };
        fetchConfig();
        return () => controller.abort();
    }, []);

    // 3B: Fetch policy descriptions
    useEffect(() => {
        const controller = new AbortController();
        const fetchPolicies = async () => {
            try {
                const res = await fetch('http://localhost:8000/guardian/policies', { signal: controller.signal });
                if (res.ok) {
                    const data = await res.json();
                    const list = Array.isArray(data) ? data : Array.isArray(data?.policies) ? data.policies : [];
                    setPolicyDescriptions(list);
                }
            } catch {
                if (controller.signal.aborted) return;
                // Fallback descriptions when backend unavailable
                setPolicyDescriptions([
                    {
                        id: 'budget_limit',
                        name: 'Budget Limit',
                        description: 'Caps maximum spend per automated action to prevent runaway costs.',
                        relevance: 'Prevents large financial commitments without human sign-off.',
                        configControl: 'Threshold: max_spend_per_action',
                        euAiActArticle: 'Art. 14 - Human oversight',
                        euAiActMatchLevel: 'partial',
                    },
                    {
                        id: 'confidence_gate',
                        name: 'Confidence Gate',
                        description: 'Requires minimum statistical confidence before acting on causal estimates.',
                        relevance: 'Ensures decisions are backed by sufficient evidence.',
                        configControl: 'Threshold: min_confidence_level',
                        euAiActArticle: 'Art. 9 - Risk management',
                        euAiActMatchLevel: 'partial',
                    },
                    {
                        id: 'human_review',
                        name: 'Human Review Gate',
                        description: 'Escalates high-impact or uncertain decisions for human approval.',
                        relevance: 'Maintains human-in-the-loop for critical actions.',
                        configControl: 'Threshold: escalation_risk_level',
                        euAiActArticle: 'Art. 14 - Human oversight',
                        euAiActMatchLevel: 'full',
                    },
                    {
                        id: 'audit_trail',
                        name: 'Audit Trail',
                        description: 'Records every decision, input, and output for traceability.',
                        relevance: 'Provides full decision lineage for regulatory review.',
                        configControl: 'Always enabled (immutable)',
                        euAiActArticle: 'Art. 12 - Record-keeping',
                        euAiActMatchLevel: 'full',
                    },
                ]);
            }
        };
        fetchPolicies();
        return () => controller.abort();
    }, []);

    // Helper: EU AI Act match badge
    const getEuMatchBadge = (level?: 'full' | 'partial' | 'low') => {
        switch (level) {
            case 'full':
                return <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-medium">Full match</span>;
            case 'partial':
                return <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700 font-medium">Partial match</span>;
            case 'low':
                return <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-medium">Low match</span>;
            default:
                return null;
        }
    };

    // 3A: Empty state with explanatory context
    if (!decision) {
        return (
            <div className="space-y-4">
                <div className="p-4 bg-gradient-to-r from-slate-50 to-blue-50 border border-slate-200 rounded-lg" data-testid="guardian-empty-state">
                    <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold text-gray-900 mb-1">Guardian: Safety & Compliance Layer</h3>
                            <p className="text-xs text-gray-600 leading-relaxed">
                                Guardian validates every proposed action against configurable safety policies
                                before execution. It enforces budget limits, confidence thresholds, and
                                human-review gates to prevent unsafe autonomous decisions.
                            </p>
                        </div>
                    </div>

                    {/* Active config summary */}
                    {guardianConfig && (
                        <div className="mt-3 pt-3 border-t border-slate-200" data-testid="guardian-config-summary">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-semibold text-gray-700">Active Configuration</span>
                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
                                    {guardianConfig.activePolicies} policies active
                                </span>
                            </div>
                            <div className="space-y-1">
                                {(guardianConfig.thresholds ?? []).map((t, idx) => (
                                    <div key={idx} className="flex items-center justify-between text-[11px]">
                                        <span className="text-gray-500">{t.name}</span>
                                        <span className="font-mono text-gray-700">{t.value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <p className="text-[10px] text-gray-400 mt-3 italic">
                        Submit a query to see Guardian evaluate the proposed action against these policies.
                    </p>
                </div>

                {/* 3B: Policy descriptions even with no decision */}
                {policyDescriptions.length > 0 && (
                    <div data-testid="guardian-policy-descriptions">
                        <div className="text-xs font-semibold text-gray-700 mb-2">Available Policies</div>
                        <div className="space-y-2">
                            {policyDescriptions.map((pd) => (
                                <div key={pd.id} className="p-2.5 bg-gray-50 rounded border border-gray-100">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-xs font-medium text-gray-900">{pd.name}</span>
                                        {pd.euAiActArticle && getEuMatchBadge(pd.euAiActMatchLevel)}
                                    </div>
                                    <p className="text-[11px] text-gray-600">{pd.description}</p>
                                    {pd.euAiActArticle && (
                                        <p className="text-[10px] text-indigo-600 mt-1">
                                            EU AI Act: {pd.euAiActArticle}
                                        </p>
                                    )}
                                    <p className="text-[10px] text-gray-400 mt-0.5">
                                        Config: {pd.configControl}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    }

    const getVerdictBadge = (status: string) => {
        switch (status) {
            case 'pass':
                return <span className="badge bg-green-500 text-white">APPROVED</span>;
            case 'fail':
                return <span className="badge bg-red-500 text-white">REJECTED</span>;
            case 'pending':
                return <span className="badge bg-yellow-500 text-white">REQUIRES APPROVAL</span>;
            default:
                return <span className="badge bg-gray-500 text-white">UNKNOWN</span>;
        }
    };

    // 3A: Helper to explain why a section might be empty
    const hasAction = decision.proposedAction && decision.proposedAction.type;
    const hasExpectedEffect = decision.proposedAction && decision.proposedAction.expectedEffect;
    const hasPolicies = decision.policies && decision.policies.length > 0;

    // Build a lookup of policy descriptions by name for enrichment
    const policyDescMap = new Map(policyDescriptions.map(pd => [pd.name, pd]));

    return (
        <div className="space-y-4">
            {/* Verdict */}
            <ExplainableWrapper
                component="guardian_verdict"
                context={{ status: decision.overallStatus, requiresApproval: decision.requiresHumanApproval }}
                title="Guardian Verdict"
            >
                <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-900">Guardian Verdict</span>
                    {getVerdictBadge(decision.overallStatus)}
                </div>
            </ExplainableWrapper>

            {/* 3-Point Context */}
            <div className="space-y-3">
                {/* WHAT */}
                {hasAction ? (
                    <ExplainableWrapper
                        component="guardian_action"
                        elementId="what"
                        context={{ action: decision.proposedAction }}
                        title="Proposed Action"
                    >
                        <div className="p-3 bg-blue-50 border-l-4 border-blue-500 rounded">
                            <div className="text-xs font-semibold text-blue-900 mb-1">WHAT</div>
                            <div className="text-sm text-blue-800">
                                {decision.proposedAction.type.toUpperCase()}: {decision.proposedAction.target}
                                <div className="text-xs mt-1">
                                    Amount: ${decision.proposedAction.amount.toLocaleString()} {decision.proposedAction.unit}
                                </div>
                            </div>
                        </div>
                    </ExplainableWrapper>
                ) : (
                    <div className="p-3 bg-blue-50/50 border-l-4 border-blue-200 rounded" data-testid="what-empty">
                        <div className="text-xs font-semibold text-blue-400 mb-1">WHAT</div>
                        <div className="text-xs text-blue-300 italic">
                            No proposed action specified. The analysis may still be determining the optimal intervention,
                            or the query did not produce an actionable recommendation.
                        </div>
                    </div>
                )}

                {/* WHY */}
                {hasExpectedEffect ? (
                    <ExplainableWrapper
                        component="guardian_action"
                        elementId="why"
                        context={{ expectedEffect: decision.proposedAction.expectedEffect }}
                        title="Expected Effect"
                    >
                        <div className="p-3 bg-purple-50 border-l-4 border-purple-500 rounded">
                            <div className="text-xs font-semibold text-purple-900 mb-1">WHY</div>
                            <div className="text-sm text-purple-800">
                                Expected effect: {decision.proposedAction.expectedEffect}
                            </div>
                        </div>
                    </ExplainableWrapper>
                ) : (
                    <div className="p-3 bg-purple-50/50 border-l-4 border-purple-200 rounded" data-testid="why-empty">
                        <div className="text-xs font-semibold text-purple-400 mb-1">WHY</div>
                        <div className="text-xs text-purple-300 italic">
                            Expected effect not yet computed. This section populates once the causal analysis
                            quantifies the anticipated impact of the proposed intervention.
                        </div>
                    </div>
                )}

                {/* RISK */}
                {hasPolicies ? (
                    <ExplainableWrapper
                        component="guardian_risk"
                        context={{ policiesPassed: decision.policies.every(p => p.status === 'passed'), policyCount: decision.policies.length }}
                        title="Risk Assessment"
                    >
                        <div className={`p-3 border-l-4 rounded ${decision.policies.some(p => p.status === 'failed')
                            ? 'bg-red-50 border-red-500'
                            : 'bg-green-50 border-green-500'
                            }`}>
                            <div className={`text-xs font-semibold mb-1 ${decision.policies.some(p => p.status === 'failed') ? 'text-red-900' : 'text-green-900'
                                }`}>RISK</div>
                            <div className={`text-sm ${decision.policies.some(p => p.status === 'failed') ? 'text-red-800' : 'text-green-800'
                                }`}>
                                {decision.policies.every(p => p.status === 'passed')
                                    ? 'All policy checks passed'
                                    : 'Policy violations detected'}
                            </div>
                        </div>
                    </ExplainableWrapper>
                ) : (
                    <div className="p-3 bg-gray-50 border-l-4 border-gray-200 rounded" data-testid="risk-empty">
                        <div className="text-xs font-semibold text-gray-400 mb-1">RISK</div>
                        <div className="text-xs text-gray-400 italic">
                            No policy checks have been evaluated yet. Policies are tested once a concrete
                            action with measurable parameters is proposed by the analysis engine.
                        </div>
                    </div>
                )}
            </div>

            {/* Policy Checks */}
            <ExplainableWrapper
                component="guardian_policies"
                context={{ totalPolicies: decision.policies.length, passedPolicies: decision.policies.filter(p => p.status === 'passed').length }}
                title="Policy Checks"
            >
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <div className="text-sm font-semibold text-gray-900">Policy Checks</div>
                        <button
                            onClick={() => setShowPolicyEditor(true)}
                            className="text-xs text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1"
                            title="Edit validation rules"
                        >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            Configure
                        </button>
                    </div>
                    <p className="text-[10px] text-gray-500 mb-3 italic">
                        Policies define the safety boundaries for automated actions. Passing all checks enables autonomous execution.
                    </p>
                    <div className="space-y-2">
                        {(decision.policies ?? []).map((policy, idx) => {
                            const desc = policyDescMap.get(policy.name);
                            return (
                                <ExplainableWrapper
                                    key={idx}
                                    component="guardian_policy"
                                    elementId={policy.name}
                                    context={{ policyName: policy.name, status: policy.status, details: policy.details }}
                                    title={policy.name}
                                >
                                    <div className="p-2 bg-gray-50 rounded hover:bg-gray-100 transition-colors">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <span className={`text-sm ${policy.status === 'passed' ? 'text-green-500' :
                                                    policy.status === 'failed' ? 'text-red-500' :
                                                        'text-yellow-500'
                                                    }`}>
                                                    {policy.status === 'passed' ? '✓' : policy.status === 'failed' ? '✗' : '⚠'}
                                                </span>
                                                <span className="text-sm font-medium text-gray-900">{policy.name}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {desc?.euAiActArticle && getEuMatchBadge(desc.euAiActMatchLevel)}
                                                <span className="text-xs text-gray-500">{policy.version}</span>
                                            </div>
                                        </div>
                                        {policy.details && (
                                            <div className="text-xs text-gray-600 mt-1 ml-6">{policy.details}</div>
                                        )}
                                        {/* 3B: Per-policy description, relevance, config control */}
                                        {desc && (
                                            <div className="ml-6 mt-1.5 space-y-0.5">
                                                <div className="text-[10px] text-gray-500">{desc.relevance}</div>
                                                <div className="text-[10px] text-gray-400">Config: {desc.configControl}</div>
                                                {desc.euAiActArticle && (
                                                    <div className="text-[10px] text-indigo-500">EU AI Act: {desc.euAiActArticle}</div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </ExplainableWrapper>
                            );
                        })}
                    </div>
                </div>
            </ExplainableWrapper>

            {/* 3C: Audit trail preserved - clickable */}
            <button
                onClick={onViewAuditTrail}
                className="w-full flex items-center justify-between p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors group"
                data-testid="audit-trail-button"
                title="View full decision audit trail"
            >
                <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-xs font-medium text-emerald-700">Audit trail preserved</span>
                </div>
                <svg className="w-3.5 h-3.5 text-emerald-400 group-hover:text-emerald-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
            </button>

            {/* Human Approval Required */}
            {decision.requiresHumanApproval && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                    <div className="text-sm font-semibold text-yellow-900 mb-2">Human Approval Required</div>
                    <div className="flex gap-2">
                        <button className="flex-1 px-3 py-2 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors">
                            Approve
                        </button>
                        <button className="flex-1 px-3 py-2 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
                            Reject
                        </button>
                    </div>
                </div>
            )}
            <PolicyEditorModal
                isOpen={showPolicyEditor}
                onClose={() => setShowPolicyEditor(false)}
            />
        </div>
    );
};

export default GuardianPanel;
