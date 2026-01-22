import React from 'react';
import type { CausalAnalysisResult, BayesianBeliefState } from '../../types/carf';

interface MethodologyModalProps {
    isOpen: boolean;
    onClose: () => void;
    type: 'causal' | 'bayesian' | 'guardian';
    causalResult?: CausalAnalysisResult | null;
    bayesianResult?: BayesianBeliefState | null;
    dataSource?: {
        name: string;
        rows: number;
        columns: number;
        uploadedAt?: string;
    };
}

const MethodologyModal: React.FC<MethodologyModalProps> = ({
    isOpen,
    onClose,
    type,
    causalResult,
    bayesianResult,
    dataSource,
}) => {
    if (!isOpen) return null;

    const handleExport = () => {
        const data = {
            type,
            timestamp: new Date().toISOString(),
            causalResult,
            bayesianResult,
            dataSource,
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `carf-methodology-${type}-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-5 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                            <span className="text-xl">🔬</span>
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-gray-900">
                                {type === 'causal' && 'Causal Analysis Methodology'}
                                {type === 'bayesian' && 'Bayesian Inference Methodology'}
                                {type === 'guardian' && 'Policy Evaluation Details'}
                            </h2>
                            <p className="text-sm text-gray-500">Transparency & traceability</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="p-5 overflow-y-auto flex-grow">
                    {type === 'causal' && causalResult && (
                        <div className="space-y-5">
                            {/* Causal Model Section */}
                            <section>
                                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                    <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs">1</span>
                                    Causal Model
                                </h3>
                                <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Framework</span>
                                        <span className="font-medium text-gray-900">DoWhy Backdoor Adjustment</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Estimator</span>
                                        <span className="font-medium text-gray-900">Linear Regression (statsmodels)</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Treatment</span>
                                        <span className="font-medium text-gray-900">{causalResult.treatment}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Outcome</span>
                                        <span className="font-medium text-gray-900">{causalResult.outcome}</span>
                                    </div>
                                </div>
                            </section>

                            {/* Data Source Section */}
                            <section>
                                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                    <span className="w-6 h-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-xs">2</span>
                                    Data Source
                                </h3>
                                <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Dataset</span>
                                        <span className="font-medium text-gray-900">{dataSource?.name || 'Mock Data'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Rows Used</span>
                                        <span className="font-medium text-gray-900">{dataSource?.rows || 'N/A'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Evidence Base</span>
                                        <span className="font-medium text-gray-900">{causalResult.evidenceBase}</span>
                                    </div>
                                </div>
                            </section>

                            {/* Confounders Section */}
                            <section>
                                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                    <span className="w-6 h-6 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-xs">3</span>
                                    Confounders Controlled
                                </h3>
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <div className="space-y-2">
                                        {causalResult.confoundersControlled.map((conf, idx) => (
                                            <div key={idx} className="flex items-center justify-between text-sm">
                                                <span className="text-gray-700">{conf.name}</span>
                                                <span className={`badge text-xs ${conf.controlled ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                                    {conf.controlled ? '✓ Controlled' : '⚠ Uncontrolled'}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </section>

                            {/* Validation Section */}
                            <section>
                                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                    <span className="w-6 h-6 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-xs">4</span>
                                    Refutation Tests
                                </h3>
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <div className="space-y-2">
                                        {causalResult.refutationDetails.map((test, idx) => (
                                            <div key={idx} className="flex items-center justify-between text-sm">
                                                <div className="flex items-center gap-2">
                                                    <span className={test.passed ? 'text-green-500' : 'text-red-500'}>
                                                        {test.passed ? '✓' : '✗'}
                                                    </span>
                                                    <span className="text-gray-700">{test.name}</span>
                                                </div>
                                                <span className="font-mono text-xs text-gray-500">p={test.pValue.toFixed(3)}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </section>

                            {/* Result Summary */}
                            <section className="bg-primary/5 border border-primary/20 rounded-lg p-4">
                                <h3 className="text-sm font-semibold text-gray-900 mb-2">Effect Estimate Summary</h3>
                                <div className="text-2xl font-bold text-primary mb-1">
                                    {causalResult.effect > 0 ? '+' : ''}{causalResult.effect.toFixed(3)} {causalResult.unit}
                                </div>
                                <div className="text-sm text-gray-600">
                                    95% CI: [{causalResult.confidenceInterval[0].toFixed(3)}, {causalResult.confidenceInterval[1].toFixed(3)}]
                                    {causalResult.pValue !== null && ` · p = ${causalResult.pValue.toFixed(4)}`}
                                </div>
                            </section>
                        </div>
                    )}

                    {type === 'bayesian' && bayesianResult && (
                        <div className="space-y-5">
                            {/* Model Section */}
                            <section>
                                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                    <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs">1</span>
                                    Bayesian Model
                                </h3>
                                <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Framework</span>
                                        <span className="font-medium text-gray-900">PyMC Active Inference</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Variable</span>
                                        <span className="font-medium text-gray-900">{bayesianResult.variable}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Confidence Level</span>
                                        <span className={`font-medium ${bayesianResult.confidenceLevel === 'high' ? 'text-green-600' : bayesianResult.confidenceLevel === 'medium' ? 'text-yellow-600' : 'text-red-600'}`}>
                                            {bayesianResult.confidenceLevel.toUpperCase()}
                                        </span>
                                    </div>
                                </div>
                            </section>

                            {/* Prior/Posterior */}
                            <section>
                                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                    <span className="w-6 h-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-xs">2</span>
                                    Prior → Posterior Update
                                </h3>
                                <div className="bg-gray-50 rounded-lg p-4 space-y-3 text-sm">
                                    <div>
                                        <div className="text-gray-600 mb-1">Prior Distribution</div>
                                        <div className="font-mono text-gray-900">
                                            N({bayesianResult.priorMean.toFixed(3)}, {bayesianResult.priorStd.toFixed(3)})
                                        </div>
                                    </div>
                                    <div className="border-t border-gray-200 pt-3">
                                        <div className="text-gray-600 mb-1">Posterior Distribution</div>
                                        <div className="font-mono text-gray-900">
                                            N({bayesianResult.posteriorMean.toFixed(3)}, {bayesianResult.posteriorStd.toFixed(3)})
                                        </div>
                                    </div>
                                </div>
                            </section>

                            {/* Uncertainty Decomposition */}
                            <section>
                                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                    <span className="w-6 h-6 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-xs">3</span>
                                    Uncertainty Decomposition
                                </h3>
                                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                                    <div>
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="text-gray-600">Epistemic (reducible with more data)</span>
                                            <span className="font-medium text-blue-600">{(bayesianResult.epistemicUncertainty * 100).toFixed(1)}%</span>
                                        </div>
                                        <div className="w-full bg-gray-200 rounded-full h-2">
                                            <div className="h-2 rounded-full bg-blue-500" style={{ width: `${bayesianResult.epistemicUncertainty * 100}%` }}></div>
                                        </div>
                                    </div>
                                    <div>
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="text-gray-600">Aleatoric (inherent randomness)</span>
                                            <span className="font-medium text-orange-600">{(bayesianResult.aleatoricUncertainty * 100).toFixed(1)}%</span>
                                        </div>
                                        <div className="w-full bg-gray-200 rounded-full h-2">
                                            <div className="h-2 rounded-full bg-orange-500" style={{ width: `${bayesianResult.aleatoricUncertainty * 100}%` }}></div>
                                        </div>
                                    </div>
                                </div>
                            </section>

                            {/* Interpretation */}
                            <section className="bg-primary/5 border border-primary/20 rounded-lg p-4">
                                <h3 className="text-sm font-semibold text-gray-900 mb-2">Interpretation</h3>
                                <p className="text-sm text-gray-700">{bayesianResult.interpretation}</p>
                                {bayesianResult.recommendedProbe && (
                                    <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                                        <div className="text-xs font-semibold text-blue-900 mb-1">💡 Recommended Probe</div>
                                        <div className="text-sm text-blue-700">{bayesianResult.recommendedProbe}</div>
                                    </div>
                                )}
                            </section>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 bg-gray-50 border-t border-gray-100 flex justify-between items-center flex-shrink-0">
                    <div className="text-xs text-gray-500">
                        Analysis timestamp: {new Date().toLocaleString()}
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={handleExport}
                            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
                        >
                            📥 Export Report
                        </button>
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary-light transition-colors"
                        >
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MethodologyModal;
