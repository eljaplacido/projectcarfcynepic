/**
 * StrategyComparisonPanel - Compare fast oracle vs rigorous DoWhy analysis
 * 
 * This component displays side-by-side comparison of:
 * - ChimeraOracle fast prediction (~50ms)
 * - Full DoWhy causal analysis with refutations (~2-5s)
 * 
 * Helps users understand trade-offs between speed and rigor.
 */

import React, { useState } from 'react';

interface OraclePrediction {
    effect_estimate: number;
    confidence_interval: [number, number];
    feature_importance: Record<string, number>;
    used_model: string;
    prediction_time_ms: number;
}

interface DoWhyResult {
    effect: number;
    p_value: number | null;
    ci_low: number;
    ci_high: number;
    refutations_passed: number;
    refutations_total: number;
    confounders_controlled: number;
    treatment: string;
    outcome: string;
}

interface StrategyComparisonProps {
    scenarioId: string;
    context: Record<string, unknown>;
    onStrategySelect?: (strategy: 'fast' | 'rigorous') => void;
}

const StrategyComparisonPanel: React.FC<StrategyComparisonProps> = ({
    scenarioId,
    context,
}) => {
    const [oracleResult, setOracleResult] = useState<OraclePrediction | null>(null);
    const [dowhyResult] = useState<DoWhyResult | null>(null);
    const [loading, setLoading] = useState<'none' | 'oracle' | 'dowhy' | 'both'>('none');
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'compare' | 'details'>('compare');

    const fetchOraclePrediction = async () => {
        setLoading('oracle');
        setError(null);
        try {
            const response = await fetch('/api/oracle/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    scenario_id: scenarioId,
                    context: context,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Oracle prediction failed');
            }

            const data = await response.json();
            setOracleResult(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading('none');
        }
    };

    const getEffectIcon = (effect: number) => {
        if (effect < -5) return '📉';
        if (effect > 5) return '📈';
        return '➡️';
    };

    const formatEffect = (effect: number, unit: string = 'units') => {
        const sign = effect > 0 ? '+' : '';
        return `${sign}${effect.toFixed(2)} ${unit}`;
    };

    const getRecommendation = () => {
        if (!oracleResult) return null;

        const effectSize = Math.abs(oracleResult.effect_estimate);
        const ciWidth = oracleResult.confidence_interval[1] - oracleResult.confidence_interval[0];

        if (effectSize > 50 && ciWidth < 50) {
            return {
                strategy: 'fast' as const,
                reason: 'Large, confident effect - fast prediction sufficient',
                confidence: 'high',
            };
        } else if (ciWidth > 100) {
            return {
                strategy: 'rigorous' as const,
                reason: 'Wide confidence interval - rigorous analysis recommended',
                confidence: 'low',
            };
        } else {
            return {
                strategy: 'rigorous' as const,
                reason: 'Moderate effect - consider rigorous analysis for important decisions',
                confidence: 'medium',
            };
        }
    };

    const recommendation = getRecommendation();

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            {/* Header */}
            <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                            ⚖️ Strategy Comparison
                        </h3>
                        <p className="text-xs text-gray-500 mt-1">
                            Compare fast oracle predictions vs rigorous causal analysis
                        </p>
                    </div>
                    {recommendation && (
                        <span className={`px-2 py-1 rounded text-xs font-medium ${recommendation.confidence === 'high'
                                ? 'bg-green-100 text-green-700'
                                : 'bg-yellow-100 text-yellow-700'
                            }`}>
                            {recommendation.strategy === 'fast' ? '⚡ Fast OK' : '🔬 Rigorous Recommended'}
                        </span>
                    )}
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-200">
                <button
                    onClick={() => setActiveTab('compare')}
                    className={`flex-1 px-4 py-2 text-xs font-medium border-b-2 transition-colors ${activeTab === 'compare'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                >
                    Compare
                </button>
                <button
                    onClick={() => setActiveTab('details')}
                    className={`flex-1 px-4 py-2 text-xs font-medium border-b-2 transition-colors ${activeTab === 'details'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                >
                    Details
                </button>
            </div>

            {/* Content */}
            <div className="p-4">
                {activeTab === 'compare' && (
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            {/* Fast Oracle Column */}
                            <div className="border-2 border-blue-200 rounded-lg p-3">
                                <h4 className="text-xs font-semibold text-gray-900 flex items-center gap-1 mb-2">
                                    ⚡ Fast Oracle
                                </h4>
                                <div className="flex items-center gap-1 text-xs text-gray-500 mb-3">
                                    🕐 ~50ms latency
                                </div>

                                {!oracleResult ? (
                                    <button
                                        onClick={fetchOraclePrediction}
                                        disabled={loading === 'oracle'}
                                        className="w-full px-3 py-2 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50 transition-colors"
                                    >
                                        {loading === 'oracle' ? 'Loading...' : 'Run Fast Prediction'}
                                    </button>
                                ) : (
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-gray-600">Effect:</span>
                                            <span className="font-mono text-xs flex items-center gap-1">
                                                {getEffectIcon(oracleResult.effect_estimate)}
                                                {formatEffect(oracleResult.effect_estimate, 'tCO2e')}
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between text-xs text-gray-500">
                                            <span>95% CI:</span>
                                            <span className="font-mono">
                                                [{oracleResult.confidence_interval[0].toFixed(1)}, {oracleResult.confidence_interval[1].toFixed(1)}]
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between text-xs text-gray-500">
                                            <span>Time:</span>
                                            <span className="font-mono">{oracleResult.prediction_time_ms.toFixed(1)}ms</span>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Rigorous DoWhy Column */}
                            <div className="border-2 border-purple-200 rounded-lg p-3">
                                <h4 className="text-xs font-semibold text-gray-900 flex items-center gap-1 mb-2">
                                    🔬 Rigorous DoWhy
                                </h4>
                                <div className="flex items-center gap-1 text-xs text-gray-500 mb-3">
                                    🕐 ~2-5s latency
                                </div>

                                {!dowhyResult ? (
                                    <button
                                        disabled
                                        className="w-full px-3 py-2 text-xs bg-gray-100 text-gray-500 rounded cursor-not-allowed"
                                    >
                                        Use /query endpoint
                                    </button>
                                ) : (
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-gray-600">Effect:</span>
                                            <span className="font-mono text-xs flex items-center gap-1">
                                                {getEffectIcon(dowhyResult.effect)}
                                                {formatEffect(dowhyResult.effect, 'tCO2e')}
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between text-xs">
                                            <span>Refutations:</span>
                                            <span className={`px-1.5 py-0.5 rounded text-xs ${dowhyResult.refutations_passed === dowhyResult.refutations_total
                                                    ? 'bg-green-100 text-green-700'
                                                    : 'bg-red-100 text-red-700'
                                                }`}>
                                                {dowhyResult.refutations_passed}/{dowhyResult.refutations_total} passed
                                            </span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Recommendation */}
                        {recommendation && (
                            <div className="p-3 bg-blue-50 rounded-lg flex items-start gap-2">
                                <span className="text-blue-500">ℹ️</span>
                                <div className="text-xs text-gray-700">
                                    <span className="font-medium">Recommendation: </span>
                                    {recommendation.reason}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'details' && (
                    <div className="space-y-4">
                        <div>
                            <h4 className="text-xs font-medium text-gray-900 mb-2">When to use Fast Oracle</h4>
                            <ul className="text-xs text-gray-600 space-y-1">
                                <li>• Real-time scoring in production systems</li>
                                <li>• Batch processing large datasets</li>
                                <li>• Initial screening before deep analysis</li>
                                <li>• Effect modifiers are within training distribution</li>
                            </ul>
                        </div>
                        <div>
                            <h4 className="text-xs font-medium text-gray-900 mb-2">When to use Rigorous Analysis</h4>
                            <ul className="text-xs text-gray-600 space-y-1">
                                <li>• High-stakes business decisions</li>
                                <li>• Novel scenarios outside training data</li>
                                <li>• When refutation tests are required</li>
                                <li>• Regulatory or audit requirements</li>
                            </ul>
                        </div>
                    </div>
                )}

                {error && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
                        {error}
                    </div>
                )}
            </div>
        </div>
    );
};

export default StrategyComparisonPanel;
