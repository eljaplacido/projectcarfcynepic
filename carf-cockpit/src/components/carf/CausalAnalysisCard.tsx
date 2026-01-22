import React from 'react';
import type { CausalAnalysisResult } from '../../types/carf';
import ExplainableWrapper from './ExplainableWrapper';

interface CausalAnalysisCardProps {
    result: CausalAnalysisResult | null;
}

const CausalAnalysisCard: React.FC<CausalAnalysisCardProps> = ({ result }) => {
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
        </div>
    );
};

export default CausalAnalysisCard;
