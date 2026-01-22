import React, { useState } from 'react';
import { XAxis, YAxis, CartesianGrid, Tooltip, Area, AreaChart } from 'recharts';
import type { BayesianBeliefState } from '../../types/carf';
import ExplainableWrapper from './ExplainableWrapper';

interface BayesianPanelProps {
    belief: BayesianBeliefState | null;
}

// Uncertainty Gauge Component
const UncertaintyGauge: React.FC<{ epistemic: number; aleatoric: number }> = ({ epistemic, aleatoric }) => {
    const total = epistemic + aleatoric;
    const epistemicAngle = (epistemic / total) * 180;

    return (
        <div className="relative w-32 h-20 mx-auto">
            <svg viewBox="0 0 100 60" className="w-full h-full">
                {/* Background arc */}
                <path
                    d="M 10 50 A 40 40 0 0 1 90 50"
                    fill="none"
                    stroke="#E5E7EB"
                    strokeWidth="8"
                    strokeLinecap="round"
                />
                {/* Epistemic (blue) arc */}
                <path
                    d={`M 10 50 A 40 40 0 0 1 ${10 + 80 * (epistemicAngle / 180)} ${50 - 40 * Math.sin(epistemicAngle * Math.PI / 180)}`}
                    fill="none"
                    stroke="#3B82F6"
                    strokeWidth="8"
                    strokeLinecap="round"
                />
                {/* Aleatoric (orange) arc - continues from epistemic */}
                <path
                    d={`M ${10 + 80 * (epistemicAngle / 180)} ${50 - 40 * Math.sin(epistemicAngle * Math.PI / 180)} A 40 40 0 0 1 90 50`}
                    fill="none"
                    stroke="#F97316"
                    strokeWidth="8"
                    strokeLinecap="round"
                />
                {/* Center value */}
                <text x="50" y="48" textAnchor="middle" className="text-xs font-bold fill-gray-700">
                    {Math.round(total * 100)}%
                </text>
                <text x="50" y="58" textAnchor="middle" className="text-[8px] fill-gray-500">
                    total
                </text>
            </svg>
        </div>
    );
};

const BayesianPanel: React.FC<BayesianPanelProps> = ({ belief }) => {
    const [showWhy, setShowWhy] = useState(false);

    if (!belief) {
        return (
            <div className="text-sm text-gray-500 italic">
                Bayesian analysis will appear here for Complex domain queries
            </div>
        );
    }

    // Calculate information gain (KL divergence approximation)
    const informationGain = belief.priorStd > 0 && belief.posteriorStd > 0
        ? Math.log(belief.priorStd / belief.posteriorStd) + (belief.posteriorStd ** 2 + (belief.posteriorMean - belief.priorMean) ** 2) / (2 * belief.priorStd ** 2) - 0.5
        : 0;
    const normalizedInfoGain = Math.min(1, Math.max(0, informationGain / 2)); // Normalize to 0-1

    // Generate distribution data for visualization
    const generateDistribution = (mean: number, std: number, label: string) => {
        const points = [];
        for (let x = mean - 3 * std; x <= mean + 3 * std; x += std / 10) {
            const y = (1 / (std * Math.sqrt(2 * Math.PI))) * Math.exp(-0.5 * Math.pow((x - mean) / std, 2));
            points.push({ x: x.toFixed(2), [label]: y });
        }
        return points;
    };

    const priorData = generateDistribution(belief.priorMean, belief.priorStd, 'prior');
    const posteriorData = generateDistribution(belief.posteriorMean, belief.posteriorStd, 'posterior');

    // Merge datasets
    const chartData = priorData.map((p, i) => ({
        x: p.x,
        prior: p.prior,
        posterior: posteriorData[i]?.posterior || 0,
    }));

    const getConfidenceColor = (level: string): string => {
        switch (level) {
            case 'high': return 'text-confidence-high';
            case 'medium': return 'text-confidence-medium';
            case 'low': return 'text-confidence-low';
            default: return 'text-gray-500';
        }
    };

    return (
        <div className="space-y-4">
            {/* Distribution Chart */}
            <ExplainableWrapper
                component="bayesian_posterior"
                context={{ priorMean: belief.priorMean, priorStd: belief.priorStd, posteriorMean: belief.posteriorMean, posteriorStd: belief.posteriorStd }}
                title="Prior/Posterior Distributions"
            >
                <div>
                    <div className="text-sm font-semibold text-gray-900 mb-2">Prior/Posterior Distributions</div>
                    <AreaChart width={280} height={150} data={chartData}>
                        <defs>
                            <linearGradient id="colorPrior" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#8884d8" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorPosterior" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10B981" stopOpacity={0.5} />
                                <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                        <XAxis dataKey="x" tick={{ fontSize: 10 }} stroke="#9CA3AF" />
                        <YAxis tick={{ fontSize: 10 }} stroke="#9CA3AF" />
                        <Tooltip contentStyle={{ fontSize: 12 }} />
                        <Area type="monotone" dataKey="prior" stroke="#8884d8" fillOpacity={1} fill="url(#colorPrior)" />
                        <Area type="monotone" dataKey="posterior" stroke="#10B981" fillOpacity={1} fill="url(#colorPosterior)" />
                    </AreaChart>
                </div>
            </ExplainableWrapper>

            {/* Belief Stats */}
            <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                    <div className="text-gray-500 text-xs">Posterior Mean</div>
                    <div className="font-bold text-gray-900">{belief.posteriorMean.toFixed(3)}</div>
                </div>
                <div>
                    <div className="text-gray-500 text-xs">Std Dev</div>
                    <div className="font-bold text-gray-900">{belief.posteriorStd.toFixed(3)}</div>
                </div>
            </div>

            {/* Uncertainty Decomposition with Gauge */}
            <ExplainableWrapper
                component="bayesian_epistemic"
                context={{ epistemic: belief.epistemicUncertainty, aleatoric: belief.aleatoricUncertainty }}
                title="Uncertainty Breakdown"
            >
                <div>
                    <div className="text-sm font-semibold text-gray-900 mb-2">Uncertainty Breakdown</div>

                    {/* Uncertainty Gauge */}
                    <UncertaintyGauge
                        epistemic={belief.epistemicUncertainty}
                        aleatoric={belief.aleatoricUncertainty}
                    />

                    {/* Legend */}
                    <div className="flex justify-center gap-4 mt-2 mb-3">
                        <div className="flex items-center gap-1.5">
                            <div className="w-3 h-3 rounded-full bg-blue-500" />
                            <span className="text-xs text-gray-600">Epistemic</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <div className="w-3 h-3 rounded-full bg-orange-500" />
                            <span className="text-xs text-gray-600">Aleatoric</span>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <ExplainableWrapper
                            component="bayesian_epistemic"
                            elementId="epistemic_bar"
                            context={{ value: belief.epistemicUncertainty }}
                            title="Epistemic Uncertainty"
                        >
                            <div>
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-xs text-gray-600">Epistemic (reducible)</span>
                                    <span className="text-xs font-bold text-blue-600">{(belief.epistemicUncertainty * 100).toFixed(0)}%</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                    <div
                                        className="h-2 rounded-full bg-blue-500"
                                        style={{ width: `${belief.epistemicUncertainty * 100}%` }}
                                    ></div>
                                </div>
                            </div>
                        </ExplainableWrapper>
                        <ExplainableWrapper
                            component="bayesian_aleatoric"
                            elementId="aleatoric_bar"
                            context={{ value: belief.aleatoricUncertainty }}
                            title="Aleatoric Uncertainty"
                        >
                            <div>
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-xs text-gray-600">Aleatoric (irreducible)</span>
                                    <span className="text-xs font-bold text-orange-600">{(belief.aleatoricUncertainty * 100).toFixed(0)}%</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                    <div
                                        className="h-2 rounded-full bg-orange-500"
                                        style={{ width: `${belief.aleatoricUncertainty * 100}%` }}
                                    ></div>
                                </div>
                            </div>
                        </ExplainableWrapper>
                    </div>

                    {/* Information Gain */}
                    <ExplainableWrapper
                        component="bayesian_info_gain"
                        context={{ informationGain: normalizedInfoGain }}
                        title="Information Gain"
                    >
                        <div className="mt-3 pt-3 border-t border-gray-100">
                            <div className="flex items-center justify-between mb-1">
                                <span className="text-xs text-gray-600">Information Gain</span>
                                <span className="text-xs font-bold text-green-600">{(normalizedInfoGain * 100).toFixed(0)}%</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                                <div
                                    className="h-2 rounded-full bg-green-500"
                                    style={{ width: `${normalizedInfoGain * 100}%` }}
                                ></div>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                                {normalizedInfoGain > 0.5 ? 'Strong belief update from evidence' :
                                    normalizedInfoGain > 0.2 ? 'Moderate evidence impact' : 'Limited new information'}
                            </p>
                        </div>
                    </ExplainableWrapper>
                </div>
            </ExplainableWrapper>

            {/* Why? Explanation Section */}
            <div className="pt-3 border-t border-gray-200">
                <button
                    onClick={() => setShowWhy(!showWhy)}
                    className="flex items-center justify-between w-full text-left"
                >
                    <span className="text-sm font-medium text-primary hover:text-primary/80">
                        Why these uncertainties?
                    </span>
                    <svg
                        className={`w-4 h-4 text-gray-400 transition-transform ${showWhy ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </button>

                {showWhy && (
                    <div className="mt-3 space-y-3">
                        {/* Epistemic Explanation */}
                        <div className="bg-blue-50 rounded-lg p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <div className="w-3 h-3 rounded-full bg-blue-500" />
                                <span className="text-xs font-semibold text-blue-900">Epistemic Uncertainty</span>
                            </div>
                            <p className="text-xs text-blue-700">
                                Uncertainty due to <strong>limited knowledge or data</strong>.
                                This can be reduced by gathering more observations or refining the model.
                                {belief.epistemicUncertainty > 0.5 && (
                                    <span className="block mt-1 text-blue-800">
                                        High epistemic uncertainty suggests more data collection would improve estimates.
                                    </span>
                                )}
                            </p>
                        </div>

                        {/* Aleatoric Explanation */}
                        <div className="bg-orange-50 rounded-lg p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <div className="w-3 h-3 rounded-full bg-orange-500" />
                                <span className="text-xs font-semibold text-orange-900">Aleatoric Uncertainty</span>
                            </div>
                            <p className="text-xs text-orange-700">
                                Uncertainty due to <strong>inherent randomness</strong> in the system.
                                This cannot be reduced by more data—it's fundamental variability.
                                {belief.aleatoricUncertainty > 0.5 && (
                                    <span className="block mt-1 text-orange-800">
                                        High aleatoric uncertainty indicates inherently variable outcomes.
                                    </span>
                                )}
                            </p>
                        </div>

                        {/* Actionable Insight */}
                        <div className="bg-gray-50 rounded-lg p-3">
                            <div className="text-xs font-semibold text-gray-700 mb-1">Recommendation</div>
                            <p className="text-xs text-gray-600">
                                {belief.epistemicUncertainty > belief.aleatoricUncertainty
                                    ? 'Focus on data collection and model refinement to reduce uncertainty.'
                                    : 'Uncertainty is primarily inherent—focus on robust decision-making under variability.'}
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* Confidence Level */}
            <ExplainableWrapper
                component="bayesian_confidence"
                context={{ confidenceLevel: belief.confidenceLevel }}
                title="Confidence Level"
            >
                <div className="pt-3 border-t border-gray-200">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-700">Confidence Level</span>
                        <span className={`text-sm font-bold ${getConfidenceColor(belief.confidenceLevel)}`}>
                            {belief.confidenceLevel.toUpperCase()}
                        </span>
                    </div>
                </div>
            </ExplainableWrapper>

            {/* Probe Recommendation */}
            {belief.recommendedProbe && (
                <ExplainableWrapper
                    component="bayesian_probe"
                    context={{ probe: belief.recommendedProbe }}
                    title="Recommended Probe"
                >
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <div className="text-xs font-semibold text-blue-900 mb-1">💡 Recommended Probe</div>
                        <div className="text-xs text-blue-700">{belief.recommendedProbe}</div>
                    </div>
                </ExplainableWrapper>
            )}
        </div>
    );
};

export default BayesianPanel;
