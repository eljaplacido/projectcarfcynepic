/**
 * ComplianceAuditTab — AUDIT pillar visualization.
 *
 * Board selector, framework selector, score gauge, article accordion,
 * gap panel, audit timeline. Board-aware with target score indicators.
 */

import React, { useEffect, useState, useCallback } from 'react';
import type { ComplianceScore, GovernanceAuditEntry, GovernanceBoard } from '../../types/carf';
import {
    getComplianceScore,
    getGovernanceAudit,
    getGovernanceBoards,
    getBoardCompliance,
} from '../../services/apiService';

const FRAMEWORKS = [
    { id: 'eu_ai_act', label: 'EU AI Act', color: '#3B82F6' },
    { id: 'csrd', label: 'CSRD', color: '#10B981' },
    { id: 'gdpr', label: 'GDPR', color: '#8B5CF6' },
    { id: 'iso_27001', label: 'ISO 27001', color: '#F59E0B' },
];

const STATUS_COLORS: Record<string, string> = {
    compliant: '#10B981',
    partial: '#F59E0B',
    non_compliant: '#EF4444',
    unknown: '#6B7280',
};

// Simple gauge component with optional target score indicator
const ScoreGauge: React.FC<{ score: number; color: string; targetScore?: number }> = ({ score, color, targetScore }) => {
    const pct = Math.round(score * 100);
    const targetPct = targetScore ? Math.round(targetScore * 100) : null;
    return (
        <div style={{ textAlign: 'center', padding: '16px' }}>
            <div style={{
                width: '120px', height: '120px', borderRadius: '50%',
                border: '6px solid #374151', position: 'relative',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                background: `conic-gradient(${color} ${pct}%, #374151 ${pct}%)`,
            }}>
                <div style={{
                    width: '96px', height: '96px', borderRadius: '50%',
                    backgroundColor: '#111827', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                    flexDirection: 'column',
                }}>
                    <span style={{ fontSize: '28px', fontWeight: 700, color }}>{pct}%</span>
                    <span style={{ fontSize: '10px', color: '#9CA3AF' }}>Compliant</span>
                </div>
            </div>
            {targetPct !== null && (
                <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '4px' }}>
                    Target: <span style={{ color: pct >= targetPct ? '#10B981' : '#F59E0B', fontWeight: 600 }}>
                        {targetPct}%
                    </span>
                </div>
            )}
        </div>
    );
};

interface ComplianceAuditTabProps {
    selectedBoardId?: string | null;
}

const ComplianceAuditTab: React.FC<ComplianceAuditTabProps> = ({ selectedBoardId }) => {
    const [selectedFramework, setSelectedFramework] = useState('eu_ai_act');
    const [compliance, setCompliance] = useState<ComplianceScore | null>(null);
    const [auditEntries, setAuditEntries] = useState<GovernanceAuditEntry[]>([]);
    const [expandedArticle, setExpandedArticle] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [boards, setBoards] = useState<GovernanceBoard[]>([]);
    const [localBoardId, setLocalBoardId] = useState<string | null>(selectedBoardId || null);

    // Load boards for selector
    useEffect(() => {
        getGovernanceBoards().then(setBoards).catch(() => {});
    }, []);

    // Sync external board selection
    useEffect(() => {
        if (selectedBoardId !== undefined) {
            setLocalBoardId(selectedBoardId || null);
        }
    }, [selectedBoardId]);

    const loadData = useCallback(async (framework: string) => {
        setLoading(true);
        try {
            if (localBoardId) {
                // Board-aware: get all compliance scores for the board
                const scores = await getBoardCompliance(localBoardId);
                const matchingScore = scores.find(s => s.framework === framework);
                setCompliance(matchingScore || null);
            } else {
                const compData = await getComplianceScore(framework);
                setCompliance(compData);
            }
            const auditData = await getGovernanceAudit(50);
            setAuditEntries(auditData);
        } catch {
            setCompliance(null);
        } finally {
            setLoading(false);
        }
    }, [localBoardId]);

    useEffect(() => {
        loadData(selectedFramework);
    }, [selectedFramework, loadData]);

    const frameworkConfig = FRAMEWORKS.find(f => f.id === selectedFramework) || FRAMEWORKS[0];
    const selectedBoard = boards.find(b => b.board_id === localBoardId);
    const targetScore = selectedBoard?.compliance_configs?.find(
        c => c.framework === selectedFramework
    )?.target_score;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Board Selector */}
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', color: '#9CA3AF' }}>Board:</span>
                <select
                    value={localBoardId || ''}
                    onChange={e => setLocalBoardId(e.target.value || null)}
                    style={{
                        padding: '6px 10px', borderRadius: '6px',
                        border: '1px solid #374151', backgroundColor: '#1F2937',
                        color: '#E5E7EB', fontSize: '12px',
                    }}
                >
                    <option value="">All (no board filter)</option>
                    {boards.map(b => (
                        <option key={b.board_id} value={b.board_id}>{b.name}</option>
                    ))}
                </select>
            </div>

            {/* Framework Selector */}
            <div style={{ display: 'flex', gap: '8px' }}>
                {FRAMEWORKS.map(fw => (
                    <button
                        key={fw.id}
                        onClick={() => setSelectedFramework(fw.id)}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '6px',
                            border: `1px solid ${selectedFramework === fw.id ? fw.color : '#374151'}`,
                            backgroundColor: selectedFramework === fw.id ? `${fw.color}22` : 'transparent',
                            color: selectedFramework === fw.id ? fw.color : '#9CA3AF',
                            cursor: 'pointer',
                            fontSize: '12px',
                            fontWeight: selectedFramework === fw.id ? 600 : 400,
                        }}
                    >
                        {fw.label}
                    </button>
                ))}
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#9CA3AF' }}>
                    Loading compliance assessment...
                </div>
            ) : compliance ? (
                <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '16px' }}>
                    {/* Left: Score + Gaps */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '16px', border: '1px solid #374151' }}>
                            <ScoreGauge
                                score={compliance.overall_score}
                                color={frameworkConfig.color}
                                targetScore={targetScore}
                            />
                            <div style={{ textAlign: 'center', fontSize: '14px', fontWeight: 600, color: '#D1D5DB' }}>
                                {frameworkConfig.label}
                            </div>
                        </div>

                        {compliance.gaps.length > 0 && (
                            <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '12px', border: '1px solid #374151' }}>
                                <div style={{ fontSize: '12px', fontWeight: 600, color: '#EF4444', marginBottom: '8px' }}>
                                    Gaps ({compliance.gaps.length})
                                </div>
                                {compliance.gaps.map((gap, i) => (
                                    <div key={i} style={{
                                        fontSize: '11px', color: '#D1D5DB', padding: '6px 8px',
                                        borderLeft: '2px solid #EF4444', marginBottom: '4px',
                                        backgroundColor: '#EF444411',
                                    }}>
                                        {gap}
                                    </div>
                                ))}
                            </div>
                        )}

                        {compliance.recommendations.length > 0 && (
                            <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '12px', border: '1px solid #374151' }}>
                                <div style={{ fontSize: '12px', fontWeight: 600, color: '#10B981', marginBottom: '8px' }}>
                                    Recommendations
                                </div>
                                {compliance.recommendations.map((rec, i) => (
                                    <div key={i} style={{
                                        fontSize: '11px', color: '#D1D5DB', padding: '6px 8px',
                                        borderLeft: '2px solid #10B981', marginBottom: '4px',
                                        backgroundColor: '#10B98111',
                                    }}>
                                        {rec}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Right: Article Accordion + Timeline */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '12px', border: '1px solid #374151' }}>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '8px' }}>
                                Articles ({compliance.articles.length})
                            </div>
                            {compliance.articles.map(article => (
                                <div key={article.article_id} style={{
                                    marginBottom: '4px',
                                    borderRadius: '6px',
                                    overflow: 'hidden',
                                    border: '1px solid #374151',
                                }}>
                                    <button
                                        onClick={() => setExpandedArticle(
                                            expandedArticle === article.article_id ? null : article.article_id
                                        )}
                                        style={{
                                            width: '100%', padding: '8px 12px',
                                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                            backgroundColor: '#111827', border: 'none',
                                            color: '#D1D5DB', cursor: 'pointer', fontSize: '12px',
                                        }}
                                    >
                                        <span>
                                            <strong>{article.article_id}</strong> — {article.title}
                                        </span>
                                        <span style={{
                                            padding: '2px 8px', borderRadius: '4px', fontSize: '10px',
                                            backgroundColor: `${STATUS_COLORS[article.status]}22`,
                                            color: STATUS_COLORS[article.status],
                                            fontWeight: 600,
                                        }}>
                                            {Math.round(article.score * 100)}%
                                        </span>
                                    </button>
                                    {expandedArticle === article.article_id && (
                                        <div style={{ padding: '8px 12px', backgroundColor: '#0D1117' }}>
                                            {article.evidence.length > 0 && (
                                                <div style={{ marginBottom: '6px' }}>
                                                    <div style={{ fontSize: '10px', color: '#10B981', fontWeight: 600 }}>Evidence:</div>
                                                    {article.evidence.map((e, i) => (
                                                        <div key={i} style={{ fontSize: '11px', color: '#9CA3AF', paddingLeft: '8px' }}>- {e}</div>
                                                    ))}
                                                </div>
                                            )}
                                            {article.gaps.length > 0 && (
                                                <div>
                                                    <div style={{ fontSize: '10px', color: '#EF4444', fontWeight: 600 }}>Gaps:</div>
                                                    {article.gaps.map((g, i) => (
                                                        <div key={i} style={{ fontSize: '11px', color: '#9CA3AF', paddingLeft: '8px' }}>- {g}</div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>

                        {auditEntries.length > 0 && (
                            <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '12px', border: '1px solid #374151' }}>
                                <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '8px' }}>
                                    Audit Timeline (Latest {Math.min(auditEntries.length, 10)})
                                </div>
                                <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                    {auditEntries.slice(0, 10).map(entry => (
                                        <div key={entry.entry_id} style={{
                                            display: 'flex', gap: '8px', padding: '6px 0',
                                            borderBottom: '1px solid #374151', fontSize: '11px',
                                        }}>
                                            <span style={{ color: '#6B7280', minWidth: '60px' }}>
                                                {new Date(entry.timestamp).toLocaleTimeString()}
                                            </span>
                                            <span style={{
                                                padding: '1px 6px', borderRadius: '3px',
                                                backgroundColor: '#3B82F622', color: '#60A5FA', fontSize: '10px',
                                            }}>
                                                {entry.event_type}
                                            </span>
                                            <span style={{ color: '#9CA3AF', flex: 1 }}>
                                                {entry.affected_domains.join(', ')}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
                    <p>Enable <code>GOVERNANCE_ENABLED=true</code> to view compliance assessments.</p>
                </div>
            )}
        </div>
    );
};

export default ComplianceAuditTab;
