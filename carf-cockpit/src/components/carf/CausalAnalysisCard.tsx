import React from 'react';
import type { CausalAnalysisResult } from '../../types/carf';
import ExplainableWrapper from './ExplainableWrapper';

interface CausalAnalysisCardProps {
    result: CausalAnalysisResult | null;
    onFollowUp?: (question: string) => void;
}

/**
 * Generate a contextual follow-up question based on the analysis result.
 */
function generateFollowUpQuestion(result: CausalAnalysisResult): string {
    // If low p-value and strong effect, ask about subgroup heterogeneity
    if (result.pValue !== null && result.pValue < 0.05 && Math.abs(result.effect) > 0) {
        return `Does the causal effect of ${result.treatment} on ${result.outcome} vary across subgroups? Are there populations where the effect is stronger or weaker?`;
    }
    // If refutation tests failed, ask about robustness
    if (result.refutationsTotal > 0 && result.refutationsPassed < result.refutationsTotal) {
        return `Some refutation tests failed for the effect of ${result.treatment} on ${result.outcome}. Which assumptions are most fragile, and how can we strengthen the analysis?`;
    }
    // If high p-value (non-significant), ask about confounders
    if (result.pValue !== null && result.pValue >= 0.05) {
        return `The effect of ${result.treatment} on ${result.outcome} is not statistically significant (p=${result.pValue.toFixed(3)}). Could uncontrolled confounders be masking a real effect?`;
    }
    // Default: ask about policy implications
    return `What are the practical implications of a ${result.effect > 0 ? '+' : ''}${result.effect.toFixed(2)} ${result.unit} effect of ${result.treatment} on ${result.outcome}?`;
}

const CausalAnalysisCard: React.FC<CausalAnalysisCardProps> = ({ result, onFollowUp }) => {
    if (!result) {
        return (
            <div className="text-sm text-gray-500 italic">
                Analysis results will appear here after query submission
            </div>
        );
    }

    const getPValueColor = (p: number | null): string => {
        if (p === null) return 'bg-gray-500';
        if (p < 0.01) return 'bg-green-500';
        if (p < 0.05) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    const followUpQuestion = generateFollowUpQuestion(result);

    return (
        <div className="space-y-4">
            {/* Effect Estimate */}
            <ExplainableWrapper
                component="causal_effect"
                context={{ effect: result.effect, unit: result.unit, pValue: result.pValue }}
                title="Causal Effect Estimate"
            >
                <div className="p-4 bg-gradient-to-r from-primary/10 to-accent/10 rounded-lg border border-primary/20 hover:border-primary/40 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">Effect Estimate</span>
                        <ExplainableWrapper
                            component="causal_pvalue"
                            context={{ pValue: result.pValue }}
                            title="Statistical Significance"
                        >
                            <span className={`badge ${getPValueColor(result.pValue)} text-white cursor-help`}>
                                p = {result.pValue?.toFixed(4) || 'N/A'}
                            </span>
                        </ExplainableWrapper>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">
                        {result.effect > 0 ? '+' : ''}{result.effect?.toFixed(2) ?? 'N/A'} {result.unit}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">{result.description}</div>

                    {/* Confidence Interval */}
                    <ExplainableWrapper
                        component="causal_ci"
                        context={{ ci: result.confidenceInterval }}
                        title="Confidence Interval"
                    >
                        <div className="mt-3">
                            <div className="text-xs text-gray-500 mb-1">95% Confidence Interval</div>
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-mono text-gray-700 cursor-help">
                                    [{result.confidenceInterval?.[0]?.toFixed(2) ?? 'N/A'}, {result.confidenceInterval?.[1]?.toFixed(2) ?? 'N/A'}]
                                </span>
                            </div>
                        </div>
                    </ExplainableWrapper>
                </div>
            </ExplainableWrapper>

            {/* Refutation Tests */}
            <ExplainableWrapper
                component="causal_refutation"
                context={{ passed: result.refutationsPassed, total: result.refutationsTotal }}
                title="Refutation Tests"
            >
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-gray-900">Refutation Tests</span>
                        <span className="badge bg-primary text-white">
                            {result.refutationsPassed}/{result.refutationsTotal} Passed
                        </span>
                    </div>
                    <div className="space-y-2">
                        {result.refutationDetails.map((test, idx) => (
                            <ExplainableWrapper
                                key={idx}
                                component="causal_refutation"
                                elementId={test.name}
                                context={{ testName: test.name, passed: test.passed, pValue: test.pValue }}
                                title={test.name}
                            >
                                <div className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100 transition-colors">
                                    <div className="flex items-center gap-2">
                                        <span className={`text-lg ${test.passed ? 'text-green-500' : 'text-red-500'}`}>
                                            {test.passed ? '✓' : '✗'}
                                        </span>
                                        <span className="text-sm text-gray-700">{test.name}</span>
                                    </div>
                                    <span className="text-xs font-mono text-gray-500">p={test.pValue?.toFixed(3) ?? 'N/A'}</span>
                                </div>
                            </ExplainableWrapper>
                        ))}
                    </div>
                </div>
            </ExplainableWrapper>

            {/* Confounders */}
            <ExplainableWrapper
                component="causal_confounder"
                context={{ confounders: result.confoundersControlled }}
                title="Confounders"
            >
                <div>
                    <div className="text-sm font-semibold text-gray-900 mb-2">Confounders</div>
                    <div className="space-y-1">
                        {result.confoundersControlled.map((conf, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-sm hover:bg-gray-50 rounded px-1 -mx-1 transition-colors">
                                <span className={`${conf.controlled ? 'text-green-500' : 'text-gray-400'}`}>
                                    {conf.controlled ? '✓' : '○'}
                                </span>
                                <span className={conf.controlled ? 'text-gray-900' : 'text-gray-500'}>
                                    {conf.name}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </ExplainableWrapper>

            {/* 3D: Ask follow-up button */}
            {onFollowUp && (
                <div className="pt-2 border-t border-gray-100">
                    <button
                        onClick={() => onFollowUp(followUpQuestion)}
                        className="w-full flex items-center justify-between p-3 bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg hover:from-indigo-100 hover:to-purple-100 transition-colors group"
                        data-testid="ask-followup-button"
                        title={followUpQuestion}
                    >
                        <div className="flex items-center gap-2 min-w-0">
                            <svg className="w-4 h-4 text-indigo-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                            <span className="text-xs font-medium text-indigo-700 truncate">
                                Ask follow-up
                            </span>
                        </div>
                        <svg className="w-3.5 h-3.5 text-indigo-400 group-hover:text-indigo-600 transition-colors flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                    </button>
                    <p className="text-[10px] text-gray-400 mt-1 px-1 truncate" title={followUpQuestion}>
                        {followUpQuestion}
                    </p>
                </div>
            )}
        </div>
    );
};

export default CausalAnalysisCard;
