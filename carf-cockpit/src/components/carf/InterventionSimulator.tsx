import React, { useState, useEffect, useMemo, useCallback } from 'react';

export interface SimulationParams {
    treatmentValue: number;
    confounderAdjustments: Record<string, number>;
    predictedOutcome: number;
    percentChange: number;
}

interface ConfounderDef {
    name: string;
    baseValue: number;
    effectOnOutcome: number;
    unit?: string;
}

interface InterventionSimulatorProps {
    treatment: string;
    outcome: string;
    baseTreatmentValue: number;
    baseOutcomeValue: number;
    effectSize: number; // Unit change in outcome per unit change in treatment
    unit?: string;
    confounders?: ConfounderDef[];
    onRunSimulation?: (params: SimulationParams) => void;
    sessionId?: string;
}

interface SavedScenario {
    id: string;
    name: string;
    treatmentValue: number;
    confounderValues: Record<string, number>;
    predictedOutcome: number;
    percentChange: number;
    timestamp: number;
}

const InterventionSimulator: React.FC<InterventionSimulatorProps> = ({
    treatment,
    outcome,
    baseTreatmentValue,
    baseOutcomeValue,
    effectSize,
    unit = 'units',
    confounders: initialConfounders,
    onRunSimulation,
    sessionId: _sessionId,
}) => {
    const [simulatedValue, setSimulatedValue] = useState<number>(baseTreatmentValue);
    const [predictedOutcome, setPredictedOutcome] = useState<number>(baseOutcomeValue);
    const [percentChange, setPercentChange] = useState<number>(0);

    // Confounder state: user-adjustable values
    const [confounders, setConfounders] = useState<ConfounderDef[]>(initialConfounders || []);
    const [confounderValues, setConfounderValues] = useState<Record<string, number>>({});
    const [showAddParam, setShowAddParam] = useState(false);
    const [newParamName, setNewParamName] = useState('');
    const [newParamEffect, setNewParamEffect] = useState(0.1);

    // Saved scenarios
    const [savedScenarios, setSavedScenarios] = useState<SavedScenario[]>([]);

    // Initialize confounder values when confounders prop changes
    useEffect(() => {
        if (initialConfounders) {
            setConfounders(initialConfounders);
            const initial: Record<string, number> = {};
            initialConfounders.forEach((c) => {
                initial[c.name] = c.baseValue;
            });
            setConfounderValues((prev) => {
                // Preserve existing adjustments for confounders that still exist
                const merged = { ...initial };
                Object.keys(prev).forEach((key) => {
                    if (key in merged) {
                        merged[key] = prev[key];
                    }
                });
                return merged;
            });
        }
    }, [initialConfounders]);

    // Calculate combined predicted outcome from treatment + all confounders
    useEffect(() => {
        const treatmentDelta = simulatedValue - baseTreatmentValue;
        let outcomeDelta = treatmentDelta * effectSize;

        // Add confounder contributions
        confounders.forEach((c) => {
            const currentVal = confounderValues[c.name] ?? c.baseValue;
            const confounderDelta = currentVal - c.baseValue;
            outcomeDelta += confounderDelta * c.effectOnOutcome;
        });

        const predicted = baseOutcomeValue + outcomeDelta;
        setPredictedOutcome(predicted);

        if (baseOutcomeValue !== 0) {
            setPercentChange((outcomeDelta / baseOutcomeValue) * 100);
        }
    }, [simulatedValue, baseTreatmentValue, baseOutcomeValue, effectSize, confounders, confounderValues]);

    const handleReset = () => {
        setSimulatedValue(baseTreatmentValue);
        const resetVals: Record<string, number> = {};
        confounders.forEach((c) => {
            resetVals[c.name] = c.baseValue;
        });
        setConfounderValues(resetVals);
    };

    const handleConfounderChange = useCallback((name: string, value: number) => {
        setConfounderValues((prev) => ({ ...prev, [name]: value }));
    }, []);

    const handleAddParameter = () => {
        if (!newParamName.trim()) return;
        const newConfounder: ConfounderDef = {
            name: newParamName.trim(),
            baseValue: 0,
            effectOnOutcome: newParamEffect,
            unit,
        };
        setConfounders((prev) => [...prev, newConfounder]);
        setConfounderValues((prev) => ({ ...prev, [newConfounder.name]: 0 }));
        setNewParamName('');
        setNewParamEffect(0.1);
        setShowAddParam(false);
    };

    const handleRemoveParameter = (name: string) => {
        setConfounders((prev) => prev.filter((c) => c.name !== name));
        setConfounderValues((prev) => {
            const next = { ...prev };
            delete next[name];
            return next;
        });
    };

    const handleRunSimulation = () => {
        if (onRunSimulation) {
            onRunSimulation({
                treatmentValue: simulatedValue,
                confounderAdjustments: { ...confounderValues },
                predictedOutcome,
                percentChange,
            });
        }
    };

    const handleSaveScenario = () => {
        const scenario: SavedScenario = {
            id: `scenario_${Date.now()}`,
            name: `Scenario ${savedScenarios.length + 1}`,
            treatmentValue: simulatedValue,
            confounderValues: { ...confounderValues },
            predictedOutcome,
            percentChange,
            timestamp: Date.now(),
        };
        setSavedScenarios((prev) => [...prev, scenario]);
    };

    // Rank parameters by absolute effect magnitude to highlight strongest
    const rankedParams = useMemo(() => {
        const params = confounders.map((c) => ({
            name: c.name,
            absEffect: Math.abs(c.effectOnOutcome),
            effectOnOutcome: c.effectOnOutcome,
        }));
        params.sort((a, b) => b.absEffect - a.absEffect);
        return params;
    }, [confounders]);

    const strongestParam = rankedParams.length > 0 ? rankedParams[0] : null;

    return (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    What-If Simulator
                </h3>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleSaveScenario}
                        className="text-xs text-gray-500 hover:text-green-600 flex items-center gap-1 px-2 py-1 rounded bg-gray-50 hover:bg-green-50 transition-colors"
                        data-testid="save-scenario-btn"
                    >
                        Save Scenario
                    </button>
                    <button
                        onClick={handleReset}
                        className="text-xs text-gray-500 hover:text-blue-600 flex items-center gap-1 px-2 py-1 rounded bg-gray-50 hover:bg-blue-50 transition-colors"
                    >
                        Reset
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Left: Parameter sliders */}
                <div className="space-y-5">
                    {/* Primary treatment slider */}
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <label className="font-medium text-gray-700">
                                Adjust {treatment}
                                <span className="ml-1 text-xs text-blue-500">(primary)</span>
                            </label>
                            <span className="font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                                {simulatedValue.toFixed(1)}
                            </span>
                        </div>
                        <input
                            type="range"
                            min={baseTreatmentValue * 0.5}
                            max={baseTreatmentValue * 1.5}
                            step={baseTreatmentValue * 0.01 || 0.01}
                            value={simulatedValue}
                            onChange={(e) => setSimulatedValue(Number(e.target.value))}
                            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                            data-testid="treatment-slider"
                        />
                        <div className="flex justify-between text-xs text-gray-400 font-mono">
                            <span>-50%</span>
                            <span>Baseline</span>
                            <span>+50%</span>
                        </div>
                    </div>

                    {/* Confounder sliders */}
                    {confounders.map((c) => {
                        const currentVal = confounderValues[c.name] ?? c.baseValue;
                        const minVal = c.baseValue - 5;
                        const maxVal = c.baseValue + 5;
                        return (
                            <div key={c.name} className="space-y-2 p-3 bg-gray-50 rounded-lg border border-gray-100" data-testid={`confounder-${c.name}`}>
                                <div className="flex justify-between items-center text-sm">
                                    <label className="font-medium text-gray-600 flex items-center gap-1">
                                        {c.name}
                                        <span className="text-xs text-gray-400">
                                            (effect: {c.effectOnOutcome > 0 ? '+' : ''}{c.effectOnOutcome.toFixed(2)})
                                        </span>
                                    </label>
                                    <div className="flex items-center gap-2">
                                        <span className="font-mono text-purple-600 bg-purple-50 px-2 py-0.5 rounded text-xs">
                                            {currentVal.toFixed(1)} {c.unit || ''}
                                        </span>
                                        <button
                                            onClick={() => handleRemoveParameter(c.name)}
                                            className="text-gray-300 hover:text-red-500 transition-colors"
                                            aria-label={`Remove ${c.name}`}
                                            data-testid={`remove-${c.name}`}
                                        >
                                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                                <input
                                    type="range"
                                    min={minVal}
                                    max={maxVal}
                                    step={0.1}
                                    value={currentVal}
                                    onChange={(e) => handleConfounderChange(c.name, Number(e.target.value))}
                                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-500"
                                />
                            </div>
                        );
                    })}

                    {/* Add Parameter button */}
                    {!showAddParam ? (
                        <button
                            onClick={() => setShowAddParam(true)}
                            className="w-full py-2 px-3 border-2 border-dashed border-gray-200 rounded-lg text-sm text-gray-500 hover:text-blue-600 hover:border-blue-300 transition-colors flex items-center justify-center gap-1"
                            data-testid="add-parameter-btn"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                            Add Parameter
                        </button>
                    ) : (
                        <div className="p-3 border border-blue-200 bg-blue-50 rounded-lg space-y-2" data-testid="add-parameter-form">
                            <input
                                type="text"
                                placeholder="Parameter name"
                                value={newParamName}
                                onChange={(e) => setNewParamName(e.target.value)}
                                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                                data-testid="new-param-name"
                            />
                            <div className="flex items-center gap-2">
                                <label className="text-xs text-gray-500 whitespace-nowrap">Effect size:</label>
                                <input
                                    type="number"
                                    step={0.01}
                                    value={newParamEffect}
                                    onChange={(e) => setNewParamEffect(Number(e.target.value))}
                                    className="w-20 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                                    data-testid="new-param-effect"
                                />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleAddParameter}
                                    className="px-3 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 transition-colors"
                                    data-testid="confirm-add-param"
                                >
                                    Add
                                </button>
                                <button
                                    onClick={() => { setShowAddParam(false); setNewParamName(''); }}
                                    className="px-3 py-1 bg-gray-200 text-gray-600 text-xs rounded hover:bg-gray-300 transition-colors"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Right: Predicted outcome + insights */}
                <div className="space-y-4">
                    {/* Combined predicted outcome */}
                    <div className="relative p-5 rounded-lg border-2 border-dashed border-gray-200 bg-gray-50/50" data-testid="predicted-outcome">
                        <div className="absolute top-1/2 -left-5 transform -translate-y-1/2 md:block hidden">
                            <span className="text-gray-300 text-xl">&rarr;</span>
                        </div>

                        <div className="text-sm text-gray-500 mb-1">{outcome} (Predicted)</div>
                        <div className="text-3xl font-bold text-gray-900 flex items-baseline gap-2">
                            {predictedOutcome.toFixed(1)}
                            <span className="text-sm font-normal text-gray-500">{unit}</span>
                        </div>

                        <div className={`mt-2 text-sm font-medium flex items-center gap-1 ${percentChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            <span>{percentChange >= 0 ? '\u25B2' : '\u25BC'}</span>
                            {Math.abs(percentChange).toFixed(1)}% {percentChange >= 0 ? 'increase' : 'decrease'}
                        </div>
                    </div>

                    {/* Platform suggestion: strongest effect */}
                    {strongestParam && confounders.length > 0 && (
                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg" data-testid="strongest-effect-hint">
                            <div className="text-xs font-semibold text-amber-800 mb-1">Strongest lever</div>
                            <div className="text-sm text-amber-700">
                                <span className="font-bold">{strongestParam.name}</span> has the largest effect on the outcome
                                (effect size: {strongestParam.effectOnOutcome > 0 ? '+' : ''}{strongestParam.effectOnOutcome.toFixed(2)} per unit).
                                Adjusting this parameter will shift predictions the most.
                            </div>
                        </div>
                    )}

                    {/* Run Simulation button */}
                    {onRunSimulation && (
                        <button
                            onClick={handleRunSimulation}
                            className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                            data-testid="run-simulation-btn"
                        >
                            Run Simulation
                        </button>
                    )}

                    {/* Saved Scenarios */}
                    {savedScenarios.length > 0 && (
                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Saved Scenarios</h4>
                            {savedScenarios.map((s) => (
                                <div key={s.id} className="p-2 bg-gray-50 rounded border border-gray-100 flex items-center justify-between text-xs">
                                    <span className="font-medium text-gray-700">{s.name}</span>
                                    <span className={`font-mono ${s.percentChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                        {s.percentChange >= 0 ? '+' : ''}{s.percentChange.toFixed(1)}%
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="mt-6 pt-4 border-t border-gray-100 flex items-start gap-3">
                <p className="text-xs text-gray-500 leading-relaxed">
                    This simulation assumes a linear causal relationship (Effect Size: <span className="font-mono text-gray-700">{effectSize.toFixed(2)}</span>).
                    {confounders.length > 0 && (
                        <> Accounting for <span className="font-mono text-gray-700">{confounders.length}</span> additional parameter{confounders.length > 1 ? 's' : ''}.</>
                    )}{' '}
                    The projection is ceteris paribus (all else equal) and valid only within the support of the observed data.
                </p>
            </div>
        </div>
    );
};

export default InterventionSimulator;
