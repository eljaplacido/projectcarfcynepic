import React, { useState, useCallback } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    MarkerType
} from 'reactflow';
import type { Node, Edge } from 'reactflow';
import 'reactflow/dist/style.css';
import type { DAGNode as DAGNodeType, DAGEdge as DAGEdgeType } from '../../types/carf';

interface CausalDAGProps {
    nodes: DAGNodeType[];
    edges: DAGEdgeType[];
    onNodeClick?: (nodeId: string) => void;
    onInterventionChange?: (nodeId: string, value: number) => void;
}

// Node explanation content based on type
const NODE_EXPLANATIONS: Record<string, { title: string; description: string; role: string }> = {
    variable: {
        title: 'Observed Variable',
        description: 'A measured quantity in the causal model that can be observed or recorded.',
        role: 'Provides data for causal inference.',
    },
    confounder: {
        title: 'Confounding Variable',
        description: 'A variable that influences both the treatment and outcome, potentially biasing causal estimates.',
        role: 'Must be controlled for to isolate true causal effects.',
    },
    intervention: {
        title: 'Intervention Point',
        description: 'The variable being manipulated or "treated" in the analysis.',
        role: 'The cause whose effect we want to measure.',
    },
    outcome: {
        title: 'Outcome Variable',
        description: 'The variable we are trying to predict or explain.',
        role: 'The effect we are measuring.',
    },
};

// Node Explanation Panel Component
const NodeExplanationPanel: React.FC<{
    node: DAGNodeType | null;
    edges: DAGEdgeType[];
    allNodes: DAGNodeType[];
    onClose: () => void;
    onInterventionChange?: (nodeId: string, value: number) => void;
}> = ({ node, edges, allNodes, onClose, onInterventionChange }) => {
    const [interventionValue, setInterventionValue] = useState<number>(node?.value || 0);

    if (!node) return null;

    const explanation = NODE_EXPLANATIONS[node.type] || NODE_EXPLANATIONS.variable;
    const incomingEdges = edges.filter(e => e.target === node.id);
    const outgoingEdges = edges.filter(e => e.source === node.id);

    const getNodeLabel = (id: string) => allNodes.find(n => n.id === id)?.label || id;

    return (
        <div className="absolute top-4 right-4 w-72 bg-white rounded-lg shadow-xl border border-gray-200 z-50">
            <div className="p-4">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                    <div>
                        <div className="flex items-center gap-2">
                            <div
                                className="w-4 h-4 rounded"
                                style={{ background: getNodeColor(node.type) }}
                            />
                            <span className="font-bold text-gray-900">{node.label}</span>
                        </div>
                        <span className="text-xs text-gray-500">{explanation.title}</span>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Description */}
                <p className="text-xs text-gray-600 mb-3">{explanation.description}</p>

                {/* Role */}
                <div className="bg-gray-50 rounded p-2 mb-3">
                    <span className="text-xs font-medium text-gray-500">Role: </span>
                    <span className="text-xs text-gray-700">{explanation.role}</span>
                </div>

                {/* Current Value */}
                {node.value !== undefined && (
                    <div className="mb-3">
                        <div className="text-xs font-medium text-gray-500 mb-1">Current Value</div>
                        <div className="text-lg font-bold text-gray-900">
                            {node.value.toFixed(2)} {node.unit || ''}
                        </div>
                    </div>
                )}

                {/* Intervention Slider (for intervention nodes) */}
                {node.type === 'intervention' && onInterventionChange && (
                    <div className="mb-3 p-3 bg-purple-50 rounded-lg">
                        <div className="text-xs font-medium text-purple-700 mb-2">Counterfactual: What if?</div>
                        <input
                            type="range"
                            min={0}
                            max={100}
                            value={interventionValue}
                            onChange={(e) => {
                                const val = Number(e.target.value);
                                setInterventionValue(val);
                            }}
                            className="w-full h-2 bg-purple-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-xs text-purple-600 mt-1">
                            <span>0</span>
                            <span className="font-bold">{interventionValue}</span>
                            <span>100</span>
                        </div>
                        <button
                            onClick={() => onInterventionChange(node.id, interventionValue)}
                            className="mt-2 w-full px-3 py-1.5 bg-purple-600 text-white text-xs rounded hover:bg-purple-700 transition-colors"
                        >
                            Simulate Intervention
                        </button>
                    </div>
                )}

                {/* Incoming Edges (Causes) */}
                {incomingEdges.length > 0 && (
                    <div className="mb-3">
                        <div className="text-xs font-medium text-gray-500 mb-1">Caused by</div>
                        <div className="space-y-1">
                            {incomingEdges.map(edge => (
                                <div key={edge.id} className="flex items-center justify-between text-xs bg-gray-50 rounded px-2 py-1">
                                    <span className="text-gray-700">{getNodeLabel(edge.source)}</span>
                                    <span className={`font-mono ${edge.effectSize >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                        {edge.effectSize > 0 ? '+' : ''}{edge.effectSize.toFixed(2)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Outgoing Edges (Effects) */}
                {outgoingEdges.length > 0 && (
                    <div>
                        <div className="text-xs font-medium text-gray-500 mb-1">Affects</div>
                        <div className="space-y-1">
                            {outgoingEdges.map(edge => (
                                <div key={edge.id} className="flex items-center justify-between text-xs bg-gray-50 rounded px-2 py-1">
                                    <span className="text-gray-700">{getNodeLabel(edge.target)}</span>
                                    <div className="flex items-center gap-1">
                                        <span className={`font-mono ${edge.effectSize >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            {edge.effectSize > 0 ? '+' : ''}{edge.effectSize.toFixed(2)}
                                        </span>
                                        {edge.validated ? (
                                            <svg className="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                            </svg>
                                        ) : (
                                            <svg className="w-3 h-3 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                            </svg>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

const CausalDAG: React.FC<CausalDAGProps> = ({ nodes, edges, onNodeClick, onInterventionChange }) => {
    const [selectedNode, setSelectedNode] = useState<DAGNodeType | null>(null);

    const handleNodeClick = useCallback((nodeId: string) => {
        const node = nodes.find(n => n.id === nodeId);
        setSelectedNode(node || null);
        onNodeClick?.(nodeId);
    }, [nodes, onNodeClick]);

    const handleClosePanel = useCallback(() => {
        setSelectedNode(null);
    }, []);

    // Convert CARF nodes to ReactFlow nodes
    const flowNodes: Node[] = nodes.map(node => ({
        id: node.id,
        data: { label: node.label, type: node.type },
        position: node.position,
        style: {
            background: getNodeColor(node.type),
            color: '#fff',
            border: selectedNode?.id === node.id ? '3px solid #1E40AF' : '2px solid #fff',
            borderRadius: node.type === 'confounder' ? '0px' : node.type === 'outcome' ? '50%' : '8px',
            padding: 10,
            fontSize: 12,
            fontWeight: 600,
            width: node.type === 'outcome' ? 80 : 60,
            height: node.type === 'outcome' ? 80 : 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            boxShadow: selectedNode?.id === node.id ? '0 0 0 4px rgba(59, 130, 246, 0.3)' : 'none',
        },
    }));

    // Convert CARF edges to ReactFlow edges
    const flowEdges: Edge[] = edges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: `${edge.effectSize > 0 ? '+' : ''}${edge.effectSize.toFixed(2)}`,
        labelStyle: { fill: '#64748b', fontSize: 10, fontWeight: 600 },
        style: {
            stroke: edge.validated ? '#10B981' : '#EF4444',
            strokeWidth: 2,
            strokeDasharray: edge.validated ? '0' : '5,5',
        },
        markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edge.validated ? '#10B981' : '#EF4444',
        },
    }));

    if (flowNodes.length === 0) {
        return (
            <div className="flex items-center justify-center h-[400px] text-gray-500 text-sm">
                No causal graph available. Submit a query to generate DAG.
            </div>
        );
    }

    return (
        <div style={{ height: 400 }} className="relative">
            <ReactFlow
                nodes={flowNodes}
                edges={flowEdges}
                onNodeClick={(_, node) => handleNodeClick(node.id)}
                fitView
                attributionPosition="bottom-left"
            >
                <Background />
                <Controls />
                <MiniMap
                    nodeColor={(node) => {
                        const type = (node.data as { type?: string }).type || 'variable';
                        return getNodeColor(type);
                    }}
                    style={{ height: 80, width: 120 }}
                />
            </ReactFlow>

            {/* Node Explanation Panel */}
            {selectedNode && (
                <NodeExplanationPanel
                    node={selectedNode}
                    edges={edges}
                    allNodes={nodes}
                    onClose={handleClosePanel}
                    onInterventionChange={onInterventionChange}
                />
            )}

            {/* Legend */}
            <div className="mt-3 flex flex-wrap gap-4 text-xs">
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                    <span>Variable</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-orange-500"></div>
                    <span>Confounder</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                    <span>Intervention</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-green-500 ring-2 ring-green-300"></div>
                    <span>Outcome</span>
                </div>
            </div>

            {/* Click hint */}
            {!selectedNode && nodes.length > 0 && (
                <div className="absolute bottom-16 left-1/2 -translate-x-1/2 bg-gray-800/80 text-white text-xs px-3 py-1.5 rounded-full">
                    Click a node to see details
                </div>
            )}
        </div>
    );
};

function getNodeColor(type: string): string {
    switch (type) {
        case 'variable': return '#3B82F6';
        case 'confounder': return '#F97316';
        case 'intervention': return '#8B5CF6';
        case 'outcome': return '#10B981';
        default: return '#6B7280';
    }
}

export default CausalDAG;
