/**
 * SpecMapTab — MAP pillar visualization.
 *
 * ReactFlow domain graph with:
 * - Actual policy counts per domain
 * - Board cross-domain edges
 * - Policy conflict indicators (dashed red edges)
 * - Node click drill-down showing policies in a side panel
 * - Edge hover highlighting
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, {
    Background,
    Controls,
    type Node,
    type Edge,
    type NodeTypes,
    type NodeMouseHandler,
    Handle,
    Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import type { QueryResponse, GovernanceDomain, GovernanceBoard, FederatedPolicyInfo, PolicyConflict } from '../../types/carf';
import { getGovernanceDomains, getGovernanceBoards, getFederatedPolicies, getConflicts } from '../../services/apiService';

// Domain color mapping
const DOMAIN_COLORS: Record<string, string> = {
    procurement: '#3B82F6',
    sustainability: '#10B981',
    security: '#EF4444',
    legal: '#8B5CF6',
    finance: '#F59E0B',
};

// Custom domain node component
const DomainNode: React.FC<{ data: { label: string; color: string; policyCount: number; dimmed?: boolean; hasConflict?: boolean } }> = ({ data }) => (
    <div style={{
        padding: '12px 20px',
        borderRadius: '12px',
        background: `${data.color}22`,
        border: `2px solid ${data.color}`,
        color: data.color,
        fontWeight: 600,
        fontSize: '13px',
        textAlign: 'center',
        minWidth: '120px',
        opacity: data.dimmed ? 0.35 : 1,
        transition: 'opacity 0.3s',
        cursor: 'pointer',
    }}>
        <Handle type="target" position={Position.Top} style={{ background: data.color }} />
        <div>{data.label}</div>
        <div style={{ fontSize: '10px', opacity: 0.7, marginTop: '4px' }}>
            {data.policyCount} policies
        </div>
        {data.hasConflict && (
            <div style={{ fontSize: '9px', color: '#EF4444', marginTop: '2px', fontWeight: 700 }}>
                ! CONFLICTS
            </div>
        )}
        <Handle type="source" position={Position.Bottom} style={{ background: data.color }} />
    </div>
);

const nodeTypes: NodeTypes = { domain: DomainNode };

interface SpecMapTabProps {
    lastResult: QueryResponse | null;
    selectedBoardId?: string | null;
}

interface DomainDetail {
    domain: GovernanceDomain;
    policies: FederatedPolicyInfo[];
    conflicts: PolicyConflict[];
}

const SpecMapTab: React.FC<SpecMapTabProps> = ({ lastResult, selectedBoardId }) => {
    const [domains, setDomains] = useState<GovernanceDomain[]>([]);
    const [boards, setBoards] = useState<GovernanceBoard[]>([]);
    const [policies, setPolicies] = useState<FederatedPolicyInfo[]>([]);
    const [conflicts, setConflicts] = useState<PolicyConflict[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDomain, setSelectedDomain] = useState<DomainDetail | null>(null);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const [d, b, p, c] = await Promise.all([
                    getGovernanceDomains(),
                    getGovernanceBoards(),
                    getFederatedPolicies(),
                    getConflicts(true).catch(() => [] as PolicyConflict[]),
                ]);
                if (!cancelled) {
                    setDomains(d);
                    setBoards(b);
                    setPolicies(p);
                    setConflicts(c);
                }
            } catch {
                // Governance may not be enabled
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, []);

    const selectedBoard = selectedBoardId
        ? boards.find(b => b.board_id === selectedBoardId)
        : null;

    // Compute policy count and conflict status per domain
    const policyCountByDomain = useMemo(() => {
        const counts: Record<string, number> = {};
        for (const policy of policies) {
            counts[policy.domain_id] = (counts[policy.domain_id] || 0) + 1;
        }
        return counts;
    }, [policies]);

    const conflictDomains = useMemo(() => {
        const domainIds = new Set<string>();
        for (const c of conflicts) {
            domainIds.add(c.policy_a_domain);
            domainIds.add(c.policy_b_domain);
        }
        return domainIds;
    }, [conflicts]);

    // Cross-domain conflict pairs for edges
    const conflictPairs = useMemo(() => {
        const pairs: { a: string; b: string; count: number }[] = [];
        const pairMap = new Map<string, number>();
        for (const c of conflicts) {
            if (c.policy_a_domain !== c.policy_b_domain) {
                const key = [c.policy_a_domain, c.policy_b_domain].sort().join('::');
                pairMap.set(key, (pairMap.get(key) || 0) + 1);
            }
        }
        for (const [key, count] of pairMap) {
            const [a, b] = key.split('::');
            pairs.push({ a, b, count });
        }
        return pairs;
    }, [conflicts]);

    const { nodes, edges } = useMemo(() => {
        const n: Node[] = [];
        const e: Edge[] = [];

        // Create domain nodes in a circle layout
        const cx = 300, cy = 250, r = 180;
        domains.forEach((domain, i) => {
            const angle = (i / Math.max(domains.length, 1)) * 2 * Math.PI - Math.PI / 2;
            const inBoard = selectedBoard
                ? selectedBoard.domain_ids.includes(domain.domain_id)
                : true;
            n.push({
                id: domain.domain_id,
                type: 'domain',
                position: { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) },
                data: {
                    label: domain.display_name,
                    color: DOMAIN_COLORS[domain.domain_id] || domain.color || '#6B7280',
                    policyCount: policyCountByDomain[domain.domain_id] || 0,
                    dimmed: selectedBoard ? !inBoard : false,
                    hasConflict: conflictDomains.has(domain.domain_id),
                },
            });
        });

        // Build edges from board cross-domain relationships
        const domainIdSet = new Set(domains.map(d => d.domain_id));
        let edgeIdx = 0;
        const edgeSet = new Set<string>(); // deduplicate edges

        for (const board of boards) {
            const boardDomains = board.domain_ids.filter(id => domainIdSet.has(id));
            for (let i = 0; i < boardDomains.length; i++) {
                for (let j = i + 1; j < boardDomains.length; j++) {
                    const key = [boardDomains[i], boardDomains[j]].sort().join('::');
                    if (!edgeSet.has(key)) {
                        edgeSet.add(key);
                        e.push({
                            id: `e-${edgeIdx++}`,
                            source: boardDomains[i],
                            target: boardDomains[j],
                            label: board.name,
                            animated: true,
                            style: { strokeWidth: 2, stroke: '#60A5FA' },
                            labelStyle: { fontSize: '10px', fill: '#9CA3AF' },
                        });
                    }
                }
            }
        }

        // Add conflict edges (dashed red)
        for (const pair of conflictPairs) {
            if (domainIdSet.has(pair.a) && domainIdSet.has(pair.b)) {
                const key = [pair.a, pair.b].sort().join('::conflict');
                if (!edgeSet.has(key)) {
                    edgeSet.add(key);
                    e.push({
                        id: `conflict-${edgeIdx++}`,
                        source: pair.a,
                        target: pair.b,
                        label: `${pair.count} conflict${pair.count > 1 ? 's' : ''}`,
                        animated: false,
                        style: { strokeWidth: 2, stroke: '#EF4444', strokeDasharray: '5 3' },
                        labelStyle: { fontSize: '10px', fill: '#EF4444', fontWeight: 600 },
                    });
                }
            }
        }

        return { nodes: n, edges: e };
    }, [domains, boards, policies, policyCountByDomain, conflictDomains, conflictPairs, selectedBoard]);

    const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
        const domain = domains.find(d => d.domain_id === node.id);
        if (!domain) return;
        const domainPolicies = policies.filter(p => p.domain_id === domain.domain_id);
        const domainConflicts = conflicts.filter(
            c => c.policy_a_domain === domain.domain_id || c.policy_b_domain === domain.domain_id
        );
        setSelectedDomain({ domain, policies: domainPolicies, conflicts: domainConflicts });
    }, [domains, policies, conflicts]);

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px', color: '#9CA3AF' }}>
                Loading governance domains...
            </div>
        );
    }

    if (domains.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>MAP</div>
                <p style={{ fontSize: '14px' }}>
                    No governance domains configured. Enable <code>GOVERNANCE_ENABLED=true</code> and add
                    domain policies to <code>config/federated_policies/</code>.
                </p>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {selectedBoard && (
                <div style={{
                    padding: '6px 12px', backgroundColor: '#1F2937', borderRadius: '6px',
                    border: '1px solid #374151', fontSize: '12px', color: '#9CA3AF',
                }}>
                    Board: <span style={{ color: '#60A5FA', fontWeight: 600 }}>{selectedBoard.name}</span>
                    <span style={{ marginLeft: '8px', fontSize: '10px' }}>
                        (highlighting {selectedBoard.domain_ids.length} domains)
                    </span>
                </div>
            )}

            {/* Legend */}
            <div style={{
                display: 'flex', gap: '14px', alignItems: 'center', fontSize: '11px', color: '#94A3B8',
                backgroundColor: '#0F172A', border: '1px solid #1E293B', borderRadius: '6px', padding: '6px 10px',
            }}>
                <span style={{ fontWeight: 600 }}>Legend:</span>
                <span style={{ color: '#60A5FA' }}>--- Board link</span>
                <span style={{ color: '#EF4444' }}>- - Conflict</span>
                <span style={{ marginLeft: 'auto', fontSize: '10px', color: '#6B7280' }}>Click a domain for details</span>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
                <div style={{
                    flex: selectedDomain ? '1 1 70%' : '1 1 100%',
                    height: '550px',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    transition: 'flex 0.3s',
                }}>
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        nodeTypes={nodeTypes}
                        onNodeClick={onNodeClick}
                        onPaneClick={() => setSelectedDomain(null)}
                        fitView
                        style={{ backgroundColor: '#0D1117' }}
                    >
                        <Background color="#1F2937" gap={20} />
                        <Controls />
                    </ReactFlow>
                </div>

                {/* Drill-down details panel */}
                {selectedDomain && (
                    <div style={{
                        flex: '0 0 30%',
                        maxWidth: '320px',
                        height: '550px',
                        overflowY: 'auto',
                        borderRadius: '8px',
                        border: '1px solid #374151',
                        backgroundColor: '#111827',
                        padding: '14px',
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                            <div style={{
                                fontSize: '14px', fontWeight: 700,
                                color: DOMAIN_COLORS[selectedDomain.domain.domain_id] || '#E2E8F0',
                            }}>
                                {selectedDomain.domain.display_name}
                            </div>
                            <button
                                onClick={() => setSelectedDomain(null)}
                                style={{ background: 'none', border: 'none', color: '#6B7280', cursor: 'pointer', fontSize: '16px', padding: '2px 6px' }}
                            >
                                x
                            </button>
                        </div>

                        {selectedDomain.domain.description && (
                            <div style={{ fontSize: '11px', color: '#94A3B8', marginBottom: '10px' }}>
                                {selectedDomain.domain.description}
                            </div>
                        )}

                        {/* Policies */}
                        <div style={{ fontSize: '11px', color: '#93C5FD', fontWeight: 600, marginBottom: '6px' }}>
                            Policies ({selectedDomain.policies.length})
                        </div>
                        {selectedDomain.policies.length === 0 ? (
                            <div style={{ fontSize: '11px', color: '#6B7280', marginBottom: '12px' }}>No policies defined</div>
                        ) : (
                            <div style={{ marginBottom: '12px' }}>
                                {selectedDomain.policies.map(p => (
                                    <div key={p.policy_id} style={{
                                        padding: '6px 8px',
                                        borderRadius: '4px',
                                        border: '1px solid #1E293B',
                                        marginBottom: '4px',
                                        fontSize: '11px',
                                    }}>
                                        <div style={{ color: '#E2E8F0', fontWeight: 600 }}>{p.name}</div>
                                        <div style={{ color: '#64748B', fontSize: '10px', marginTop: '2px' }}>
                                            {p.namespace} | priority {p.priority} | {p.rules.length} rules |
                                            <span style={{ color: p.is_active ? '#10B981' : '#EF4444' }}>
                                                {p.is_active ? ' active' : ' inactive'}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Conflicts */}
                        {selectedDomain.conflicts.length > 0 && (
                            <>
                                <div style={{ fontSize: '11px', color: '#FCA5A5', fontWeight: 600, marginBottom: '6px' }}>
                                    Conflicts ({selectedDomain.conflicts.length})
                                </div>
                                {selectedDomain.conflicts.map(c => (
                                    <div key={c.conflict_id} style={{
                                        padding: '6px 8px',
                                        borderRadius: '4px',
                                        border: '1px solid #7F1D1D',
                                        backgroundColor: '#450A0A33',
                                        marginBottom: '4px',
                                        fontSize: '11px',
                                    }}>
                                        <div style={{ color: '#FCA5A5', fontWeight: 600 }}>
                                            {c.policy_a_name} vs {c.policy_b_name}
                                        </div>
                                        <div style={{ color: '#94A3B8', fontSize: '10px', marginTop: '2px' }}>
                                            {c.severity} | {c.conflict_type}
                                        </div>
                                        {c.description && (
                                            <div style={{ color: '#6B7280', fontSize: '10px', marginTop: '2px' }}>
                                                {c.description}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default SpecMapTab;
