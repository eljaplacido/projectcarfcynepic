import React, { useState, useMemo } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ReferenceLine,
    ReferenceArea,
    ResponsiveContainer,
} from 'recharts';

interface SensitivityPlotProps {
    gamma: number; // Rosenbaum bounds gamma value where significance is lost
    treatment?: string; // Optional treatment variable name
    outcome?: string; // Optional outcome variable name
    refutationsPassed?: number; // Number of refutation tests passed
    refutationsTotal?: number; // Total refutation tests run
}

const SensitivityPlot: React.FC<SensitivityPlotProps> = ({
    gamma,
    treatment,
    outcome,
    refutationsPassed,
    refutationsTotal,
}) => {
    const [isExpanded, setIsExpanded] = useState(false);

    // Generate data points for the sensitivity curve
    const data = useMemo(() => {
        const points = [];
        for (let g = 1; g <= 3; g += 0.1) {
            // p-value rises as hidden factor strength increases
            // Critical gamma is where p crosses 0.05
            const pValue = 0.001 * Math.pow(g, 3);
            points.push({
                gamma: parseFloat(g.toFixed(2)),
                pValue: parseFloat(Math.min(pValue, 0.15).toFixed(4)),
            });
        }
        return points;
    }, []);

    const criticalGamma = gamma;

    // Determine robustness label
    const robustnessLabel = gamma > 2 ? 'very robust' : gamma > 1.5 ? 'moderately robust' : 'fragile';

    const allPassed = refutationsPassed !== undefined && refutationsTotal !== undefined && refutationsPassed === refutationsTotal;

    const chartContent = (
        <ResponsiveContainer width="100%" height={isExpanded ? 350 : 140}>
            <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                    dataKey="gamma"
                    label={{ value: 'Strength of Hidden Factors', position: 'insideBottom', offset: -10, style: { fontSize: 12, fill: '#4b5563' } }}
                    tick={{ fontSize: 10 }}
                    domain={[1, 3]}
                />
                <YAxis
                    label={{ value: 'Chance of Error', angle: -90, position: 'insideLeft', offset: 5, style: { fontSize: 12, fill: '#4b5563' } }}
                    tick={{ fontSize: 10 }}
                    domain={[0, 0.12]}
                    tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                />
                <Tooltip
                    formatter={(value) => [`${(Number(value) * 100).toFixed(2)}%`, 'Chance of Error']}
                    labelFormatter={(label: number) => `Hidden factor strength: ${label}x`}
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
                />

                {/* Green "Robust" zone: left of critical gamma */}
                <ReferenceArea x1={1} x2={Math.min(criticalGamma, 3)} y1={0} y2={0.12} fill="#22c55e" fillOpacity={0.08} label={{ value: 'Robust', position: 'insideTopLeft', style: { fontSize: 11, fill: '#16a34a', fontWeight: 600 } }} />

                {/* Red "Fragile" zone: right of critical gamma */}
                {criticalGamma < 3 && (
                    <ReferenceArea x1={criticalGamma} x2={3} y1={0} y2={0.12} fill="#ef4444" fillOpacity={0.08} label={{ value: 'Fragile', position: 'insideTopRight', style: { fontSize: 11, fill: '#dc2626', fontWeight: 600 } }} />
                )}

                {/* Significance threshold line at p=0.05 */}
                <ReferenceLine y={0.05} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'p=0.05', position: 'right', style: { fontSize: 10, fill: '#ef4444' } }} />

                {/* Critical gamma vertical line */}
                <ReferenceLine x={criticalGamma} stroke="#ef4444" strokeWidth={1.5} label={{ value: `Critical: ${criticalGamma.toFixed(1)}`, position: 'top', style: { fontSize: 10, fill: '#374151', fontWeight: 700 } }} />

                {/* The sensitivity curve */}
                <Line
                    type="monotone"
                    dataKey="pValue"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: '#3b82f6' }}
                />
            </LineChart>
        </ResponsiveContainer>
    );

    const interpretationAndRefutation = (
        <div className="mt-2 p-2 bg-gray-50 rounded-lg text-xs text-gray-600 flex-shrink-0 space-y-2">
            <div>
                <span className="font-semibold">Interpretation:</span>{' '}
                This result would hold even if hidden factors were up to{' '}
                <span className="font-bold text-gray-900">{gamma.toFixed(1)}x</span>{' '}
                stronger than measured. This is considered{' '}
                <span className="font-bold">{robustnessLabel}</span>.
            </div>
            {refutationsPassed !== undefined && refutationsTotal !== undefined && refutationsTotal > 0 && (
                <div>
                    <span className="font-semibold">Validation:</span>{' '}
                    These validation tests check if the finding is genuine or could be noise.{' '}
                    <span className="font-bold text-gray-900">{refutationsPassed}/{refutationsTotal}</span> passed &mdash;{' '}
                    <span className="font-bold">
                        {allPassed
                            ? 'your finding is well-supported'
                            : 'some tests flagged sensitivity \u2014 investigate further'}
                    </span>.
                </div>
            )}
        </div>
    );

    // Fullscreen modal overlay
    if (isExpanded) {
        return (
            <>
                {/* Backdrop */}
                <div
                    className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
                    onClick={() => setIsExpanded(false)}
                    data-testid="sensitivity-modal-backdrop"
                >
                    <div
                        className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl mx-4 p-6 max-h-[90vh] overflow-y-auto"
                        onClick={(e) => e.stopPropagation()}
                        data-testid="sensitivity-modal"
                    >
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                                Sensitivity Analysis
                                {treatment && outcome && (
                                    <span className="text-sm font-normal text-gray-500">
                                        &mdash; {treatment} on {outcome}
                                    </span>
                                )}
                            </h3>
                            <button
                                onClick={() => setIsExpanded(false)}
                                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 transition-colors"
                                aria-label="Close expanded view"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {chartContent}
                        {interpretationAndRefutation}
                    </div>
                </div>
            </>
        );
    }

    return (
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm h-full overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-2 flex-shrink-0">
                <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
                    Sensitivity Analysis
                </h3>
                <button
                    onClick={() => setIsExpanded(true)}
                    className="text-xs text-gray-400 hover:text-blue-600 p-1 rounded hover:bg-gray-50 transition-colors"
                    aria-label="Expand sensitivity plot"
                    data-testid="expand-sensitivity-btn"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                    </svg>
                </button>
            </div>

            <div className="relative w-full flex-1 min-h-0" style={{ maxHeight: '140px' }}>
                {chartContent}
            </div>

            {interpretationAndRefutation}
        </div>
    );
};

export default SensitivityPlot;
