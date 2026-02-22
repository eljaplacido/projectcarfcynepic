/**
 * SpecMapTab — MAP pillar visualization.
 *
 * ReactFlow triple graph: domain nodes + entity nodes + predicate edges.
 * Board-aware: highlights board domains when a board is selected.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, {
    Background,
    Controls,
    type Node,
    type Edge,
    type NodeTypes,
    Handle,
    Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import type { QueryResponse, GovernanceDomain, GovernanceBoard } from '../../types/carf';
import { getGovernanceDomains, getGovernanceBoards } from '../../services/apiService';

// Domain color mapping
const DOMAIN_COLORS: Record<string, string> = {
    procurement: '#3B82F6',
    sustainability: '#10B981',
    security: '#EF4444',
    legal: '#8B5CF6',
    finance: '#F59E0B',
};

// Custom domain node component
const DomainNode: React.FC<{ data: { label: string; color: string; policyCount: number; dimmed?: boolean } }> = ({ data }) => (
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
    }}>
        <Handle type="target" position={Position.Top} style={{ background: data.color }} />
        <div>{data.label}</div>
        <div style={{ fontSize: '10px', opacity: 0.7, marginTop: '4px' }}>
            {data.policyCount} policies
        </div>
        <Handle type="source" position={Position.Bottom} style={{ background: data.color }} />
    </div>
);

const nodeTypes: NodeTypes = { domain: DomainNode };

interface SpecMapTabProps {
    lastResult: QueryResponse | null;
    selectedBoardId?: string | null;
}

const SpecMapTab: React.FC<SpecMapTabProps> = ({ lastResult, selectedBoardId }) => {
    const [domains, setDomains] = useState<GovernanceDomain[]>([]);
    const [boards, setBoards] = useState<GovernanceBoard[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const [d, b] = await Promise.all([
                    getGovernanceDomains(),
                    getGovernanceBoards(),
                ]);
                if (!cancelled) {
                    setDomains(d);
                    setBoards(b);
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
                    policyCount: 0,
                    dimmed: selectedBoard ? !inBoard : false,
                },
            });
        });

        // Add edges from context triples in the last result
        const triples = (lastResult?.context as Record<string, unknown>)?.governance_triples as Array<{
            domain_source: string; domain_target: string; predicate: string; confidence: number;
        }> | undefined;

        if (triples) {
            triples.forEach((triple, i) => {
                e.push({
                    id: `e-${i}`,
                    source: triple.domain_source,
                    target: triple.domain_target,
                    label: triple.predicate,
                    animated: true,
                    style: { strokeWidth: Math.max(1, triple.confidence * 3), stroke: '#60A5FA' },
                    labelStyle: { fontSize: '10px', fill: '#9CA3AF' },
                });
            });
        }

        return { nodes: n, edges: e };
    }, [domains, lastResult, selectedBoard]);

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
            <div style={{ height: '550px', border: '1px solid #374151', borderRadius: '8px', overflow: 'hidden' }}>
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    nodeTypes={nodeTypes}
                    fitView
                    style={{ backgroundColor: '#0D1117' }}
                >
                    <Background color="#1F2937" gap={20} />
                    <Controls />
                </ReactFlow>
            </div>
        </div>
    );
};

export default SpecMapTab;
