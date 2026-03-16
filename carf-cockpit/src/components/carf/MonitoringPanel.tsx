// Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
/**
 * MonitoringPanel — Phase 18 monitoring dashboard.
 *
 * Three-tab layout: Drift Monitor | Bias Audit | Convergence
 *
 * Provides real-time visibility into routing distribution drift,
 * memory bias auditing, and router retraining convergence.
 */

import React, { useEffect, useState } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    LineChart, Line, Legend,
} from 'recharts';
import type { DriftStatus, BiasReport, ConvergenceStatus, DriftSnapshot } from '../../types/carf';
import {
    getMonitoringDriftStatus,
    getMonitoringDriftHistory,
    resetMonitoringDriftBaseline,
    getMonitoringBiasAudit,
    getMonitoringConvergence,
} from '../../services/apiService';

type MonitoringTab = 'drift' | 'bias' | 'convergence';

interface MonitoringPanelProps {
    /** Optional injected data for testing */
    initialDriftStatus?: DriftStatus | null;
    initialBiasReport?: BiasReport | null;
    initialConvergenceStatus?: ConvergenceStatus | null;
    initialDriftHistory?: DriftSnapshot[];
    /** If true, skip auto-fetch on mount */
    skipAutoFetch?: boolean;
}

const TAB_CONFIG: { id: MonitoringTab; label: string; icon: string }[] = [
    { id: 'drift', label: 'Drift Monitor', icon: 'D' },
    { id: 'bias', label: 'Bias Audit', icon: 'B' },
    { id: 'convergence', label: 'Convergence', icon: 'C' },
];

const MonitoringPanel: React.FC<MonitoringPanelProps> = ({
    initialDriftStatus = null,
    initialBiasReport = null,
    initialConvergenceStatus = null,
    initialDriftHistory = [],
    skipAutoFetch = false,
}) => {
    const [activeTab, setActiveTab] = useState<MonitoringTab>('drift');
    const [loading, setLoading] = useState(!skipAutoFetch);
    const [error, setError] = useState<string | null>(null);

    const [driftStatus, setDriftStatus] = useState<DriftStatus | null>(initialDriftStatus);
    const [driftHistory, setDriftHistory] = useState<DriftSnapshot[]>(initialDriftHistory);
    const [biasReport, setBiasReport] = useState<BiasReport | null>(initialBiasReport);
    const [convergenceStatus, setConvergenceStatus] = useState<ConvergenceStatus | null>(initialConvergenceStatus);
    const [resetting, setResetting] = useState(false);

    useEffect(() => {
        if (skipAutoFetch) return;

        const fetchAll = async () => {
            setLoading(true);
            setError(null);
            try {
                const [drift, history, bias, convergence] = await Promise.allSettled([
                    getMonitoringDriftStatus(),
                    getMonitoringDriftHistory(20),
                    getMonitoringBiasAudit(),
                    getMonitoringConvergence(),
                ]);

                if (drift.status === 'fulfilled') setDriftStatus(drift.value);
                if (history.status === 'fulfilled') setDriftHistory(history.value.snapshots);
                if (bias.status === 'fulfilled') setBiasReport(bias.value);
                if (convergence.status === 'fulfilled') setConvergenceStatus(convergence.value);

                // If all failed, show error
                const allFailed = [drift, history, bias, convergence].every(r => r.status === 'rejected');
                if (allFailed) {
                    setError('Failed to fetch monitoring data. Backend may be unavailable.');
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to fetch monitoring data');
            } finally {
                setLoading(false);
            }
        };

        fetchAll();
    }, [skipAutoFetch]);

    const handleResetBaseline = async () => {
        setResetting(true);
        try {
            await resetMonitoringDriftBaseline();
            // Refresh drift data
            const [drift, history] = await Promise.allSettled([
                getMonitoringDriftStatus(),
                getMonitoringDriftHistory(20),
            ]);
            if (drift.status === 'fulfilled') setDriftStatus(drift.value);
            if (history.status === 'fulfilled') setDriftHistory(history.value.snapshots);
        } catch (err) {
            console.error('Failed to reset baseline:', err);
        } finally {
            setResetting(false);
        }
    };

    // ---- Drift Monitor Tab ----
    const renderDriftTab = () => {
        if (!driftStatus && !loading) {
            return <div style={{ padding: '24px', textAlign: 'center', color: '#9CA3AF' }}>No drift data available yet.</div>;
        }

        // Build comparison chart data from baseline vs current distribution
        const distributionData = driftStatus
            ? Object.keys({ ...driftStatus.baseline_distribution, ...driftStatus.current_distribution }).map(domain => ({
                  domain,
                  baseline: driftStatus.baseline_distribution[domain] ?? 0,
                  current: driftStatus.current_distribution[domain] ?? 0,
              }))
            : [];

        // Build KL-divergence history from snapshots
        const klHistoryData = driftHistory.map((snap, idx) => ({
            index: idx + 1,
            kl_divergence: snap.kl_divergence,
            timestamp: snap.timestamp,
        }));

        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Summary Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
                    <div style={{
                        padding: '16px', borderRadius: '8px', border: '1px solid #374151',
                        backgroundColor: '#1F2937',
                    }}>
                        <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>Total Observations</div>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: '#F9FAFB' }}>{driftStatus?.total_observations ?? 0}</div>
                    </div>
                    <div style={{
                        padding: '16px', borderRadius: '8px', border: '1px solid #374151',
                        backgroundColor: '#1F2937',
                    }}>
                        <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>KL Divergence</div>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: driftStatus?.last_snapshot?.drift_detected ? '#EF4444' : '#10B981' }}>
                            {driftStatus?.last_snapshot?.kl_divergence?.toFixed(4) ?? 'N/A'}
                        </div>
                    </div>
                    <div style={{
                        padding: '16px', borderRadius: '8px', border: '1px solid #374151',
                        backgroundColor: '#1F2937',
                    }}>
                        <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>Alert Count</div>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: (driftStatus?.alert_count ?? 0) > 0 ? '#F59E0B' : '#10B981' }}>
                            {driftStatus?.alert_count ?? 0}
                        </div>
                    </div>
                    <div style={{
                        padding: '16px', borderRadius: '8px', border: '1px solid #374151',
                        backgroundColor: '#1F2937',
                    }}>
                        <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>Drift Detected</div>
                        <div style={{
                            fontSize: '14px', fontWeight: 600, padding: '4px 12px', borderRadius: '9999px', display: 'inline-block',
                            backgroundColor: driftStatus?.last_snapshot?.drift_detected ? '#7F1D1D' : '#064E3B',
                            color: driftStatus?.last_snapshot?.drift_detected ? '#FCA5A5' : '#6EE7B7',
                        }}>
                            {driftStatus?.last_snapshot?.drift_detected ? 'YES' : 'NO'}
                        </div>
                    </div>
                </div>

                {/* Distribution Comparison Chart */}
                {distributionData.length > 0 && (
                    <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '16px', border: '1px solid #374151' }}>
                        <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '12px' }}>
                            Baseline vs Current Distribution
                        </h4>
                        <div style={{ width: '100%', height: 220 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={distributionData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="domain" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                                    <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                                    <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', color: '#F9FAFB' }} />
                                    <Legend wrapperStyle={{ fontSize: 11, color: '#9CA3AF' }} />
                                    <Bar dataKey="baseline" name="Baseline" fill="#3B82F6" radius={[3, 3, 0, 0]} />
                                    <Bar dataKey="current" name="Current" fill="#8B5CF6" radius={[3, 3, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {/* KL Divergence History */}
                {klHistoryData.length > 0 && (
                    <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '16px', border: '1px solid #374151' }}>
                        <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '12px' }}>
                            KL Divergence History
                        </h4>
                        <div style={{ width: '100%', height: 180 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={klHistoryData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="index" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                                    <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                                    <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', color: '#F9FAFB' }} />
                                    <Line type="monotone" dataKey="kl_divergence" stroke="#F59E0B" strokeWidth={2} dot={{ r: 3 }} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {/* Reset Baseline Button */}
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                        onClick={handleResetBaseline}
                        disabled={resetting}
                        data-testid="reset-baseline-btn"
                        style={{
                            padding: '8px 20px', borderRadius: '6px', border: '1px solid #374151',
                            backgroundColor: resetting ? '#374151' : '#1F2937',
                            color: resetting ? '#6B7280' : '#60A5FA',
                            cursor: resetting ? 'not-allowed' : 'pointer',
                            fontSize: '13px', fontWeight: 500,
                        }}
                    >
                        {resetting ? 'Resetting...' : 'Reset Baseline'}
                    </button>
                </div>
            </div>
        );
    };

    // ---- Bias Audit Tab ----
    const renderBiasTab = () => {
        if (!biasReport && !loading) {
            return <div style={{ padding: '24px', textAlign: 'center', color: '#9CA3AF' }}>No bias audit data available yet.</div>;
        }

        const domainData = biasReport
            ? Object.entries(biasReport.domain_percentages).map(([domain, pct]) => ({
                  domain,
                  percentage: Number((pct * 100).toFixed(1)),
                  count: biasReport.domain_distribution[domain] ?? 0,
              }))
            : [];

        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Overall Verdict */}
                {biasReport && (
                    <div style={{
                        padding: '16px', borderRadius: '8px', border: '1px solid #374151',
                        backgroundColor: biasReport.overall_bias_detected ? '#7F1D1D' : '#064E3B',
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    }}>
                        <div>
                            <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>
                                Overall Bias Verdict
                            </div>
                            <div style={{
                                fontSize: '18px', fontWeight: 700,
                                color: biasReport.overall_bias_detected ? '#FCA5A5' : '#6EE7B7',
                            }}>
                                {biasReport.overall_bias_detected ? 'Bias Detected' : 'No Bias Detected'}
                            </div>
                        </div>
                        <div style={{
                            padding: '6px 16px', borderRadius: '9999px', fontSize: '12px', fontWeight: 600,
                            backgroundColor: biasReport.overall_bias_detected ? '#991B1B' : '#065F46',
                            color: biasReport.overall_bias_detected ? '#FCA5A5' : '#6EE7B7',
                        }} data-testid="bias-verdict-badge">
                            {biasReport.total_entries} entries analyzed
                        </div>
                    </div>
                )}

                {/* Statistics Grid */}
                {biasReport && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
                        <div style={{ padding: '16px', borderRadius: '8px', border: '1px solid #374151', backgroundColor: '#1F2937' }}>
                            <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>Chi-Squared</div>
                            <div style={{ fontSize: '20px', fontWeight: 700, color: '#F9FAFB' }}>{biasReport.chi_squared_statistic.toFixed(3)}</div>
                            <div style={{ fontSize: '11px', color: '#6B7280', marginTop: '2px' }}>p-value: {biasReport.chi_squared_p_value.toFixed(4)}</div>
                        </div>
                        <div style={{ padding: '16px', borderRadius: '8px', border: '1px solid #374151', backgroundColor: '#1F2937' }}>
                            <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>Quality Disparity</div>
                            <div style={{ fontSize: '20px', fontWeight: 700, color: biasReport.quality_biased ? '#EF4444' : '#10B981' }}>
                                {biasReport.quality_disparity.toFixed(3)}
                            </div>
                        </div>
                        <div style={{ padding: '16px', borderRadius: '8px', border: '1px solid #374151', backgroundColor: '#1F2937' }}>
                            <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>Approval Rate Disparity</div>
                            <div style={{ fontSize: '20px', fontWeight: 700, color: '#F9FAFB' }}>
                                {biasReport.approval_rate_disparity.toFixed(3)}
                            </div>
                        </div>
                    </div>
                )}

                {/* Domain Distribution Chart */}
                {domainData.length > 0 && (
                    <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '16px', border: '1px solid #374151' }}>
                        <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '12px' }}>
                            Domain Distribution
                        </h4>
                        <div style={{ width: '100%', height: 200 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={domainData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="domain" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                                    <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                                    <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', color: '#F9FAFB' }} />
                                    <Bar dataKey="percentage" name="Percentage (%)" fill="#8B5CF6" radius={[3, 3, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {/* Findings List */}
                {biasReport && biasReport.findings.length > 0 && (
                    <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '16px', border: '1px solid #374151' }}>
                        <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '12px' }}>
                            Findings
                        </h4>
                        <ul style={{ margin: 0, padding: '0 0 0 20px', listStyleType: 'disc' }}>
                            {biasReport.findings.map((finding, idx) => (
                                <li key={idx} style={{ fontSize: '13px', color: '#D1D5DB', marginBottom: '6px' }} data-testid={`bias-finding-${idx}`}>
                                    {finding}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        );
    };

    // ---- Convergence Tab ----
    const renderConvergenceTab = () => {
        if (!convergenceStatus && !loading) {
            return <div style={{ padding: '24px', textAlign: 'center', color: '#9CA3AF' }}>No convergence data available yet.</div>;
        }

        const conv = convergenceStatus?.convergence;
        const historyData = conv?.history?.map(h => ({
            epoch: h.epoch,
            accuracy: h.accuracy,
        })) ?? [];

        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Summary Cards */}
                {conv && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
                        <div style={{ padding: '16px', borderRadius: '8px', border: '1px solid #374151', backgroundColor: '#1F2937' }}>
                            <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>Total Epochs</div>
                            <div style={{ fontSize: '24px', fontWeight: 700, color: '#F9FAFB' }}>{convergenceStatus?.total_epochs ?? 0}</div>
                        </div>
                        <div style={{ padding: '16px', borderRadius: '8px', border: '1px solid #374151', backgroundColor: '#1F2937' }}>
                            <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>Converged</div>
                            <div style={{
                                fontSize: '14px', fontWeight: 600, padding: '4px 12px', borderRadius: '9999px', display: 'inline-block',
                                backgroundColor: conv.converged ? '#064E3B' : '#374151',
                                color: conv.converged ? '#6EE7B7' : '#9CA3AF',
                            }} data-testid="convergence-badge">
                                {conv.converged ? 'YES' : 'NO'}
                            </div>
                        </div>
                        <div style={{ padding: '16px', borderRadius: '8px', border: '1px solid #374151', backgroundColor: '#1F2937' }}>
                            <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>Plateau</div>
                            <div style={{
                                fontSize: '14px', fontWeight: 600, padding: '4px 12px', borderRadius: '9999px', display: 'inline-block',
                                backgroundColor: conv.plateau_detected ? '#78350F' : '#374151',
                                color: conv.plateau_detected ? '#FDE68A' : '#9CA3AF',
                            }}>
                                {conv.plateau_detected ? 'Detected' : 'None'}
                            </div>
                        </div>
                        <div style={{ padding: '16px', borderRadius: '8px', border: '1px solid #374151', backgroundColor: '#1F2937' }}>
                            <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>Accuracy Delta</div>
                            <div style={{
                                fontSize: '20px', fontWeight: 700,
                                color: conv.regressed ? '#EF4444' : '#10B981',
                            }}>
                                {conv.accuracy_delta >= 0 ? '+' : ''}{conv.accuracy_delta.toFixed(4)}
                            </div>
                        </div>
                    </div>
                )}

                {/* Recommendation */}
                {conv?.recommendation && (
                    <div style={{
                        padding: '16px', borderRadius: '8px', border: '1px solid #374151',
                        backgroundColor: '#1F2937',
                    }}>
                        <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '6px' }}>Recommendation</div>
                        <div style={{ fontSize: '14px', color: '#D1D5DB', lineHeight: 1.5 }} data-testid="convergence-recommendation">
                            {conv.recommendation}
                        </div>
                    </div>
                )}

                {/* Accuracy History Chart */}
                {historyData.length > 0 && (
                    <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '16px', border: '1px solid #374151' }}>
                        <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '12px' }}>
                            Accuracy History
                        </h4>
                        <div style={{ width: '100%', height: 200 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={historyData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="epoch" tick={{ fontSize: 11, fill: '#9CA3AF' }} label={{ value: 'Epoch', position: 'insideBottom', offset: -5, fill: '#9CA3AF', fontSize: 11 }} />
                                    <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} domain={[0, 1]} />
                                    <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', color: '#F9FAFB' }} />
                                    <Line type="monotone" dataKey="accuracy" stroke="#10B981" strokeWidth={2} dot={{ r: 3 }} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {/* Accuracy History Table */}
                {historyData.length > 0 && (
                    <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '16px', border: '1px solid #374151' }}>
                        <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '12px' }}>
                            Epoch Log
                        </h4>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                            <thead>
                                <tr>
                                    <th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid #374151', color: '#9CA3AF' }}>Epoch</th>
                                    <th style={{ textAlign: 'right', padding: '6px 8px', borderBottom: '1px solid #374151', color: '#9CA3AF' }}>Accuracy</th>
                                    <th style={{ textAlign: 'right', padding: '6px 8px', borderBottom: '1px solid #374151', color: '#9CA3AF' }}>Timestamp</th>
                                </tr>
                            </thead>
                            <tbody>
                                {conv?.history?.map((h, idx) => (
                                    <tr key={idx}>
                                        <td style={{ padding: '6px 8px', borderBottom: '1px solid #1F2937', color: '#D1D5DB' }}>{h.epoch}</td>
                                        <td style={{ padding: '6px 8px', borderBottom: '1px solid #1F2937', color: '#D1D5DB', textAlign: 'right' }}>{h.accuracy.toFixed(4)}</td>
                                        <td style={{ padding: '6px 8px', borderBottom: '1px solid #1F2937', color: '#6B7280', textAlign: 'right', fontSize: '11px' }}>{h.timestamp}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="monitoring-panel" data-testid="monitoring-panel" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Tab Navigation */}
            <div style={{
                display: 'flex',
                gap: '2px',
                padding: '8px 12px',
                borderBottom: '1px solid #374151',
                backgroundColor: '#111827',
            }}>
                {TAB_CONFIG.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        data-testid={`monitoring-tab-${tab.id}`}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '6px 6px 0 0',
                            border: 'none',
                            backgroundColor: activeTab === tab.id ? '#1F2937' : 'transparent',
                            color: activeTab === tab.id ? '#60A5FA' : '#9CA3AF',
                            cursor: 'pointer',
                            fontWeight: activeTab === tab.id ? 600 : 400,
                            fontSize: '13px',
                            transition: 'all 0.2s',
                        }}
                    >
                        <span style={{ marginRight: '6px', opacity: 0.7 }}>{tab.icon}</span>
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Loading / Error States */}
            {loading && (
                <div style={{ padding: '24px', textAlign: 'center', color: '#9CA3AF' }} data-testid="monitoring-loading">
                    Loading monitoring data...
                </div>
            )}

            {error && (
                <div style={{ padding: '16px', margin: '12px', borderRadius: '8px', backgroundColor: '#7F1D1D', color: '#FCA5A5', fontSize: '13px' }} data-testid="monitoring-error">
                    {error}
                </div>
            )}

            {/* Tab Content */}
            {!loading && (
                <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
                    {activeTab === 'drift' && renderDriftTab()}
                    {activeTab === 'bias' && renderBiasTab()}
                    {activeTab === 'convergence' && renderConvergenceTab()}
                </div>
            )}
        </div>
    );
};

export default MonitoringPanel;
