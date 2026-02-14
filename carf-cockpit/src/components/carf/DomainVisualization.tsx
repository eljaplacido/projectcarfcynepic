/**
 * DomainVisualization.tsx - Domain-Specific Visualizations
 *
 * Renders different UI components based on Cynefin domain classification:
 * - Clear: Decision tree / checklist
 * - Complicated: Expert analysis panel (handled by existing Causal DAG)
 * - Complex: Uncertainty exploration (handled by existing Bayesian panel)
 * - Chaotic: Circuit breaker / rapid response
 * - Disorder: Escalation / clarification prompts
 */

import React from 'react';
import type { CynefinDomain, CausalAnalysisResult, BayesianBeliefState } from '../../types/carf';

interface DomainVisualizationProps {
    domain: CynefinDomain | null;
    confidence: number;
    onEscalate?: () => void;
    onAction?: (action: string) => void;
    isProcessing?: boolean;
    causalResult?: CausalAnalysisResult | null;
    bayesianResult?: BayesianBeliefState | null;
}

// Styles
const styles = {
    container: {
        borderRadius: '12px',
        padding: '1.25rem',
        marginTop: '1rem',
        border: '1px solid rgba(255, 255, 255, 0.08)',
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '1rem',
        fontSize: '0.875rem',
        fontWeight: 600,
    },
    checklistItem: {
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '0.75rem 1rem',
        backgroundColor: 'rgba(0, 0, 0, 0.2)',
        borderRadius: '8px',
        marginBottom: '0.5rem',
        cursor: 'pointer',
        transition: 'all 0.2s',
    },
    checkbox: {
        width: '20px',
        height: '20px',
        borderRadius: '4px',
        border: '2px solid rgba(255, 255, 255, 0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '0.75rem',
    },
    actionButton: {
        padding: '0.75rem 1.25rem',
        borderRadius: '8px',
        border: 'none',
        fontWeight: 600,
        cursor: 'pointer',
        fontSize: '0.875rem',
        transition: 'all 0.2s',
        flex: 1,
    },
    circuitBreaker: {
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '1rem',
        backgroundColor: 'rgba(239, 68, 68, 0.15)',
        borderRadius: '8px',
        border: '1px solid rgba(239, 68, 68, 0.3)',
    },
    statusIndicator: {
        width: '12px',
        height: '12px',
        borderRadius: '50%',
        animation: 'pulse 2s infinite',
    },
    rapidAction: {
        display: 'flex',
        gap: '0.5rem',
        marginTop: '1rem',
        flexWrap: 'wrap' as const,
    },
};

// ============================================================================
// Clear Domain: Decision Checklist
// ============================================================================
const ClearDomainView: React.FC<{ onAction?: (action: string) => void }> = ({
    onAction,
}) => {
    const [checked, setChecked] = React.useState<Record<string, boolean>>({});

    const steps = [
        { id: 'review', label: 'Review analysis results', icon: '📊' },
        { id: 'validate', label: 'Validate assumptions', icon: '✓' },
        { id: 'implement', label: 'Implement recommendation', icon: '🚀' },
        { id: 'monitor', label: 'Set up monitoring', icon: '📈' },
    ];

    return (
        <div style={{ ...styles.container, backgroundColor: 'rgba(16, 185, 129, 0.1)' }}>
            <div style={{ ...styles.header, color: '#10b981' }}>
                <span>✓</span>
                <span>Clear Domain - Decision Checklist</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#888', marginBottom: '1rem' }}>
                Follow these standard steps to implement the recommendation
            </div>

            {steps.map((step) => (
                <div
                    key={step.id}
                    style={{
                        ...styles.checklistItem,
                        opacity: checked[step.id] ? 0.6 : 1,
                    }}
                    onClick={() => {
                        setChecked((prev) => ({ ...prev, [step.id]: !prev[step.id] }));
                    }}
                >
                    <div
                        style={{
                            ...styles.checkbox,
                            backgroundColor: checked[step.id] ? '#10b981' : 'transparent',
                            borderColor: checked[step.id] ? '#10b981' : 'rgba(255,255,255,0.3)',
                        }}
                    >
                        {checked[step.id] && '✓'}
                    </div>
                    <span style={{ marginRight: '0.5rem' }}>{step.icon}</span>
                    <span style={{ color: '#fff', textDecoration: checked[step.id] ? 'line-through' : 'none' }}>
                        {step.label}
                    </span>
                </div>
            ))}

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                <button
                    style={{
                        ...styles.actionButton,
                        backgroundColor: '#10b981',
                        color: '#fff',
                    }}
                    onClick={() => onAction?.('apply')}
                >
                    Apply Recommendation
                </button>
            </div>
        </div>
    );
};

// ============================================================================
// Chaotic Domain: Circuit Breaker
// ============================================================================
const ChaoticDomainView: React.FC<{ onAction?: (action: string) => void }> = ({
    onAction,
}) => {
    const [circuitOpen, setCircuitOpen] = React.useState(true);

    return (
        <div style={{ ...styles.container, backgroundColor: 'rgba(239, 68, 68, 0.1)' }}>
            <div style={{ ...styles.header, color: '#ef4444' }}>
                <span>⚡</span>
                <span>Chaotic Domain - Rapid Response Mode</span>
            </div>

            {/* Circuit Breaker Status */}
            <div style={styles.circuitBreaker}>
                <div
                    style={{
                        ...styles.statusIndicator,
                        backgroundColor: circuitOpen ? '#ef4444' : '#10b981',
                    }}
                />
                <div>
                    <div style={{ color: '#fff', fontWeight: 600 }}>
                        Circuit Breaker: {circuitOpen ? 'OPEN' : 'CLOSED'}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#888' }}>
                        {circuitOpen
                            ? 'System is protecting against unstable conditions'
                            : 'Normal operations resumed'}
                    </div>
                </div>
                <button
                    style={{
                        marginLeft: 'auto',
                        padding: '0.5rem 1rem',
                        borderRadius: '6px',
                        border: 'none',
                        backgroundColor: circuitOpen ? '#10b981' : '#ef4444',
                        color: '#fff',
                        fontWeight: 600,
                        cursor: 'pointer',
                    }}
                    onClick={() => setCircuitOpen(!circuitOpen)}
                >
                    {circuitOpen ? 'Close Circuit' : 'Open Circuit'}
                </button>
            </div>

            {/* Rapid Response Actions */}
            <div style={{ marginTop: '1rem', fontSize: '0.875rem', color: '#fff' }}>
                <strong>Immediate Actions Available:</strong>
            </div>
            <div style={styles.rapidAction}>
                <button
                    style={{
                        ...styles.actionButton,
                        backgroundColor: '#ef4444',
                        color: '#fff',
                    }}
                    onClick={() => onAction?.('halt')}
                >
                    🛑 Halt Operations
                </button>
                <button
                    style={{
                        ...styles.actionButton,
                        backgroundColor: '#f59e0b',
                        color: '#000',
                    }}
                    onClick={() => onAction?.('fallback')}
                >
                    🔄 Activate Fallback
                </button>
                <button
                    style={{
                        ...styles.actionButton,
                        backgroundColor: '#6366f1',
                        color: '#fff',
                    }}
                    onClick={() => onAction?.('escalate')}
                >
                    📞 Escalate
                </button>
            </div>
        </div>
    );
};

// ============================================================================
// Disorder Domain: Escalation / Clarification
// ============================================================================
const DisorderDomainView: React.FC<{
    onEscalate?: () => void;
    onAction?: (action: string) => void;
}> = ({ onEscalate, onAction }) => {
    const [clarification, setClarification] = React.useState('');

    return (
        <div style={{ ...styles.container, backgroundColor: 'rgba(156, 163, 175, 0.1)' }}>
            <div style={{ ...styles.header, color: '#9ca3af' }}>
                <span>❓</span>
                <span>Disorder Domain - Clarification Required</span>
            </div>

            <div
                style={{
                    padding: '1rem',
                    backgroundColor: 'rgba(251, 191, 36, 0.1)',
                    borderRadius: '8px',
                    border: '1px solid rgba(251, 191, 36, 0.3)',
                    marginBottom: '1rem',
                }}
            >
                <div style={{ color: '#fbbf24', fontWeight: 600, marginBottom: '0.5rem' }}>
                    ⚠️ Unable to classify with confidence
                </div>
                <div style={{ fontSize: '0.875rem', color: '#888' }}>
                    The system needs additional context to proceed. Please provide clarification
                    or escalate to a human expert.
                </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.8rem', color: '#888', display: 'block', marginBottom: '0.5rem' }}>
                    Add clarification:
                </label>
                <textarea
                    style={{
                        width: '100%',
                        padding: '0.75rem',
                        borderRadius: '8px',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        backgroundColor: 'rgba(0, 0, 0, 0.3)',
                        color: '#fff',
                        fontSize: '0.875rem',
                        resize: 'vertical',
                        minHeight: '80px',
                    }}
                    placeholder="Provide additional context about your query..."
                    value={clarification}
                    onChange={(e) => setClarification(e.target.value)}
                />
            </div>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                    style={{
                        ...styles.actionButton,
                        backgroundColor: '#6366f1',
                        color: '#fff',
                    }}
                    onClick={() => onAction?.('resubmit')}
                    disabled={!clarification.trim()}
                >
                    Resubmit with Clarification
                </button>
                <button
                    style={{
                        ...styles.actionButton,
                        backgroundColor: '#f59e0b',
                        color: '#000',
                    }}
                    onClick={onEscalate}
                >
                    ⚠️ Escalate to Human
                </button>
            </div>
        </div>
    );
};

// ============================================================================
// Complicated Domain: Expert Analysis Path
// ============================================================================
const ComplicatedDomainView: React.FC<{
    onAction?: (action: string) => void;
    causalResult?: CausalAnalysisResult | null;
}> = ({ onAction, causalResult }) => {
    return (
        <div style={{ ...styles.container, backgroundColor: 'rgba(59, 130, 246, 0.1)' }}>
            <div style={{ ...styles.header, color: '#3b82f6' }}>
                <span>🔬</span>
                <span>Complicated Domain - Expert Analysis</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#888', marginBottom: '1rem' }}>
                This problem requires expert decomposition. Review causal pathways below.
            </div>

            {/* Effect Summary */}
            {causalResult && (
                <div style={{
                    padding: '1rem',
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    borderRadius: '8px',
                    border: '1px solid rgba(59, 130, 246, 0.2)',
                    marginBottom: '0.75rem',
                }}>
                    <div style={{ color: '#60a5fa', fontWeight: 600, marginBottom: '0.5rem' }}>
                        Causal Effect: {causalResult.effect.toFixed(3)} {causalResult.unit}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                        {causalResult.treatment} → {causalResult.outcome}
                        {causalResult.pValue !== null && ` (p=${causalResult.pValue.toFixed(4)})`}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                        Refutations: {causalResult.refutationsPassed}/{causalResult.refutationsTotal} passed
                    </div>
                </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                <button
                    style={{ ...styles.actionButton, backgroundColor: '#3b82f6', color: '#fff' }}
                    onClick={() => onAction?.('deep_analysis')}
                >
                    🔍 Deep Analysis
                </button>
                <button
                    style={{ ...styles.actionButton, backgroundColor: '#1e40af', color: '#fff' }}
                    onClick={() => onAction?.('sensitivity_check')}
                >
                    📐 Sensitivity Check
                </button>
            </div>
        </div>
    );
};

// ============================================================================
// Complex Domain: Uncertainty Exploration
// ============================================================================
const ComplexDomainView: React.FC<{
    onAction?: (action: string) => void;
    bayesianResult?: BayesianBeliefState | null;
}> = ({ onAction, bayesianResult }) => {
    return (
        <div style={{ ...styles.container, backgroundColor: 'rgba(139, 92, 246, 0.1)' }}>
            <div style={{ ...styles.header, color: '#8b5cf6' }}>
                <span>🌀</span>
                <span>Complex Domain - Uncertainty Exploration</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#888', marginBottom: '1rem' }}>
                Emergent patterns detected. Explore uncertainty landscape with probes.
            </div>

            {/* Uncertainty Breakdown */}
            {bayesianResult && (
                <div style={{
                    padding: '1rem',
                    backgroundColor: 'rgba(139, 92, 246, 0.08)',
                    borderRadius: '8px',
                    border: '1px solid rgba(139, 92, 246, 0.2)',
                    marginBottom: '0.75rem',
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                        <span style={{ fontSize: '0.8rem', color: '#a78bfa' }}>Total Uncertainty</span>
                        <span style={{ fontSize: '0.8rem', color: '#fff', fontWeight: 600 }}>
                            {(bayesianResult.totalUncertainty * 100).toFixed(1)}%
                        </span>
                    </div>
                    {/* Uncertainty bar */}
                    <div style={{
                        height: '8px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.1)',
                        overflow: 'hidden', display: 'flex',
                    }}>
                        <div style={{
                            width: `${bayesianResult.epistemicUncertainty * 100}%`,
                            backgroundColor: '#8b5cf6', transition: 'width 0.5s',
                        }} />
                        <div style={{
                            width: `${bayesianResult.aleatoricUncertainty * 100}%`,
                            backgroundColor: '#c084fc', transition: 'width 0.5s',
                        }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
                        <span style={{ fontSize: '0.7rem', color: '#a78bfa' }}>
                            Epistemic: {(bayesianResult.epistemicUncertainty * 100).toFixed(0)}%
                        </span>
                        <span style={{ fontSize: '0.7rem', color: '#c084fc' }}>
                            Aleatoric: {(bayesianResult.aleatoricUncertainty * 100).toFixed(0)}%
                        </span>
                    </div>

                    {bayesianResult.recommendedProbe && (
                        <div style={{
                            marginTop: '0.75rem', padding: '0.5rem',
                            backgroundColor: 'rgba(139, 92, 246, 0.15)', borderRadius: '6px',
                            fontSize: '0.8rem', color: '#c4b5fd',
                        }}>
                            💡 Probe: {bayesianResult.recommendedProbe}
                        </div>
                    )}
                </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                <button
                    style={{ ...styles.actionButton, backgroundColor: '#8b5cf6', color: '#fff' }}
                    onClick={() => onAction?.('run_probe')}
                >
                    🔮 Run Probe
                </button>
                <button
                    style={{ ...styles.actionButton, backgroundColor: '#6d28d9', color: '#fff' }}
                    onClick={() => onAction?.('explore_scenarios')}
                >
                    🌐 Explore Scenarios
                </button>
            </div>
        </div>
    );
};

// ============================================================================
// Main Component
// ============================================================================
const DomainVisualization: React.FC<DomainVisualizationProps> = ({
    domain,
    onEscalate,
    onAction,
    isProcessing,
    causalResult,
    bayesianResult,
}) => {
    if (!domain || isProcessing) {
        return null;
    }

    switch (domain) {
        case 'clear':
            return <ClearDomainView onAction={onAction} />;
        case 'complicated':
            return <ComplicatedDomainView onAction={onAction} causalResult={causalResult} />;
        case 'complex':
            return <ComplexDomainView onAction={onAction} bayesianResult={bayesianResult} />;
        case 'chaotic':
            return <ChaoticDomainView onAction={onAction} />;
        case 'disorder':
            return <DisorderDomainView onEscalate={onEscalate} onAction={onAction} />;
        default:
            return null;
    }
};

export default DomainVisualization;
