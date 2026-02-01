import React, { useState, useEffect } from 'react';

interface InterventionSimulatorProps {
    treatment: string;
    outcome: string;
    baseTreatmentValue: number;
    baseOutcomeValue: number;
    effectSize: number; // Unit change in outcome per unit change in treatment
    unit?: string;
}

const InterventionSimulator: React.FC<InterventionSimulatorProps> = ({
    treatment,
    outcome,
    baseTreatmentValue,
    baseOutcomeValue,
    effectSize,
    unit = 'units'
}) => {
    const [simulatedValue, setSimulatedValue] = useState<number>(baseTreatmentValue);
    const [predictedOutcome, setPredictedOutcome] = useState<number>(baseOutcomeValue);
    const [percentChange, setPercentChange] = useState<number>(0);

    useEffect(() => {
        const delta = simulatedValue - baseTreatmentValue;
        const outcomeDelta = delta * effectSize;
        setPredictedOutcome(baseOutcomeValue + outcomeDelta);

        if (baseOutcomeValue !== 0) {
            setPercentChange((outcomeDelta / baseOutcomeValue) * 100);
        }
    }, [simulatedValue, baseTreatmentValue, baseOutcomeValue, effectSize]);

    const handleReset = () => {
        setSimulatedValue(baseTreatmentValue);
    };

    return (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <span>🎛️</span> What-If Simulator
                </h3>
                <button
                    onClick={handleReset}
                    className="text-xs text-gray-500 hover:text-blue-600 flex items-center gap-1 px-2 py-1 rounded bg-gray-50 hover:bg-blue-50 transition-colors"
                >
                    <span>↺</span> Reset
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
                {/* Input: Intervention (Treatment) */}
                <div className="space-y-4">
                    <div className="flex justify-between text-sm">
                        <label className="font-medium text-gray-700">Adjust {treatment}</label>
                        <span className="font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                            {simulatedValue.toFixed(1)}
                        </span>
                    </div>

                    <input
                        type="range"
                        min={baseTreatmentValue * 0.5}
                        max={baseTreatmentValue * 1.5}
                        step={baseTreatmentValue * 0.01}
                        value={simulatedValue}
                        onChange={(e) => setSimulatedValue(Number(e.target.value))}
                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                    />

                    <div className="flex justify-between text-xs text-gray-400 font-mono">
                        <span>-50%</span>
                        <span>Baseline</span>
                        <span>+50%</span>
                    </div>
                </div>

                {/* Output: Prediction (Outcome) */}
                <div className="relative p-5 rounded-lg border-2 border-dashed border-gray-200 bg-gray-50/50">
                    <div className="absolute top-1/2 -left-5 transform -translate-y-1/2 md:block hidden">
                        <span className="text-gray-300 text-xl">➔</span>
                    </div>

                    <div className="text-sm text-gray-500 mb-1">{outcome} (Predicted)</div>
                    <div className="text-3xl font-bold text-gray-900 flex items-baseline gap-2">
                        {predictedOutcome.toFixed(1)}
                        <span className="text-sm font-normal text-gray-500">{unit}</span>
                    </div>

                    <div className={`mt-2 text-sm font-medium flex items-center gap-1 ${percentChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        <span>{percentChange >= 0 ? '▲' : '▼'}</span>
                        {Math.abs(percentChange).toFixed(1)}% {percentChange >= 0 ? 'increase' : 'decrease'}
                    </div>
                </div>
            </div>

            <div className="mt-6 pt-4 border-t border-gray-100 flex items-start gap-3">
                <span className="text-lg">ℹ️</span>
                <p className="text-xs text-gray-500 leading-relaxed">
                    This simulation assumes a linear causal relationship (Effect Size: <span className="font-mono text-gray-700">{effectSize.toFixed(2)}</span>).
                    The projection is ceteris paribus (all else equal) and valid only within the support of the observed data.
                </p>
            </div>
        </div>
    );
};

export default InterventionSimulator;
