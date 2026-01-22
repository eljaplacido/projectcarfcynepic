/**
 * DataFlowView.tsx - Data Flow Transparency Visualization
 *
 * Shows the data pipeline from upload to analysis output:
 * - Upload → Transform → Analyze → Output flow
 * - Data quality indicators
 * - Variable relationships
 */

import React, { useState } from 'react';

interface DataFlowViewProps {
    uploadedFile?: { name: string; rows: number; columns: string[] };
    selectedVariables?: {
        treatment?: string;
        outcome?: string;
        covariates?: string[];
    };
    analysisState?: 'idle' | 'processing' | 'complete' | 'error';
}

const styles = {
    container: {
        backgroundColor: 'rgba(255, 255, 255, 0.02)',
        borderRadius: '16px',
        padding: '1.5rem',
        border: '1px solid rgba(255, 255, 255, 0.08)',
    },
    header: {
        fontSize: '1rem',
        fontWeight: 600,
        color: '#fff',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
    },
    pipeline: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '0.5rem',
        marginBottom: '1.5rem',
    },
    stage: {
        flex: 1,
        padding: '1rem',
        borderRadius: '12px',
        textAlign: 'center' as const,
        position: 'relative' as const,
    },
    stageIcon: {
        fontSize: '1.5rem',
        marginBottom: '0.5rem',
    },
    stageName: {
        fontSize: '0.75rem',
        fontWeight: 600,
        textTransform: 'uppercase' as const,
        letterSpacing: '0.05em',
    },
    stageValue: {
        fontSize: '0.8rem',
        color: '#888',
        marginTop: '0.25rem',
    },
    arrow: {
        color: 'rgba(255, 255, 255, 0.3)',
        fontSize: '1.25rem',
        flexShrink: 0,
    },
    qualitySection: {
        marginTop: '1.5rem',
    },
    qualityHeader: {
        fontSize: '0.875rem',
        fontWeight: 600,
        color: '#fff',
        marginBottom: '0.75rem',
    },
    qualityGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '0.75rem',
    },
    qualityCard: {
        padding: '1rem',
        backgroundColor: 'rgba(0, 0, 0, 0.2)',
        borderRadius: '8px',
        textAlign: 'center' as const,
    },
    qualityValue: {
        fontSize: '1.25rem',
        fontWeight: 700,
        marginBottom: '0.25rem',
    },
    qualityLabel: {
        fontSize: '0.75rem',
        color: '#888',
    },
    variableSection: {
        marginTop: '1.5rem',
    },
    variableList: {
        display: 'flex',
        flexWrap: 'wrap' as const,
        gap: '0.5rem',
    },
    variableTag: {
        padding: '0.375rem 0.75rem',
        borderRadius: '100px',
        fontSize: '0.75rem',
        fontWeight: 500,
    },
};

const DataFlowView: React.FC<DataFlowViewProps> = ({
    uploadedFile,
    selectedVariables,
    analysisState = 'idle',
}) => {
    const [expanded, setExpanded] = useState(false);

    const getStageStatus = (stage: 'upload' | 'transform' | 'analyze' | 'output') => {
        const states = {
            idle: { upload: 'pending', transform: 'pending', analyze: 'pending', output: 'pending' },
            processing: { upload: 'complete', transform: 'complete', analyze: 'active', output: 'pending' },
            complete: { upload: 'complete', transform: 'complete', analyze: 'complete', output: 'complete' },
            error: { upload: 'complete', transform: 'complete', analyze: 'error', output: 'pending' },
        };
        return states[analysisState][stage];
    };

    const getStageColor = (status: string) => {
        switch (status) {
            case 'complete': return { bg: 'rgba(16, 185, 129, 0.15)', border: '#10b981', text: '#10b981' };
            case 'active': return { bg: 'rgba(99, 102, 241, 0.15)', border: '#6366f1', text: '#6366f1' };
            case 'error': return { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', text: '#ef4444' };
            default: return { bg: 'rgba(255, 255, 255, 0.05)', border: 'rgba(255, 255, 255, 0.1)', text: '#888' };
        }
    };

    const stages = [
        { id: 'upload', icon: '📤', name: 'Upload', value: uploadedFile?.name || 'No file' },
        { id: 'transform', icon: '⚙️', name: 'Transform', value: uploadedFile ? `${uploadedFile.columns.length} cols` : '--' },
        { id: 'analyze', icon: '🔬', name: 'Analyze', value: selectedVariables?.treatment || '--' },
        { id: 'output', icon: '📊', name: 'Output', value: analysisState === 'complete' ? 'Ready' : '--' },
    ];

    // Sample quality metrics (in production, calculate from actual data)
    const qualityMetrics = [
        { label: 'Completeness', value: uploadedFile ? '94%' : '--', color: '#10b981' },
        { label: 'Validity', value: uploadedFile ? '98%' : '--', color: '#6366f1' },
        { label: 'Columns', value: uploadedFile ? String(uploadedFile.columns.length) : '--', color: '#f59e0b' },
    ];

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <span>🔄</span>
                <span>Data Flow Pipeline</span>
                <button
                    onClick={() => setExpanded(!expanded)}
                    style={{
                        marginLeft: 'auto',
                        background: 'transparent',
                        border: 'none',
                        color: '#888',
                        cursor: 'pointer',
                        fontSize: '0.875rem',
                    }}
                >
                    {expanded ? '▼ Collapse' : '▶ Expand'}
                </button>
            </div>

            {/* Pipeline Stages */}
            <div style={styles.pipeline}>
                {stages.map((stage, i) => {
                    const status = getStageStatus(stage.id as 'upload' | 'transform' | 'analyze' | 'output');
                    const colors = getStageColor(status);
                    return (
                        <React.Fragment key={stage.id}>
                            <div
                                style={{
                                    ...styles.stage,
                                    backgroundColor: colors.bg,
                                    border: `1px solid ${colors.border}`,
                                }}
                            >
                                <div style={styles.stageIcon}>{stage.icon}</div>
                                <div style={{ ...styles.stageName, color: colors.text }}>{stage.name}</div>
                                <div style={styles.stageValue}>{stage.value}</div>
                            </div>
                            {i < stages.length - 1 && <span style={styles.arrow}>→</span>}
                        </React.Fragment>
                    );
                })}
            </div>

            {expanded && (
                <>
                    {/* Data Quality */}
                    <div style={styles.qualitySection}>
                        <div style={styles.qualityHeader}>Data Quality Indicators</div>
                        <div style={styles.qualityGrid}>
                            {qualityMetrics.map((metric) => (
                                <div key={metric.label} style={styles.qualityCard}>
                                    <div style={{ ...styles.qualityValue, color: metric.color }}>{metric.value}</div>
                                    <div style={styles.qualityLabel}>{metric.label}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Selected Variables */}
                    {selectedVariables && (
                        <div style={styles.variableSection}>
                            <div style={styles.qualityHeader}>Selected Variables</div>
                            <div style={styles.variableList}>
                                {selectedVariables.treatment && (
                                    <span style={{ ...styles.variableTag, backgroundColor: 'rgba(99, 102, 241, 0.2)', color: '#6366f1' }}>
                                        T: {selectedVariables.treatment}
                                    </span>
                                )}
                                {selectedVariables.outcome && (
                                    <span style={{ ...styles.variableTag, backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#10b981' }}>
                                        O: {selectedVariables.outcome}
                                    </span>
                                )}
                                {selectedVariables.covariates?.map((cov) => (
                                    <span
                                        key={cov}
                                        style={{ ...styles.variableTag, backgroundColor: 'rgba(255, 255, 255, 0.05)', color: '#888' }}
                                    >
                                        {cov}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default DataFlowView;
