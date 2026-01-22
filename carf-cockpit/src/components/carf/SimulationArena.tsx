/**
 * Simulation Arena Component
 * 
 * Side-by-side comparison view for two analysis scenarios.
 * Enables users to compare causal effects, Bayesian beliefs, and domain classifications.
 */

import React, { useState, useMemo } from 'react';
import type { AnalysisSession, CynefinDomain } from '../../types/carf';

interface SimulationArenaProps {
    isOpen: boolean;
    onClose: () => void;
    sessionA: AnalysisSession;
    sessionB: AnalysisSession;
    onRerunWithChanges?: (session: AnalysisSession, changes: Record<string, number>) => void;
}

interface ComparisonMetric {
    label: string;
    valueA: string | number | null;
    valueB: string | number | null;
    unit?: string;
    highlight?: 'a-better' | 'b-better' | 'equal' | 'neutral';
}

const getDomainColor = (domain: CynefinDomain): string => {
    const colors: Record<CynefinDomain, string> = {
        clear: 'bg-green-100 text-green-800 border-green-300',
        complicated: 'bg-blue-100 text-blue-800 border-blue-300',
        complex: 'bg-purple-100 text-purple-800 border-purple-300',
        chaotic: 'bg-red-100 text-red-800 border-red-300',
        disorder: 'bg-gray-100 text-gray-800 border-gray-300',
    };
    return colors[domain] || colors.disorder;
};

const formatNumber = (value: number | null | undefined, decimals = 2): string => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(decimals);
};

const formatPercentage = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return 'N/A';
    return `${(value * 100).toFixed(0)}%`;
};

// Analysis method toggles for simulation
interface AnalysisMethodToggles {
    causalAnalysis: boolean;
    bayesianAnalysis: boolean;
    guardianLayer: boolean;
}

// Benchmark definition
interface Benchmark {
    id: string;
    name: string;
    type: 'industry' | 'historical' | 'custom';
    value: number;
    description: string;
}

const DEFAULT_BENCHMARKS: Benchmark[] = [
    { id: 'industry-avg', name: 'Industry Average', type: 'industry', value: 0.15, description: 'Standard industry benchmark effect size' },
    { id: 'best-practice', name: 'Best Practice', type: 'industry', value: 0.25, description: 'Top quartile performance benchmark' },
    { id: 'historical', name: 'Historical Mean', type: 'historical', value: 0.12, description: 'Your historical average effect' },
];

const SimulationArena: React.FC<SimulationArenaProps> = ({
    isOpen,
    onClose,
    sessionA,
    sessionB,
    onRerunWithChanges,
}) => {
    const [activeTab, setActiveTab] = useState<'overview' | 'causal' | 'bayesian' | 'simulation' | 'parameters'>('overview');
    const [simulatedChange, setSimulatedChange] = useState<number>(0); // Percentage change in treatment

    // Enhanced simulation controls
    const [methodToggles, setMethodToggles] = useState<AnalysisMethodToggles>({
        causalAnalysis: true,
        bayesianAnalysis: true,
        guardianLayer: true,
    });
    const [selectedBenchmark, setSelectedBenchmark] = useState<string | null>(null);
    const [customBenchmark, setCustomBenchmark] = useState<number>(0);
    const [showMethodImpact, setShowMethodImpact] = useState(false);
    const [confidenceThreshold, setConfidenceThreshold] = useState<number>(70); // Percentage

    const comparisonMetrics = useMemo((): ComparisonMetric[] => {
        // Guard against undefined sessions
        if (!sessionA || !sessionB) {
            return [];
        }
        const metrics: ComparisonMetric[] = [];

        // Domain classification
        metrics.push({
            label: 'Domain',
            valueA: sessionA.domain,
            valueB: sessionB.domain,
            highlight: sessionA.domain === sessionB.domain ? 'equal' : 'neutral',
        });

        // Confidence
        metrics.push({
            label: 'Confidence',
            valueA: formatPercentage(sessionA.confidence),
            valueB: formatPercentage(sessionB.confidence),
            highlight: sessionA.confidence > sessionB.confidence ? 'a-better'
                : sessionB.confidence > sessionA.confidence ? 'b-better' : 'equal',
        });

        // Entropy (lower is better)
        const entropyA = sessionA.result.domainEntropy;
        const entropyB = sessionB.result.domainEntropy;
        metrics.push({
            label: 'Entropy',
            valueA: formatNumber(entropyA, 3),
            valueB: formatNumber(entropyB, 3),
            highlight: entropyA < entropyB ? 'a-better'
                : entropyB < entropyA ? 'b-better' : 'equal',
        });

        // Duration (lower is better)
        metrics.push({
            label: 'Duration',
            valueA: sessionA.duration,
            valueB: sessionB.duration,
            unit: 'ms',
            highlight: sessionA.duration < sessionB.duration ? 'a-better'
                : sessionB.duration < sessionA.duration ? 'b-better' : 'equal',
        });

        return metrics;
    }, [sessionA, sessionB]);

    const causalMetrics = useMemo((): ComparisonMetric[] => {
        // Guard against undefined sessions
        if (!sessionA || !sessionB) {
            return [];
        }
        const causalA = sessionA.result?.causalResult;
        const causalB = sessionB.result?.causalResult;

        if (!causalA && !causalB) return [];

        return [
            {
                label: 'Effect Size',
                valueA: causalA ? formatNumber(causalA.effect, 3) : 'N/A',
                valueB: causalB ? formatNumber(causalB.effect, 3) : 'N/A',
                unit: causalA?.unit || causalB?.unit,
                highlight: 'neutral',
            },
            {
                label: 'P-Value',
                valueA: causalA?.pValue ? formatNumber(causalA.pValue, 4) : 'N/A',
                valueB: causalB?.pValue ? formatNumber(causalB.pValue, 4) : 'N/A',
                highlight: (causalA?.pValue || 1) < (causalB?.pValue || 1) ? 'a-better'
                    : (causalB?.pValue || 1) < (causalA?.pValue || 1) ? 'b-better' : 'equal',
            },
            {
                label: 'CI Low',
                valueA: causalA ? formatNumber(causalA.confidenceInterval[0], 3) : 'N/A',
                valueB: causalB ? formatNumber(causalB.confidenceInterval[0], 3) : 'N/A',
                highlight: 'neutral',
            },
            {
                label: 'CI High',
                valueA: causalA ? formatNumber(causalA.confidenceInterval[1], 3) : 'N/A',
                valueB: causalB ? formatNumber(causalB.confidenceInterval[1], 3) : 'N/A',
                highlight: 'neutral',
            },
            {
                label: 'Refutations',
                valueA: causalA ? `${causalA.refutationsPassed}/${causalA.refutationsTotal}` : 'N/A',
                valueB: causalB ? `${causalB.refutationsPassed}/${causalB.refutationsTotal}` : 'N/A',
                highlight: (causalA?.refutationsPassed || 0) > (causalB?.refutationsPassed || 0) ? 'a-better'
                    : (causalB?.refutationsPassed || 0) > (causalA?.refutationsPassed || 0) ? 'b-better' : 'equal',
            },
        ];
    }, [sessionA, sessionB]);

    const bayesianMetrics = useMemo((): ComparisonMetric[] => {
        // Guard against undefined sessions
        if (!sessionA || !sessionB) {
            return [];
        }
        const bayesA = sessionA.result?.bayesianResult;
        const bayesB = sessionB.result?.bayesianResult;

        if (!bayesA && !bayesB) return [];

        return [
            {
                label: 'Posterior Mean',
                valueA: bayesA ? formatNumber(bayesA.posteriorMean, 4) : 'N/A',
                valueB: bayesB ? formatNumber(bayesB.posteriorMean, 4) : 'N/A',
                highlight: 'neutral',
            },
            {
                label: 'Epistemic Uncertainty',
                valueA: bayesA ? formatPercentage(bayesA.epistemicUncertainty) : 'N/A',
                valueB: bayesB ? formatPercentage(bayesB.epistemicUncertainty) : 'N/A',
                highlight: (bayesA?.epistemicUncertainty || 1) < (bayesB?.epistemicUncertainty || 1) ? 'a-better'
                    : (bayesB?.epistemicUncertainty || 1) < (bayesA?.epistemicUncertainty || 1) ? 'b-better' : 'equal',
            },
            {
                label: 'Aleatoric Uncertainty',
                valueA: bayesA ? formatPercentage(bayesA.aleatoricUncertainty) : 'N/A',
                valueB: bayesB ? formatPercentage(bayesB.aleatoricUncertainty) : 'N/A',
                highlight: 'neutral',
            },
            {
                label: 'Confidence Level',
                valueA: bayesA?.confidenceLevel || 'N/A',
                valueB: bayesB?.confidenceLevel || 'N/A',
                highlight: bayesA?.confidenceLevel === 'high' && bayesB?.confidenceLevel !== 'high' ? 'a-better'
                    : bayesB?.confidenceLevel === 'high' && bayesA?.confidenceLevel !== 'high' ? 'b-better' : 'equal',
            },
        ];
    }, [sessionA, sessionB]);

    const getHighlightClass = (highlight?: string): string => {
        switch (highlight) {
            case 'a-better': return 'bg-green-50';
            case 'b-better': return 'bg-blue-50';
            case 'equal': return 'bg-gray-50';
            default: return '';
        }
    };

    if (!isOpen) return null;

    const renderMetricsTable = (metrics: ComparisonMetric[], title: string) => {
        if (metrics.length === 0) {
            return (
                <div className="text-center text-gray-500 py-8">
                    No {title.toLowerCase()} data available for comparison
                </div>
            );
        }

        return (
            <div className="overflow-hidden rounded-xl border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                                Metric
                            </th>
                            <th className="px-4 py-3 text-center text-xs font-semibold text-primary uppercase">
                                Scenario A
                            </th>
                            <th className="px-4 py-3 text-center text-xs font-semibold text-accent uppercase">
                                Scenario B
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-100">
                        {metrics.map((metric, idx) => (
                            <tr key={idx} className={getHighlightClass(metric.highlight)}>
                                <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                    {metric.label}
                                </td>
                                <td className="px-4 py-3 text-center text-sm text-gray-700">
                                    <span className="font-semibold">{metric.valueA}</span>
                                    {metric.unit && <span className="text-gray-500 ml-1">{metric.unit}</span>}
                                    {metric.highlight === 'a-better' && (
                                        <span className="ml-2 text-green-600">✓</span>
                                    )}
                                </td>
                                <td className="px-4 py-3 text-center text-sm text-gray-700">
                                    <span className="font-semibold">{metric.valueB}</span>
                                    {metric.unit && <span className="text-gray-500 ml-1">{metric.unit}</span>}
                                    {metric.highlight === 'b-better' && (
                                        <span className="ml-2 text-green-600">✓</span>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-primary/5 via-transparent to-accent/5">
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                                <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                                Simulation Arena
                            </h2>
                            <p className="text-sm text-gray-500 mt-1">Compare two analysis scenarios side-by-side</p>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Scenario Headers */}
                    <div className="grid grid-cols-2 gap-6 mt-4">
                        <div className="p-3 bg-primary/10 rounded-lg border border-primary/20">
                            <div className="flex items-center gap-2">
                                <span className="w-6 h-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">A</span>
                                <span className={`px-2 py-0.5 text-xs rounded-full border ${getDomainColor(sessionA.domain)}`}>
                                    {sessionA.domain}
                                </span>
                            </div>
                            <p className="text-sm text-gray-700 mt-2 line-clamp-2">"{sessionA.query}"</p>
                            <p className="text-xs text-gray-500 mt-1">
                                {new Date(sessionA.timestamp).toLocaleString()}
                            </p>
                        </div>
                        <div className="p-3 bg-accent/10 rounded-lg border border-accent/20">
                            <div className="flex items-center gap-2">
                                <span className="w-6 h-6 rounded-full bg-accent text-white text-xs font-bold flex items-center justify-center">B</span>
                                <span className={`px-2 py-0.5 text-xs rounded-full border ${getDomainColor(sessionB.domain)}`}>
                                    {sessionB.domain}
                                </span>
                            </div>
                            <p className="text-sm text-gray-700 mt-2 line-clamp-2">"{sessionB.query}"</p>
                            <p className="text-xs text-gray-500 mt-1">
                                {new Date(sessionB.timestamp).toLocaleString()}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Tabs */}
                <div className="px-6 py-2 border-b border-gray-200 flex items-center gap-2">
                    {(['overview', 'causal', 'bayesian'] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${activeTab === tab
                                ? 'bg-primary text-white'
                                : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                    <button
                        onClick={() => setActiveTab('simulation')}
                        className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${activeTab === 'simulation'
                            ? 'bg-primary text-white'
                            : 'text-gray-600 hover:bg-gray-100'
                            }`}
                    >
                        <span>🎮</span> Simulation
                    </button>
                    <button
                        onClick={() => setActiveTab('parameters')}
                        className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${activeTab === 'parameters'
                            ? 'bg-primary text-white'
                            : 'text-gray-600 hover:bg-gray-100'
                            }`}
                    >
                        <span>⚙️</span> Parameters
                    </button>
                </div>

                {/* Content */}
                <div className="flex-grow overflow-y-auto p-6">
                    {activeTab === 'overview' && (
                        <div className="space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">Overview Comparison</h3>
                                {renderMetricsTable(comparisonMetrics, 'Overview')}
                            </div>

                            {/* Quick Insights */}
                            <div className="bg-gray-50 rounded-xl p-4">
                                <h4 className="font-semibold text-gray-900 mb-3">Key Differences</h4>
                                <ul className="space-y-2 text-sm">
                                    {sessionA.domain !== sessionB.domain && (
                                        <li className="flex items-start gap-2">
                                            <span className="text-accent">•</span>
                                            <span>
                                                Different domains detected: <strong className="text-primary">{sessionA.domain}</strong> vs <strong className="text-accent">{sessionB.domain}</strong>
                                            </span>
                                        </li>
                                    )}
                                    {Math.abs(sessionA.confidence - sessionB.confidence) > 0.1 && (
                                        <li className="flex items-start gap-2">
                                            <span className="text-primary">•</span>
                                            <span>
                                                Confidence gap of <strong>{Math.abs((sessionA.confidence - sessionB.confidence) * 100).toFixed(0)}%</strong>
                                            </span>
                                        </li>
                                    )}
                                    {sessionA.result.causalResult && sessionB.result.causalResult && (
                                        <li className="flex items-start gap-2">
                                            <span className="text-green-600">•</span>
                                            <span>
                                                Both scenarios have causal analysis results
                                            </span>
                                        </li>
                                    )}
                                </ul>
                            </div>
                        </div>
                    )}

                    {activeTab === 'causal' && (
                        <div className="space-y-6">
                            <h3 className="text-lg font-semibold text-gray-900">Causal Analysis Comparison</h3>
                            {renderMetricsTable(causalMetrics, 'Causal')}

                            {/* Effect Size Visualization */}
                            {sessionA.result.causalResult && sessionB.result.causalResult && (
                                <div className="bg-gray-50 rounded-xl p-4">
                                    <h4 className="font-semibold text-gray-900 mb-3">Effect Size Comparison</h4>
                                    <div className="flex items-center gap-4">
                                        <div className="flex-1">
                                            <div className="text-xs text-gray-500 mb-1">Scenario A</div>
                                            <div className="h-8 bg-primary/20 rounded flex items-center px-3">
                                                <div
                                                    className="h-4 bg-primary rounded"
                                                    style={{
                                                        width: `${Math.min(100, Math.abs(sessionA.result.causalResult.effect) * 20)}%`
                                                    }}
                                                />
                                            </div>
                                        </div>
                                        <div className="flex-1">
                                            <div className="text-xs text-gray-500 mb-1">Scenario B</div>
                                            <div className="h-8 bg-accent/20 rounded flex items-center px-3">
                                                <div
                                                    className="h-4 bg-accent rounded"
                                                    style={{
                                                        width: `${Math.min(100, Math.abs(sessionB.result.causalResult.effect) * 20)}%`
                                                    }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'bayesian' && (
                        <div className="space-y-6">
                            <h3 className="text-lg font-semibold text-gray-900">Bayesian Analysis Comparison</h3>
                            {renderMetricsTable(bayesianMetrics, 'Bayesian')}

                            {/* Uncertainty Visualization */}
                            {sessionA.result.bayesianResult && sessionB.result.bayesianResult && (
                                <div className="bg-gray-50 rounded-xl p-4">
                                    <h4 className="font-semibold text-gray-900 mb-3">Uncertainty Breakdown</h4>
                                    <div className="grid grid-cols-2 gap-6">
                                        <div>
                                            <div className="text-xs text-gray-500 mb-2 text-center">Scenario A</div>
                                            <div className="space-y-2">
                                                <div>
                                                    <div className="flex justify-between text-xs mb-1">
                                                        <span>Epistemic</span>
                                                        <span>{formatPercentage(sessionA.result.bayesianResult.epistemicUncertainty)}</span>
                                                    </div>
                                                    <div className="h-3 bg-gray-200 rounded-full">
                                                        <div
                                                            className="h-3 bg-blue-500 rounded-full"
                                                            style={{ width: `${sessionA.result.bayesianResult.epistemicUncertainty * 100}%` }}
                                                        />
                                                    </div>
                                                </div>
                                                <div>
                                                    <div className="flex justify-between text-xs mb-1">
                                                        <span>Aleatoric</span>
                                                        <span>{formatPercentage(sessionA.result.bayesianResult.aleatoricUncertainty)}</span>
                                                    </div>
                                                    <div className="h-3 bg-gray-200 rounded-full">
                                                        <div
                                                            className="h-3 bg-orange-500 rounded-full"
                                                            style={{ width: `${sessionA.result.bayesianResult.aleatoricUncertainty * 100}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-gray-500 mb-2 text-center">Scenario B</div>
                                            <div className="space-y-2">
                                                <div>
                                                    <div className="flex justify-between text-xs mb-1">
                                                        <span>Epistemic</span>
                                                        <span>{formatPercentage(sessionB.result.bayesianResult.epistemicUncertainty)}</span>
                                                    </div>
                                                    <div className="h-3 bg-gray-200 rounded-full">
                                                        <div
                                                            className="h-3 bg-blue-500 rounded-full"
                                                            style={{ width: `${sessionB.result.bayesianResult.epistemicUncertainty * 100}%` }}
                                                        />
                                                    </div>
                                                </div>
                                                <div>
                                                    <div className="flex justify-between text-xs mb-1">
                                                        <span>Aleatoric</span>
                                                        <span>{formatPercentage(sessionB.result.bayesianResult.aleatoricUncertainty)}</span>
                                                    </div>
                                                    <div className="h-3 bg-gray-200 rounded-full">
                                                        <div
                                                            className="h-3 bg-orange-500 rounded-full"
                                                            style={{ width: `${sessionB.result.bayesianResult.aleatoricUncertainty * 100}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'simulation' && (
                        <div className="space-y-6">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-semibold text-gray-900">What-If Simulation</h3>
                                <button
                                    onClick={() => setShowMethodImpact(!showMethodImpact)}
                                    className="text-sm text-primary hover:text-primary/80 flex items-center gap-1"
                                >
                                    <span>{showMethodImpact ? '▼' : '▶'}</span>
                                    Method Controls
                                </button>
                            </div>

                            {/* Method Toggles Panel */}
                            {showMethodImpact && (
                                <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl">
                                    <div className="text-sm font-semibold text-purple-900 mb-3">Analysis Method Toggles</div>
                                    <div className="text-xs text-purple-700 mb-4">
                                        Toggle methods to see how disabling specific analysis components affects the output.
                                    </div>
                                    <div className="grid grid-cols-3 gap-4">
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={methodToggles.causalAnalysis}
                                                onChange={(e) => setMethodToggles(prev => ({ ...prev, causalAnalysis: e.target.checked }))}
                                                className="accent-purple-600"
                                            />
                                            <span className={`text-sm ${methodToggles.causalAnalysis ? 'text-purple-900' : 'text-gray-400'}`}>
                                                Causal Analysis
                                            </span>
                                        </label>
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={methodToggles.bayesianAnalysis}
                                                onChange={(e) => setMethodToggles(prev => ({ ...prev, bayesianAnalysis: e.target.checked }))}
                                                className="accent-purple-600"
                                            />
                                            <span className={`text-sm ${methodToggles.bayesianAnalysis ? 'text-purple-900' : 'text-gray-400'}`}>
                                                Bayesian Analysis
                                            </span>
                                        </label>
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={methodToggles.guardianLayer}
                                                onChange={(e) => setMethodToggles(prev => ({ ...prev, guardianLayer: e.target.checked }))}
                                                className="accent-purple-600"
                                            />
                                            <span className={`text-sm ${methodToggles.guardianLayer ? 'text-purple-900' : 'text-gray-400'}`}>
                                                Guardian Layer
                                            </span>
                                        </label>
                                    </div>
                                    {(!methodToggles.causalAnalysis || !methodToggles.bayesianAnalysis || !methodToggles.guardianLayer) && (
                                        <div className="mt-4 p-3 bg-yellow-100 border border-yellow-200 rounded-lg">
                                            <div className="text-xs text-yellow-800">
                                                <strong>Impact Preview:</strong>{' '}
                                                {!methodToggles.causalAnalysis && 'No effect size estimation. '}
                                                {!methodToggles.bayesianAnalysis && 'No uncertainty quantification. '}
                                                {!methodToggles.guardianLayer && 'No policy enforcement (risky!). '}
                                            </div>
                                        </div>
                                    )}
                                    <button
                                        onClick={() => onRerunWithChanges?.(sessionA, {
                                            causalAnalysis: methodToggles.causalAnalysis ? 1 : 0,
                                            bayesianAnalysis: methodToggles.bayesianAnalysis ? 1 : 0,
                                            guardianLayer: methodToggles.guardianLayer ? 1 : 0,
                                        })}
                                        disabled={!onRerunWithChanges}
                                        className="mt-4 w-full px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                                    >
                                        Re-run with Modified Methods
                                    </button>
                                </div>
                            )}

                            {!sessionA.result.causalResult ? (
                                <div className="p-8 text-center text-gray-500 bg-gray-50 rounded-xl border border-dashed border-gray-300">
                                    Simulation requires successful causal analysis in Scenario A
                                </div>
                            ) : (
                                <div className="grid grid-cols-12 gap-8">
                                    {/* Controls */}
                                    <div className="col-span-4 space-y-4">
                                        <div className="card bg-gray-50 p-4 rounded-xl border border-gray-200">
                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                Adjust Treatment: <span className="text-primary">{sessionA.result.causalResult.treatment}</span>
                                            </label>
                                            <div className="flex items-center gap-4">
                                                <span className="text-xs text-gray-500">-50%</span>
                                                <input
                                                    type="range"
                                                    min="-50"
                                                    max="50"
                                                    step="1"
                                                    value={simulatedChange}
                                                    onChange={(e) => setSimulatedChange(parseInt(e.target.value))}
                                                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
                                                />
                                                <span className="text-xs text-gray-500">+50%</span>
                                            </div>
                                            <div className="mt-2 text-center font-mono font-bold text-primary">
                                                {simulatedChange > 0 ? '+' : ''}{simulatedChange}%
                                            </div>
                                            <p className="text-xs text-gray-500 mt-2 text-center">
                                                Change from baseline
                                            </p>
                                        </div>

                                        {/* Confidence Threshold */}
                                        <div className="card bg-gray-50 p-4 rounded-xl border border-gray-200">
                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                Confidence Threshold
                                            </label>
                                            <div className="flex items-center gap-3">
                                                <input
                                                    type="range"
                                                    min="50"
                                                    max="95"
                                                    step="5"
                                                    value={confidenceThreshold}
                                                    onChange={(e) => setConfidenceThreshold(parseInt(e.target.value))}
                                                    className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
                                                />
                                                <span className="text-sm font-mono font-bold text-gray-700 w-12">{confidenceThreshold}%</span>
                                            </div>
                                            <p className="text-xs text-gray-500 mt-2">
                                                Minimum confidence level for actionable insights
                                            </p>
                                        </div>

                                        {/* Benchmark Comparison */}
                                        <div className="card bg-gray-50 p-4 rounded-xl border border-gray-200">
                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                Compare to Benchmark
                                            </label>
                                            <select
                                                value={selectedBenchmark || ''}
                                                onChange={(e) => setSelectedBenchmark(e.target.value || null)}
                                                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                                            >
                                                <option value="">No benchmark</option>
                                                {DEFAULT_BENCHMARKS.map(b => (
                                                    <option key={b.id} value={b.id}>{b.name} ({formatNumber(b.value, 2)})</option>
                                                ))}
                                                <option value="custom">Custom value...</option>
                                            </select>
                                            {selectedBenchmark === 'custom' && (
                                                <div className="mt-2">
                                                    <input
                                                        type="number"
                                                        step="0.01"
                                                        value={customBenchmark}
                                                        onChange={(e) => setCustomBenchmark(parseFloat(e.target.value) || 0)}
                                                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                                                        placeholder="Enter benchmark value"
                                                    />
                                                </div>
                                            )}
                                        </div>

                                        <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
                                            <h4 className="text-sm font-semibold text-blue-900 mb-2">Simulation Logic</h4>
                                            <p className="text-xs text-blue-800">
                                                Based on estimated effect size of <strong>{formatNumber(sessionA.result.causalResult.effect)}</strong>.
                                                Linear extrapolation assumes constant causal effect across the range.
                                            </p>
                                        </div>
                                    </div>

                                    {/* Visualization */}
                                    <div className="col-span-8">
                                        <div className="h-64 relative bg-white border border-gray-200 rounded-xl p-6 flex flex-col justify-center items-center">
                                            <div className="text-sm text-gray-500 mb-8 absolute top-4 left-4">
                                                Predicted Outcome: <span className="font-semibold text-gray-900">{sessionA.result.causalResult.outcome}</span>
                                            </div>

                                            <div className="flex items-end gap-12 h-40">
                                                {/* Baseline Bar */}
                                                <div className="flex flex-col items-center gap-2 group">
                                                    <span className="text-xs font-medium text-gray-500 group-hover:text-gray-900 transition-colors">Baseline</span>
                                                    <div className="w-16 bg-gray-300 rounded-t-lg transition-all duration-500" style={{ height: '50%' }}></div>
                                                    <span className="text-sm font-mono text-gray-600">100.0</span>
                                                </div>

                                                {/* Arrow */}
                                                <div className="pb-8 text-gray-400">
                                                    ➜
                                                </div>

                                                {/* Simulated Bar */}
                                                <div className="flex flex-col items-center gap-2 group">
                                                    <span className="text-xs font-medium text-primary group-hover:text-primary-dark transition-colors">Simulated</span>
                                                    <div
                                                        className={`w-16 rounded-t-lg transition-all duration-300 ${simulatedChange >= 0 ? 'bg-primary' : 'bg-red-500'}`}
                                                        style={{
                                                            height: `${Math.max(10, Math.min(100, 50 + (simulatedChange * sessionA.result.causalResult.effect)))}%`
                                                        }}
                                                    ></div>
                                                    <div className="flex flex-col items-center">
                                                        <span className="text-sm font-mono font-bold text-gray-900">
                                                            {(100 + (simulatedChange * sessionA.result.causalResult.effect)).toFixed(1)}
                                                        </span>
                                                        <span className={`text-xs ${simulatedChange * sessionA.result.causalResult.effect >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                                                            {(simulatedChange * sessionA.result.causalResult.effect) > 0 ? '+' : ''}
                                                            {(simulatedChange * sessionA.result.causalResult.effect).toFixed(1)}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'parameters' && (
                        <div className="space-y-6">
                            <h3 className="text-lg font-semibold text-gray-900">Configuration Difference Results</h3>

                            <div className="overflow-hidden rounded-xl border border-gray-200">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase w-1/4">Parameter</th>
                                            <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase w-1/3">Scenario A</th>
                                            <th className="px-4 py-3 text-left text-xs font-semibold text-accent uppercase w-1/3">Scenario B</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-100">
                                        <tr>
                                            <td className="px-4 py-3 text-sm font-medium text-gray-900">Query</td>
                                            <td className="px-4 py-3 text-sm text-gray-700 font-mono text-xs">{sessionA.query}</td>
                                            <td className="px-4 py-3 text-sm text-gray-700 font-mono text-xs">{sessionB.query}</td>
                                        </tr>
                                        <tr>
                                            <td className="px-4 py-3 text-sm font-medium text-gray-900">Variables</td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {sessionA.result.causalResult ? (
                                                    <div className="space-y-1">
                                                        <div className="text-xs"><span className="text-gray-500">T:</span> {sessionA.result.causalResult.treatment}</div>
                                                        <div className="text-xs"><span className="text-gray-500">O:</span> {sessionA.result.causalResult.outcome}</div>
                                                    </div>
                                                ) : <span className="text-gray-400 italic">None</span>}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {sessionB.result.causalResult ? (
                                                    <div className="space-y-1">
                                                        <div className="text-xs"><span className="text-gray-500">T:</span> {sessionB.result.causalResult.treatment}</div>
                                                        <div className="text-xs"><span className="text-gray-500">O:</span> {sessionB.result.causalResult.outcome}</div>
                                                    </div>
                                                ) : <span className="text-gray-400 italic">None</span>}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td className="px-4 py-3 text-sm font-medium text-gray-900">Confounders</td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {sessionA.result.causalResult?.confoundersControlled?.map(c => c.name).join(', ') || '-'}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {sessionB.result.causalResult?.confoundersControlled?.map(c => c.name).join(', ') || '-'}
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                            <span className="w-3 h-3 rounded bg-green-100 border border-green-300"></span>
                            Better value
                        </span>
                        <span className="flex items-center gap-1">
                            <span className="w-3 h-3 rounded bg-gray-100 border border-gray-300"></span>
                            Equal
                        </span>
                    </div>
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SimulationArena;
