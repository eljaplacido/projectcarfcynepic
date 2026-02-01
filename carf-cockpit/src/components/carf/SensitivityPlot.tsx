import React from 'react';

interface SensitivityPlotProps {
    gamma: number; // Rosenbaum bounds gamma value where significance is lost
}

const SensitivityPlot: React.FC<SensitivityPlotProps> = ({ gamma }) => {
    // Generate mock data points for the curve
    const generateCurve = () => {
        const points = [];
        for (let g = 1; g <= 3; g += 0.2) {
            // Mock p-value function: rises as Gamma increases (hidden bias)
            // As Gamma increases, p-value increases. If p > 0.05, we lose significance.
            // Critical Gamma is where p = 0.05
            const pValue = 0.001 * Math.pow(g, 3);
            points.push({ g, p: pValue });
        }
        return points;
    };

    const data = generateCurve();
    const criticalGamma = gamma;

    // Simple SVG plotting
    const width = 400;
    const height = 200;
    const padding = 30;

    const xScale = (g: number) => padding + ((g - 1) / 2) * (width - 2 * padding);
    const yScale = (p: number) => height - padding - (p / 0.1) * (height - 2 * padding); // Scale p=0.1 to top

    const pathD = `M ${data.map(d => `${xScale(d.g)},${yScale(d.p)}`).join(' L ')}`;

    return (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm h-full">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <span>🛡️</span> Sensitivity Analysis
            </h3>

            <div className="relative w-full h-48">
                {/* Y-axis label */}
                <div className="absolute -left-2 top-1/2 -rotate-90 text-xs text-gray-400">p-value</div>

                <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
                    {/* Axes */}
                    <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#e5e7eb" strokeWidth="2" />
                    <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#e5e7eb" strokeWidth="2" />

                    {/* Threshold Line (p=0.05) */}
                    <line
                        x1={padding}
                        y1={yScale(0.05)}
                        x2={width - padding}
                        y2={yScale(0.05)}
                        stroke="#ef4444"
                        strokeWidth="1"
                        strokeDasharray="4 4"
                    />
                    <text x={width - padding + 5} y={yScale(0.05)} className="text-[10px] fill-red-500" dominantBaseline="middle">p=0.05</text>

                    {/* The Curve */}
                    <path d={pathD} fill="none" stroke="#3b82f6" strokeWidth="2" />

                    {/* Critical Marker */}
                    <circle cx={xScale(criticalGamma)} cy={yScale(0.05)} r="4" fill="#ef4444" />
                    <line
                        x1={xScale(criticalGamma)}
                        y1={yScale(0.05)}
                        x2={xScale(criticalGamma)}
                        y2={height - padding}
                        stroke="#ef4444"
                        strokeWidth="1"
                    />
                    <text x={xScale(criticalGamma)} y={height - padding + 15} className="text-xs font-bold fill-gray-700" textAnchor="middle">
                        Γ = {criticalGamma.toFixed(1)}
                    </text>
                </svg>

                {/* X-axis label */}
                <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 text-xs text-gray-400">Hidden Bias Magnitude (Γ)</div>
            </div>

            <div className="mt-4 p-3 bg-gray-50 rounded-lg text-xs text-gray-600">
                <span className="font-semibold block mb-1">Interpretation:</span>
                Result remains statistically significant even if an unobserved confounder increases the odds of treatment by a factor of <span className="font-bold text-gray-900">{gamma.toFixed(1)}x</span>.
            </div>
        </div>
    );
};

export default SensitivityPlot;
