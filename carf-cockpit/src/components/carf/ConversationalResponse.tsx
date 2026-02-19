import React, { useState } from 'react';
import type { QueryResponse } from '../../types/carf';
import SuggestedQuestions, { generateSuggestedQuestions } from './SuggestedQuestions';

interface ConversationalResponseProps {
    response: QueryResponse | null;
    onFollowUpQuestion: (question: string) => void;
    onViewMethodology: (type: 'causal' | 'bayesian' | 'guardian') => void;
    onViewData?: () => void;
}

interface ConfidenceZone {
    level: 'high' | 'medium' | 'low';
    title: string;
    items: {
        text: string;
        action?: { label: string; onClick: () => void };
    }[];
}

const ConversationalResponse: React.FC<ConversationalResponseProps> = ({
    response,
    onFollowUpQuestion,
    onViewMethodology,
    onViewData,
}) => {
    const [expandedZone, setExpandedZone] = useState<string | null>(null);
    const [expandedSummary, setExpandedSummary] = useState<any>(null);

    if (!response || !response.response) {
        return null;
    }

    const getConfidenceZones = (): ConfidenceZone[] => {
        const zones: ConfidenceZone[] = [];

        // High confidence zone
        const highItems: ConfidenceZone['items'] = [];
        if (response.causalResult) {
            const cr = response.causalResult;
            highItems.push({
                text: `Effect of ${cr.treatment ?? 'treatment'} on ${cr.outcome ?? 'outcome'}: ${cr.effect != null && cr.effect > 0 ? '+' : ''}${cr.effect?.toFixed(2) ?? 'N/A'} ${cr.unit ?? ''}`,
                action: { label: 'View Methodology', onClick: () => onViewMethodology('causal') },
            });
            highItems.push({
                text: `95% CI: [${cr.confidenceInterval?.[0]?.toFixed(2) ?? 'N/A'}, ${cr.confidenceInterval?.[1]?.toFixed(2) ?? 'N/A'}]${cr.pValue != null ? ` · p = ${cr.pValue.toFixed(4)}` : ''}`,
            });
            if (cr.refutationsPassed === cr.refutationsTotal) {
                highItems.push({
                    text: `Refutation tests: ${cr.refutationsPassed}/${cr.refutationsTotal} passed`,
                });
            }
        }
        if (response.bayesianResult && response.bayesianResult.confidenceLevel === 'high') {
            highItems.push({
                text: `Posterior mean: ${response.bayesianResult.posteriorMean?.toFixed(3) ?? 'N/A'} (std: ${response.bayesianResult.posteriorStd?.toFixed(3) ?? 'N/A'})`,
                action: { label: 'View Methodology', onClick: () => onViewMethodology('bayesian') },
            });
        }
        if (highItems.length > 0) {
            zones.push({ level: 'high', title: 'High Confidence', items: highItems });
        }

        // Medium confidence zone
        const mediumItems: ConfidenceZone['items'] = [];
        if (response.causalResult) {
            const cr = response.causalResult;
            const controlledConfounders = cr.confoundersControlled?.filter(c => c.controlled) ?? [];
            const uncontrolledConfounders = cr.confoundersControlled?.filter(c => !c.controlled) ?? [];

            if (controlledConfounders.length > 0) {
                mediumItems.push({
                    text: `Confounders controlled: ${controlledConfounders.map(c => c.name).join(', ')}`,
                });
            }
            if (uncontrolledConfounders.length > 0) {
                mediumItems.push({
                    text: `⚠️ '${uncontrolledConfounders[0].name}' may be an uncontrolled confounder`,
                    action: { label: 'Add to analysis', onClick: () => onFollowUpQuestion(`Include ${uncontrolledConfounders[0].name} as a confounder`) },
                });
            }
            if (cr.refutationsPassed != null && cr.refutationsTotal != null && cr.refutationsPassed < cr.refutationsTotal) {
                const failedTests = cr.refutationDetails?.filter(t => !t.passed) ?? [];
                mediumItems.push({
                    text: `⚠️ ${failedTests.length} refutation test(s) showed sensitivity`,
                });
            }
        }
        if (response.bayesianResult && response.bayesianResult.confidenceLevel === 'medium') {
            mediumItems.push({
                text: `Moderate uncertainty: epistemic ${((response.bayesianResult.epistemicUncertainty ?? 0) * 100).toFixed(0)}%, aleatoric ${((response.bayesianResult.aleatoricUncertainty ?? 0) * 100).toFixed(0)}%`,
            });
        }
        if (mediumItems.length > 0) {
            zones.push({ level: 'medium', title: 'Medium Confidence', items: mediumItems });
        }

        // Low confidence / needs more info
        const lowItems: ConfidenceZone['items'] = [];
        if (response.domainEntropy != null && response.domainEntropy > 0.5) {
            lowItems.push({
                text: `High query entropy (${(response.domainEntropy * 100).toFixed(0)}%) - domain classification less certain`,
            });
        }
        if (response.bayesianResult?.recommendedProbe) {
            lowItems.push({
                text: response.bayesianResult.recommendedProbe,
                action: { label: 'Design probe', onClick: () => onFollowUpQuestion(response.bayesianResult?.recommendedProbe || '') },
            });
        }
        if (lowItems.length > 0) {
            zones.push({ level: 'low', title: 'Needs More Information', items: lowItems });
        }

        return zones;
    };

    const zones = getConfidenceZones();
    const suggestedQuestions = generateSuggestedQuestions(
        response.domain,
        response.causalResult?.treatment,
        response.causalResult?.outcome,
        response.causalResult?.confoundersControlled?.filter(c => c.controlled).map(c => c.name)
    );

    const getZoneStyles = (level: string) => {
        switch (level) {
            case 'high':
                return { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-800', icon: '🟢' };
            case 'medium':
                return { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-800', icon: '🟡' };
            case 'low':
                return { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', icon: '🔴' };
            default:
                return { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-800', icon: '⚪' };
        }
    };

    return (
        <div className="space-y-6">
            {/* Analysis Complete Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-xl">💬</span>
                    <h3 className="text-lg font-semibold text-gray-900">Analysis Complete</h3>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`badge ${response.domainConfidence >= 0.8
                        ? 'bg-green-500'
                        : response.domainConfidence >= 0.5
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        } text-white`}>
                        {Math.round(response.domainConfidence * 100)}% Confident
                    </span>
                    {response.guardianVerdict && (
                        <span className={`badge ${response.guardianVerdict === 'approved'
                            ? 'bg-green-500'
                            : response.guardianVerdict === 'rejected'
                                ? 'bg-red-500'
                                : 'bg-yellow-500'
                            } text-white`}>
                            {response.guardianVerdict === 'approved' ? '✓ Approved' : response.guardianVerdict === 'rejected' ? '✗ Rejected' : '⚠ Review'}
                        </span>
                    )}
                </div>
            </div>

            {/* Confidence Zones */}
            <div className="space-y-3">
                {zones.map((zone) => {
                    const styles = getZoneStyles(zone.level);
                    const isExpanded = expandedZone === zone.level;

                    return (
                        <div
                            key={zone.level}
                            className={`${styles.bg} border ${styles.border} rounded-xl overflow-hidden`}
                        >
                            <button
                                onClick={() => setExpandedZone(isExpanded ? null : zone.level)}
                                className="w-full px-4 py-3 flex items-center justify-between text-left"
                            >
                                <div className="flex items-center gap-2">
                                    <span>{styles.icon}</span>
                                    <span className={`font-semibold ${styles.text}`}>{zone.title}</span>
                                    <span className="text-xs text-gray-500">({zone.items.length} items)</span>
                                </div>
                                <svg
                                    className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>

                            {isExpanded && (
                                <div className="px-4 pb-4 space-y-2">
                                    {zone.items.map((item, idx) => (
                                        <div key={idx} className="flex items-start justify-between gap-2 text-sm">
                                            <span className={styles.text}>{item.text}</span>
                                            {item.action && (
                                                <button
                                                    onClick={item.action.onClick}
                                                    className="text-primary hover:underline whitespace-nowrap text-xs"
                                                >
                                                    {item.action.label} →
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Main Response */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                <div className="text-sm text-gray-900 leading-relaxed whitespace-pre-wrap">
                    {response.response}
                </div>
                <div className="mt-3 flex gap-2">
                    {onViewData && (
                        <button
                            onClick={onViewData}
                            className="text-xs text-primary hover:underline flex items-center gap-1"
                        >
                            📊 View Data
                        </button>
                    )}
                    <button
                        onClick={() => onViewMethodology('causal')}
                        className="text-xs text-primary hover:underline flex items-center gap-1"
                    >
                        🔬 View Methodology
                    </button>
                    <button
                        onClick={async () => {
                            try {
                                const { getExecutiveSummary } = await import('../../services/apiService');
                                const ctx = {
                                    domain: response?.domain || 'unknown',
                                    domain_confidence: response?.domainConfidence || 0,
                                    causal_effect: response?.causalResult?.effect || null,
                                    guardian_verdict: response?.guardianVerdict || 'unknown',
                                    treatment: response?.causalResult?.treatment || null,
                                    outcome: response?.causalResult?.outcome || null,
                                };
                                const summary = await getExecutiveSummary(ctx);
                                setExpandedSummary(summary);
                            } catch (e) {
                                console.error('Failed to generate executive summary:', e);
                            }
                        }}
                        className="text-xs px-3 py-1.5 bg-amber-100 text-amber-800 rounded-full hover:bg-amber-200 transition-colors flex items-center gap-1"
                    >
                        Executive Summary
                    </button>
                </div>
            </div>

            {expandedSummary && (
                <div className="mt-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-semibold text-amber-900">Executive Summary</h4>
                        <button
                            onClick={() => setExpandedSummary(null)}
                            className="text-amber-500 hover:text-amber-700 text-xs"
                        >
                            Close
                        </button>
                    </div>
                    <div className="space-y-2 text-sm">
                        <div>
                            <span className="font-medium text-amber-900">Key Finding: </span>
                            <span className="text-amber-800">{expandedSummary.key_finding}</span>
                        </div>
                        <div>
                            <span className="font-medium text-amber-900">Confidence: </span>
                            <span className="text-amber-800">{expandedSummary.confidence_level}</span>
                        </div>
                        <div>
                            <span className="font-medium text-amber-900">Risk: </span>
                            <span className="text-amber-800">{expandedSummary.risk_assessment}</span>
                        </div>
                        <div>
                            <span className="font-medium text-amber-900">Recommendation: </span>
                            <span className="text-amber-800">{expandedSummary.recommended_action}</span>
                        </div>
                        <hr className="border-amber-200" />
                        <p className="text-xs text-amber-700 italic">{expandedSummary.plain_explanation}</p>
                    </div>
                </div>
            )}

            {/* Key Insights */}
            {response.keyInsights && response.keyInsights.length > 0 && (
                <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
                        💡 Key Insights
                    </h4>
                    <ul className="space-y-2">
                        {response.keyInsights.map((insight, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                                <span className="text-primary mt-0.5">•</span>
                                <span>{insight}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Suggested Follow-ups */}
            {suggestedQuestions.length > 0 && (
                <SuggestedQuestions
                    questions={suggestedQuestions}
                    onSelectQuestion={onFollowUpQuestion}
                />
            )}

            {/* Error Display */}
            {response.error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
                    <div className="flex items-center gap-2 text-sm font-semibold text-red-900 mb-1">
                        <span>⚠️</span>
                        <span>Error</span>
                    </div>
                    <div className="text-sm text-red-700">{response.error}</div>
                </div>
            )}
        </div>
    );
};

export default ConversationalResponse;
