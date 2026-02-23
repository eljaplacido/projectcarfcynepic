/**
 * GovernanceSemanticGraphTab — Enhanced semantic graph visualization.
 *
 * Features:
 * - Nodes colored by domain with size proportional to connection count
 * - Zoom/pan controls + minimap
 * - Click-to-inspect details panel
 * - Conflict edges highlighted with dashed red
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    type Edge,
    type Node,
    type NodeTypes,
    type NodeMouseHandler,
    Handle,
    Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import type { GovernanceSemanticGraph, GovernanceSemanticNode, GovernanceSemanticEdge } from '../../types/carf';
import { getGovernanceSemanticGraph } from '../../services/apiService';

interface GovernanceSemanticGraphTabProps {
    selectedBoardId?: string | null;
    sessionId?: string;
}

const DOMAIN_COLORS: Record<string, string> = {
    procurement: '#3B82F6',
    sustainability: '#10B981',
    security: '#EF4444',
    legal: '#8B5CF6',
    finance: '#F59E0B',
};

const DEFAULT_COLOR = '#64748B';

// ---------- Custom node components with connection-aware sizing ----------

interface NodeData {
    label: string;
    domainId?: string | null;
    metadata?: Record<string, unknown>;
    connectionCount: number;
    nodeType: string;
}

function getDomainColor(domainId?: string | null): string {
    return (domainId && DOMAIN_COLORS[domainId]) || DEFAULT_COLOR;
}

const DomainNode: React.FC<{ data: NodeData }> = ({ data }) => {
    const color = getDomainColor(data.domainId);
    const scale = Math.min(1.3, 1 + data.connectionCount * 0.04);
    return (
        <div style={{
            borderRadius: '12px',
            padding: '12px 16px',
            minWidth: `${Math.round(140 * scale)}px`,
            border: `2px solid ${color}`,
            background: `${color}22`,
            color: '#DBEAFE',
            fontSize: '12px',
            fontWeight: 700,
            textAlign: 'center',
            transform: `scale(${scale})`,
        }}>
            <Handle type="target" position={Position.Top} style={{ background: color }} />
            <div>{data.label}</div>
            <div style={{ fontSize: '9px', opacity: 0.6, marginTop: '3px' }}>
                {data.connectionCount} connections
            </div>
            <Handle type="source" position={Position.Bottom} style={{ background: color }} />
        </div>
    );
};

const PolicyNode: React.FC<{ data: NodeData }> = ({ data }) => {
    const color = getDomainColor(data.domainId);
    return (
        <div style={{
            borderRadius: '10px',
            padding: '10px 14px',
            minWidth: '130px',
            border: `1px solid ${color}`,
            background: `${color}1A`,
            color: '#D1FAE5',
            fontSize: '11px',
            fontWeight: 600,
            textAlign: 'center',
        }}>
            <Handle type="target" position={Position.Top} style={{ background: color }} />
            <div>{data.label}</div>
            {data.metadata?.rule_count != null && (
                <div style={{ fontSize: '9px', opacity: 0.6, marginTop: '2px' }}>
                    {String(data.metadata.rule_count)} rules
                </div>
            )}
            <Handle type="source" position={Position.Bottom} style={{ background: color }} />
        </div>
    );
};

const ConceptNode: React.FC<{ data: NodeData }> = ({ data }) => (
    <div style={{
        borderRadius: '8px',
        padding: '8px 10px',
        minWidth: '110px',
        border: '1px solid #475569',
        background: '#0F172A',
        color: '#CBD5E1',
        fontSize: '10px',
        fontWeight: 500,
        textAlign: 'center',
    }}>
        <Handle type="target" position={Position.Top} style={{ background: '#64748B' }} />
        <div>{data.label}</div>
        <Handle type="source" position={Position.Bottom} style={{ background: '#64748B' }} />
    </div>
);

const nodeTypes: NodeTypes = {
    domain: DomainNode,
    policy: PolicyNode,
    concept: ConceptNode,
};

// ---------- Layout ----------

function buildLayout(nodes: GovernanceSemanticNode[]): Record<string, { x: number; y: number }> {
    const layout: Record<string, { x: number; y: number }> = {};
    const byType = {
        domain: nodes.filter(n => n.node_type === 'domain'),
        policy: nodes.filter(n => n.node_type === 'policy'),
        concept: nodes.filter(n => n.node_type === 'concept'),
    };

    const placeRow = (items: GovernanceSemanticNode[], y: number, startX: number, spacingX: number) => {
        items.forEach((node, idx) => {
            layout[node.node_id] = { x: startX + idx * spacingX, y };
        });
    };

    placeRow(byType.domain, 80, 40, 220);
    placeRow(byType.policy, 300, 40, 220);

    const conceptColumns = 5;
    byType.concept.forEach((node, idx) => {
        const col = idx % conceptColumns;
        const row = Math.floor(idx / conceptColumns);
        layout[node.node_id] = { x: 40 + col * 230, y: 510 + row * 110 };
    });

    return layout;
}

// ---------- Details panel ----------

interface SelectedDetail {
    type: 'node' | 'edge';
    id: string;
    label: string;
    entries: { key: string; value: string }[];
}

function buildNodeDetail(node: GovernanceSemanticNode, edges: GovernanceSemanticEdge[]): SelectedDetail {
    const connections = edges.filter(e => e.source === node.node_id || e.target === node.node_id);
    const entries: { key: string; value: string }[] = [
        { key: 'Type', value: node.node_type },
    ];
    if (node.domain_id) entries.push({ key: 'Domain', value: node.domain_id });
    entries.push({ key: 'Connections', value: String(connections.length) });
    if (node.metadata) {
        for (const [k, v] of Object.entries(node.metadata)) {
            if (v != null && k !== 'color') {
                entries.push({ key: k.replace(/_/g, ' '), value: String(v) });
            }
        }
    }
    return { type: 'node', id: node.node_id, label: node.label, entries };
}

// ---------- Main component ----------

const GovernanceSemanticGraphTab: React.FC<GovernanceSemanticGraphTabProps> = ({ selectedBoardId, sessionId }) => {
    const [graph, setGraph] = useState<GovernanceSemanticGraph | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selected, setSelected] = useState<SelectedDetail | null>(null);

    useEffect(() => {
        let active = true;
        setLoading(true);
        setError(null);

        (async () => {
            try {
                const response = await getGovernanceSemanticGraph({
                    boardId: selectedBoardId || undefined,
                    sessionId,
                    unresolvedOnly: true,
                    tripleLimit: 120,
                });
                if (active) setGraph(response);
            } catch (err) {
                if (active) setError(err instanceof Error ? err.message : String(err));
            } finally {
                if (active) setLoading(false);
            }
        })();

        return () => { active = false; };
    }, [selectedBoardId, sessionId]);

    // Pre-compute connection counts per node
    const connectionCounts = useMemo(() => {
        const counts: Record<string, number> = {};
        if (!graph) return counts;
        for (const edge of graph.edges) {
            counts[edge.source] = (counts[edge.source] || 0) + 1;
            counts[edge.target] = (counts[edge.target] || 0) + 1;
        }
        return counts;
    }, [graph]);

    const { flowNodes, flowEdges } = useMemo(() => {
        if (!graph) return { flowNodes: [] as Node[], flowEdges: [] as Edge[] };

        const layout = buildLayout(graph.nodes);

        const flowNodes: Node[] = graph.nodes.map((node) => ({
            id: node.node_id,
            type: node.node_type === 'domain' || node.node_type === 'policy' || node.node_type === 'concept'
                ? node.node_type : 'concept',
            position: layout[node.node_id] || { x: 0, y: 0 },
            data: {
                label: node.label,
                domainId: node.domain_id,
                metadata: node.metadata,
                connectionCount: connectionCounts[node.node_id] || 0,
                nodeType: node.node_type,
            } as NodeData,
            draggable: true,
        }));

        const flowEdges: Edge[] = graph.edges.map((edge) => {
            const isConflict = edge.relation === 'conflicts_with';
            const isPolicyEdge = edge.relation === 'owns_policy';
            const baseColor = isConflict ? '#EF4444' : isPolicyEdge ? '#10B981' : '#60A5FA';
            return {
                id: edge.edge_id,
                source: edge.source,
                target: edge.target,
                label: edge.relation.replace(/_/g, ' '),
                animated: isConflict,
                style: {
                    stroke: baseColor,
                    strokeWidth: Math.max(1, edge.confidence * 3),
                    strokeDasharray: isConflict ? '5 3' : undefined,
                },
                labelStyle: { fill: '#94A3B8', fontSize: 10, fontWeight: 500 },
            };
        });

        return { flowNodes, flowEdges };
    }, [graph, connectionCounts]);

    const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
        if (!graph) return;
        const gNode = graph.nodes.find(n => n.node_id === node.id);
        if (gNode) setSelected(buildNodeDetail(gNode, graph.edges));
    }, [graph]);

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '420px', color: '#9CA3AF' }}>
                Loading governance semantic graph...
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ padding: '16px', borderRadius: '8px', border: '1px solid #7F1D1D', backgroundColor: '#450A0A', color: '#FCA5A5' }}>
                Failed to load semantic graph: {error}
            </div>
        );
    }

    if (!graph || graph.nodes.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: '42px 20px', color: '#6B7280' }}>
                <div style={{ fontSize: '42px', marginBottom: '10px' }}>SG</div>
                <p style={{ fontSize: '13px' }}>
                    No semantic graph data available yet. Create governance domains/policies or run a query that emits triples.
                </p>
            </div>
        );
    }

    const basedOn = graph.explainability?.based_on || [];

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Explainability header */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1fr',
                gap: '10px',
                padding: '10px 12px',
                borderRadius: '8px',
                backgroundColor: '#111827',
                border: '1px solid #1F2937',
            }}>
                <div>
                    <div style={{ fontSize: '11px', color: '#93C5FD', fontWeight: 600, marginBottom: '4px' }}>
                        Why this
                    </div>
                    <div style={{ fontSize: '12px', color: '#CBD5E1' }}>
                        {graph.explainability?.why_this || 'Governance topology across domains, policies, conflicts, and semantic triples.'}
                    </div>
                </div>
                <div>
                    <div style={{ fontSize: '11px', color: '#93C5FD', fontWeight: 600, marginBottom: '4px' }}>
                        How confident
                    </div>
                    <div style={{ fontSize: '12px', color: '#CBD5E1', marginBottom: '6px' }}>
                        {typeof graph.explainability?.how_confident === 'number'
                            ? `${(graph.explainability.how_confident * 100).toFixed(1)}%`
                            : 'n/a'}
                    </div>
                    <div style={{ fontSize: '10px', color: '#6B7280' }}>
                        Nodes: {graph.nodes.length} | Edges: {graph.edges.length}
                    </div>
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                    <div style={{ fontSize: '11px', color: '#93C5FD', fontWeight: 600, marginBottom: '4px' }}>
                        Based on
                    </div>
                    <div style={{ fontSize: '11px', color: '#94A3B8' }}>
                        {basedOn.join(' | ') || 'No provenance details available.'}
                    </div>
                </div>
            </div>

            {/* Legend */}
            <div style={{
                display: 'flex',
                gap: '14px',
                alignItems: 'center',
                fontSize: '11px',
                color: '#94A3B8',
                backgroundColor: '#0F172A',
                border: '1px solid #1E293B',
                borderRadius: '8px',
                padding: '8px 10px',
            }}>
                <span style={{ fontWeight: 600 }}>Legend:</span>
                <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', backgroundColor: '#3B82F6', marginRight: 4, verticalAlign: 'middle' }} />Domain</span>
                <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '4px', backgroundColor: '#10B981', marginRight: 4, verticalAlign: 'middle' }} />Policy</span>
                <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '2px', backgroundColor: '#475569', marginRight: 4, verticalAlign: 'middle' }} />Concept</span>
                <span style={{ borderLeft: '1px solid #334155', paddingLeft: 10 }}>
                    <span style={{ color: '#60A5FA' }}>--- Semantic</span>
                    {' '}
                    <span style={{ color: '#10B981' }}>--- Owns</span>
                    {' '}
                    <span style={{ color: '#EF4444' }}>- - Conflict</span>
                </span>
            </div>

            {/* Graph + Details side-by-side */}
            <div style={{ display: 'flex', gap: '10px' }}>
                <div style={{
                    flex: selected ? '1 1 70%' : '1 1 100%',
                    height: '610px',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    border: '1px solid #1F2937',
                    transition: 'flex 0.3s',
                }}>
                    <ReactFlow
                        nodes={flowNodes}
                        edges={flowEdges}
                        nodeTypes={nodeTypes}
                        onNodeClick={onNodeClick}
                        onPaneClick={() => setSelected(null)}
                        fitView
                        minZoom={0.15}
                        maxZoom={1.6}
                        style={{ backgroundColor: '#020617' }}
                    >
                        <Background color="#0F172A" gap={20} />
                        <Controls />
                        <MiniMap
                            zoomable
                            pannable
                            style={{ background: '#0B1220' }}
                            nodeColor={(n) => getDomainColor((n.data as NodeData)?.domainId)}
                        />
                    </ReactFlow>
                </div>

                {/* Details panel */}
                {selected && (
                    <div style={{
                        flex: '0 0 30%',
                        maxWidth: '320px',
                        height: '610px',
                        overflowY: 'auto',
                        borderRadius: '8px',
                        border: '1px solid #1F2937',
                        backgroundColor: '#111827',
                        padding: '14px',
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                            <div style={{ fontSize: '14px', fontWeight: 700, color: '#E2E8F0' }}>{selected.label}</div>
                            <button
                                onClick={() => setSelected(null)}
                                style={{
                                    background: 'none', border: 'none', color: '#6B7280',
                                    cursor: 'pointer', fontSize: '16px', padding: '2px 6px',
                                }}
                            >
                                x
                            </button>
                        </div>
                        <div style={{ fontSize: '10px', color: '#64748B', marginBottom: '10px' }}>
                            {selected.id}
                        </div>
                        {selected.entries.map((entry, idx) => (
                            <div key={idx} style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                padding: '6px 0',
                                borderBottom: '1px solid #1E293B',
                                fontSize: '12px',
                            }}>
                                <span style={{ color: '#94A3B8', textTransform: 'capitalize' }}>{entry.key}</span>
                                <span style={{ color: '#CBD5E1', fontWeight: 500, maxWidth: '60%', textAlign: 'right', wordBreak: 'break-word' }}>
                                    {entry.value}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default GovernanceSemanticGraphTab;
