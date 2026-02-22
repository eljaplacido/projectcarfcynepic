/**
 * GovernanceBoardTab — Board configurator UI.
 *
 * Header bar with create/template/seed actions, board sidebar,
 * board detail with domains/policies/compliance/members sub-sections,
 * and export bar.
 */

import React, { useEffect, useState, useCallback } from 'react';
import type {
    GovernanceBoard,
    GovernanceDomain,
    FederatedPolicyInfo,
    BoardTemplate,
    ComplianceScore,
} from '../../types/carf';
import {
    getGovernanceBoards,
    createGovernanceBoard,
    getBoardTemplates,
    createBoardFromTemplate,
    deleteGovernanceBoard,
    getBoardCompliance,
    getGovernanceDomains,
    getFederatedPolicies,
    exportGovernanceSpec,
    seedGovernanceDemoData,
} from '../../services/apiService';

const DOMAIN_COLORS: Record<string, string> = {
    procurement: '#3B82F6',
    sustainability: '#10B981',
    security: '#EF4444',
    legal: '#8B5CF6',
    finance: '#F59E0B',
};

interface GovernanceBoardTabProps {
    onBoardSelect?: (boardId: string | null) => void;
    selectedBoardId?: string | null;
}

const GovernanceBoardTab: React.FC<GovernanceBoardTabProps> = ({
    onBoardSelect,
    selectedBoardId: externalSelectedId,
}) => {
    const [boards, setBoards] = useState<GovernanceBoard[]>([]);
    const [templates, setTemplates] = useState<BoardTemplate[]>([]);
    const [domains, setDomains] = useState<GovernanceDomain[]>([]);
    const [policies, setPolicies] = useState<FederatedPolicyInfo[]>([]);
    const [selectedBoardId, setSelectedBoardId] = useState<string | null>(externalSelectedId || null);
    const [compliance, setCompliance] = useState<ComplianceScore[]>([]);
    const [loading, setLoading] = useState(true);
    const [showTemplateDropdown, setShowTemplateDropdown] = useState(false);
    const [exporting, setExporting] = useState<string | null>(null);

    const loadData = useCallback(async () => {
        try {
            const [b, t, d, p] = await Promise.all([
                getGovernanceBoards(),
                getBoardTemplates(),
                getGovernanceDomains(),
                getFederatedPolicies(),
            ]);
            setBoards(b);
            setTemplates(t);
            setDomains(d);
            setPolicies(p);
        } catch {
            // Governance may not be enabled
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    // Load compliance when board selected
    useEffect(() => {
        if (!selectedBoardId) {
            setCompliance([]);
            return;
        }
        (async () => {
            try {
                const scores = await getBoardCompliance(selectedBoardId);
                setCompliance(scores);
            } catch {
                setCompliance([]);
            }
        })();
    }, [selectedBoardId]);

    const selectedBoard = boards.find(b => b.board_id === selectedBoardId);

    const handleSelectBoard = (boardId: string | null) => {
        setSelectedBoardId(boardId);
        onBoardSelect?.(boardId);
    };

    const handleNewBoard = async () => {
        const name = prompt('Board name:');
        if (!name) return;
        try {
            const board = await createGovernanceBoard({ name });
            setBoards(prev => [...prev, board]);
            handleSelectBoard(board.board_id);
        } catch (err) {
            console.error('Failed to create board:', err);
        }
    };

    const handleFromTemplate = async (templateId: string) => {
        setShowTemplateDropdown(false);
        try {
            const board = await createBoardFromTemplate(templateId);
            await loadData();
            handleSelectBoard(board.board_id);
        } catch (err) {
            console.error('Failed to create from template:', err);
        }
    };

    const handleSeedDemo = async () => {
        const templateId = selectedBoard?.template_id || 'scope_emissions';
        try {
            await seedGovernanceDemoData(templateId);
            await loadData();
        } catch (err) {
            console.error('Failed to seed demo data:', err);
        }
    };

    const handleDeleteBoard = async (boardId: string) => {
        if (!confirm('Delete this board?')) return;
        try {
            await deleteGovernanceBoard(boardId);
            setBoards(prev => prev.filter(b => b.board_id !== boardId));
            if (selectedBoardId === boardId) handleSelectBoard(null);
        } catch (err) {
            console.error('Failed to delete board:', err);
        }
    };

    const handleExport = async (format: 'json_ld' | 'yaml' | 'csl') => {
        if (!selectedBoardId) return;
        setExporting(format);
        try {
            const data = await exportGovernanceSpec(selectedBoardId, format);
            const content = format === 'yaml' ? (data as Record<string, unknown>).content as string : JSON.stringify(data, null, 2);
            const blob = new Blob([content], { type: format === 'yaml' ? 'text/yaml' : 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `governance_${selectedBoard?.name || 'board'}_${format}.${format === 'yaml' ? 'yaml' : 'json'}`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Export failed:', err);
        } finally {
            setExporting(null);
        }
    };

    const boardDomains = selectedBoard
        ? domains.filter(d => selectedBoard.domain_ids.includes(d.domain_id))
        : [];

    const boardPolicies = selectedBoard
        ? policies.filter(p => selectedBoard.policy_namespaces.includes(p.namespace))
        : [];

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', color: '#9CA3AF' }}>
                Loading governance boards...
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px' }}>
            {/* Header Bar */}
            <div style={{
                display: 'flex', gap: '8px', alignItems: 'center',
                padding: '8px 12px', backgroundColor: '#1F2937',
                borderRadius: '8px', border: '1px solid #374151',
            }}>
                <button
                    onClick={handleNewBoard}
                    style={{
                        padding: '6px 14px', borderRadius: '6px', border: '1px solid #3B82F6',
                        backgroundColor: '#3B82F622', color: '#60A5FA', cursor: 'pointer',
                        fontSize: '12px', fontWeight: 600,
                    }}
                >
                    + New Board
                </button>

                <div style={{ position: 'relative' }}>
                    <button
                        onClick={() => setShowTemplateDropdown(!showTemplateDropdown)}
                        style={{
                            padding: '6px 14px', borderRadius: '6px', border: '1px solid #10B981',
                            backgroundColor: '#10B98122', color: '#10B981', cursor: 'pointer',
                            fontSize: '12px', fontWeight: 600,
                        }}
                    >
                        From Template
                    </button>
                    {showTemplateDropdown && (
                        <div style={{
                            position: 'absolute', top: '100%', left: 0, zIndex: 50,
                            marginTop: '4px', backgroundColor: '#1F2937',
                            border: '1px solid #374151', borderRadius: '8px',
                            minWidth: '280px', overflow: 'hidden',
                        }}>
                            {templates.map(t => (
                                <button
                                    key={t.template_id}
                                    onClick={() => handleFromTemplate(t.template_id)}
                                    style={{
                                        width: '100%', padding: '10px 12px', border: 'none',
                                        backgroundColor: 'transparent', color: '#D1D5DB',
                                        cursor: 'pointer', textAlign: 'left', fontSize: '12px',
                                        borderBottom: '1px solid #374151',
                                    }}
                                    onMouseOver={e => (e.currentTarget.style.backgroundColor = '#374151')}
                                    onMouseOut={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                                >
                                    <div style={{ fontWeight: 600 }}>{t.name}</div>
                                    <div style={{ fontSize: '10px', color: '#9CA3AF', marginTop: '2px' }}>
                                        {t.description}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                <button
                    onClick={handleSeedDemo}
                    style={{
                        padding: '6px 14px', borderRadius: '6px', border: '1px solid #F59E0B',
                        backgroundColor: '#F59E0B22', color: '#F59E0B', cursor: 'pointer',
                        fontSize: '12px', fontWeight: 600,
                    }}
                >
                    Seed Demo Data
                </button>

                <div style={{ flex: 1 }} />

                <span style={{ fontSize: '11px', color: '#6B7280' }}>
                    {boards.length} board{boards.length !== 1 ? 's' : ''}
                </span>
            </div>

            {/* Main Content */}
            <div style={{ flex: 1, display: 'flex', gap: '12px', overflow: 'hidden' }}>
                {/* Board Sidebar */}
                <div style={{
                    width: '220px', flexShrink: 0, backgroundColor: '#1F2937',
                    borderRadius: '8px', padding: '12px', border: '1px solid #374151',
                    overflowY: 'auto',
                }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#9CA3AF', marginBottom: '8px', textTransform: 'uppercase' }}>
                        Boards
                    </div>
                    {boards.length === 0 ? (
                        <div style={{ fontSize: '11px', color: '#6B7280', padding: '8px' }}>
                            No boards yet. Create one or use a template.
                        </div>
                    ) : (
                        boards.map(board => (
                            <button
                                key={board.board_id}
                                onClick={() => handleSelectBoard(board.board_id)}
                                style={{
                                    width: '100%', padding: '8px', borderRadius: '6px', border: 'none',
                                    backgroundColor: selectedBoardId === board.board_id ? '#374151' : 'transparent',
                                    color: selectedBoardId === board.board_id ? '#E5E7EB' : '#9CA3AF',
                                    cursor: 'pointer', textAlign: 'left', marginBottom: '4px', fontSize: '12px',
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <span style={{
                                        width: '8px', height: '8px', borderRadius: '50%',
                                        backgroundColor: board.is_active ? '#10B981' : '#6B7280',
                                        flexShrink: 0,
                                    }} />
                                    <span style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {board.name}
                                    </span>
                                </div>
                                <div style={{ fontSize: '10px', opacity: 0.7, marginTop: '2px', paddingLeft: '14px' }}>
                                    {board.domain_ids.length} domains | {board.policy_namespaces.length} policies
                                </div>
                            </button>
                        ))
                    )}
                </div>

                {/* Board Detail */}
                <div style={{ flex: 1, overflowY: 'auto' }}>
                    {selectedBoard ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {/* Board Header */}
                            <div style={{
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                padding: '12px', backgroundColor: '#1F2937', borderRadius: '8px',
                                border: '1px solid #374151',
                            }}>
                                <div>
                                    <div style={{ fontSize: '16px', fontWeight: 700, color: '#E5E7EB' }}>
                                        {selectedBoard.name}
                                    </div>
                                    <div style={{ fontSize: '12px', color: '#9CA3AF', marginTop: '2px' }}>
                                        {selectedBoard.description}
                                    </div>
                                    {selectedBoard.tags.length > 0 && (
                                        <div style={{ display: 'flex', gap: '4px', marginTop: '6px', flexWrap: 'wrap' }}>
                                            {selectedBoard.tags.map(tag => (
                                                <span key={tag} style={{
                                                    fontSize: '10px', padding: '2px 6px', borderRadius: '4px',
                                                    backgroundColor: '#3B82F622', color: '#60A5FA',
                                                }}>
                                                    {tag}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                <button
                                    onClick={() => handleDeleteBoard(selectedBoard.board_id)}
                                    style={{
                                        padding: '4px 10px', borderRadius: '4px', border: '1px solid #EF4444',
                                        backgroundColor: 'transparent', color: '#EF4444', cursor: 'pointer',
                                        fontSize: '11px',
                                    }}
                                >
                                    Delete
                                </button>
                            </div>

                            {/* Domains Section */}
                            <div style={{
                                padding: '12px', backgroundColor: '#1F2937', borderRadius: '8px',
                                border: '1px solid #374151',
                            }}>
                                <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '8px' }}>
                                    Domains ({boardDomains.length})
                                </div>
                                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                    {boardDomains.map(domain => {
                                        const color = DOMAIN_COLORS[domain.domain_id] || domain.color;
                                        return (
                                            <div key={domain.domain_id} style={{
                                                padding: '8px 12px', borderRadius: '6px',
                                                backgroundColor: `${color}15`,
                                                border: `1px solid ${color}55`,
                                                borderLeft: `3px solid ${color}`,
                                            }}>
                                                <div style={{ fontWeight: 600, color, fontSize: '12px' }}>
                                                    {domain.display_name}
                                                </div>
                                                <div style={{ fontSize: '10px', color: '#9CA3AF', marginTop: '2px' }}>
                                                    {domain.description}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Policies Section */}
                            <div style={{
                                padding: '12px', backgroundColor: '#1F2937', borderRadius: '8px',
                                border: '1px solid #374151',
                            }}>
                                <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '8px' }}>
                                    Policies ({boardPolicies.length})
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '8px' }}>
                                    {boardPolicies.map(policy => {
                                        const color = DOMAIN_COLORS[policy.domain_id] || '#6B7280';
                                        return (
                                            <div key={policy.namespace} style={{
                                                padding: '10px', borderRadius: '6px',
                                                backgroundColor: '#111827',
                                                border: `1px solid ${color}33`,
                                                borderLeft: `3px solid ${color}`,
                                            }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <span style={{ fontWeight: 600, color: '#E5E7EB', fontSize: '12px' }}>
                                                        {policy.name}
                                                    </span>
                                                    <span style={{
                                                        fontSize: '9px', padding: '2px 5px', borderRadius: '3px',
                                                        backgroundColor: policy.is_active ? '#10B98133' : '#EF444433',
                                                        color: policy.is_active ? '#10B981' : '#EF4444',
                                                    }}>
                                                        {policy.is_active ? 'Active' : 'Off'}
                                                    </span>
                                                </div>
                                                <div style={{ fontSize: '10px', color: '#6B7280', marginTop: '4px' }}>
                                                    {policy.rules.length} rules | P{policy.priority}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Compliance Section */}
                            <div style={{
                                padding: '12px', backgroundColor: '#1F2937', borderRadius: '8px',
                                border: '1px solid #374151',
                            }}>
                                <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '8px' }}>
                                    Compliance ({compliance.length} frameworks)
                                </div>
                                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                                    {compliance.map(score => {
                                        const pct = Math.round(score.overall_score * 100);
                                        const config = selectedBoard.compliance_configs.find(
                                            c => c.framework === score.framework
                                        );
                                        const targetPct = config ? Math.round(config.target_score * 100) : null;
                                        const color = pct >= 80 ? '#10B981' : pct >= 60 ? '#F59E0B' : '#EF4444';
                                        return (
                                            <div key={score.framework} style={{
                                                padding: '12px', borderRadius: '8px',
                                                backgroundColor: '#111827',
                                                border: `1px solid ${color}55`,
                                                minWidth: '150px', textAlign: 'center',
                                            }}>
                                                <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: '4px' }}>
                                                    {score.framework.replace('_', ' ')}
                                                </div>
                                                <div style={{ fontSize: '28px', fontWeight: 700, color }}>
                                                    {pct}%
                                                </div>
                                                {targetPct && (
                                                    <div style={{ fontSize: '10px', color: '#6B7280', marginTop: '2px' }}>
                                                        Target: {targetPct}%
                                                    </div>
                                                )}
                                                <div style={{ fontSize: '10px', color: '#6B7280', marginTop: '2px' }}>
                                                    {score.articles.length} articles | {score.gaps.length} gaps
                                                </div>
                                            </div>
                                        );
                                    })}
                                    {compliance.length === 0 && (
                                        <div style={{ fontSize: '11px', color: '#6B7280', padding: '8px' }}>
                                            No compliance frameworks configured for this board.
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Members Section */}
                            {selectedBoard.members.length > 0 && (
                                <div style={{
                                    padding: '12px', backgroundColor: '#1F2937', borderRadius: '8px',
                                    border: '1px solid #374151',
                                }}>
                                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '8px' }}>
                                        Members ({selectedBoard.members.length})
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                        {selectedBoard.members.map(member => (
                                            <div key={member.user_id} style={{
                                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                                padding: '6px 8px', borderRadius: '4px', backgroundColor: '#111827',
                                                fontSize: '12px',
                                            }}>
                                                <span style={{ color: '#D1D5DB' }}>{member.name}</span>
                                                <span style={{
                                                    fontSize: '10px', padding: '2px 6px', borderRadius: '3px',
                                                    backgroundColor: '#3B82F622', color: '#60A5FA',
                                                }}>
                                                    {member.role}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div style={{
                            display: 'flex', flexDirection: 'column', alignItems: 'center',
                            justifyContent: 'center', height: '100%', color: '#6B7280',
                        }}>
                            <div style={{ fontSize: '24px', marginBottom: '8px' }}>BOARDS</div>
                            <p style={{ fontSize: '13px', textAlign: 'center', maxWidth: '400px' }}>
                                Select a board from the sidebar or create one using the buttons above.
                                Boards group domains, policies, and compliance frameworks into governance bundles.
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* Export Bar */}
            {selectedBoard && (
                <div style={{
                    display: 'flex', gap: '8px', padding: '8px 12px',
                    backgroundColor: '#1F2937', borderRadius: '8px', border: '1px solid #374151',
                    alignItems: 'center',
                }}>
                    <span style={{ fontSize: '11px', color: '#9CA3AF', fontWeight: 600 }}>Export:</span>
                    {(['json_ld', 'yaml', 'csl'] as const).map(format => (
                        <button
                            key={format}
                            onClick={() => handleExport(format)}
                            disabled={!!exporting}
                            style={{
                                padding: '4px 12px', borderRadius: '4px',
                                border: '1px solid #374151',
                                backgroundColor: exporting === format ? '#374151' : 'transparent',
                                color: '#D1D5DB', cursor: exporting ? 'wait' : 'pointer',
                                fontSize: '11px',
                            }}
                        >
                            {exporting === format ? 'Exporting...' : format.replace('_', '-').toUpperCase()}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

export default GovernanceBoardTab;
