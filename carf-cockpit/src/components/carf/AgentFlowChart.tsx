/**
 * AgentFlowChart Component
 *
 * Renders an interactive agent activation sequence using ReactFlow.
 * Shows nodes for each trace step with real latency, status badges,
 * and truncated I/O. Click a node to see full input/output in an
 * expandable detail panel.
 */

import React, { useState, useMemo, useCallback } from 'react';
import ReactFlow, {
    Position,
    Handle,
    ReactFlowProvider,
} from 'reactflow';
import type { Node, Edge, NodeProps } from 'reactflow';
import 'reactflow/dist/style.css';

export interface TraceStep {
    node: string;
    action: string;
    durationMs: number;
    confidence: string;
    status: string;
    inputSummary?: string;
    outputSummary?: string;
}

interface AgentFlowChartProps {
    traceSteps: TraceStep[];
}

// Status to colour mapping
const STATUS_COLORS: Record<string, { bg: string; border: string; text: string; badge: string }> = {
    completed: { bg: '#dcfce7', border: '#22c55e', text: '#15803d', badge: 'bg-green-100 text-green-700' },
    failed: { bg: '#fee2e2', border: '#ef4444', text: '#b91c1c', badge: 'bg-red-100 text-red-700' },
    'in-progress': { bg: '#dbeafe', border: '#3b82f6', text: '#1d4ed8', badge: 'bg-blue-100 text-blue-700' },
    pending: { bg: '#f3f4f6', border: '#9ca3af', text: '#4b5563', badge: 'bg-gray-100 text-gray-600' },
};

function getStatusColor(status: string) {
    return STATUS_COLORS[status] || STATUS_COLORS.pending;
}

function truncate(text: string | undefined, maxLen: number): string {
    if (!text) return '---';
    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
}

// Custom node component rendered inside ReactFlow
const AgentNode: React.FC<NodeProps> = ({ data }) => {
    const colors = getStatusColor(data.status);

    return (
        <div
            className="rounded-lg shadow-sm border-2 p-3 min-w-[180px] max-w-[240px] cursor-pointer transition-shadow hover:shadow-md"
            style={{
                background: colors.bg,
                borderColor: colors.border,
            }}
            data-testid={`agent-node-${data.index}`}
        >
            <Handle type="target" position={Position.Top} className="!bg-gray-400 !w-2 !h-2" />

            {/* Header */}
            <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold truncate" style={{ color: colors.text }}>
                    {data.label}
                </span>
                <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${colors.badge}`}
                    data-testid={`status-badge-${data.index}`}
                >
                    {data.status}
                </span>
            </div>

            {/* Action */}
            <div className="text-[11px] text-gray-600 mb-1 truncate" title={data.action}>
                {data.action}
            </div>

            {/* Latency and Confidence */}
            <div className="flex items-center justify-between text-[10px] text-gray-500 mb-1.5">
                <span className="font-mono" data-testid={`duration-${data.index}`}>{data.durationMs}ms</span>
                <span>conf: {data.confidence}</span>
            </div>

            {/* Truncated I/O */}
            <div className="space-y-0.5">
                <div className="text-[10px] text-gray-400 truncate" title={data.inputSummary || ''}>
                    In: {truncate(data.inputSummary, 30)}
                </div>
                <div className="text-[10px] text-gray-400 truncate" title={data.outputSummary || ''}>
                    Out: {truncate(data.outputSummary, 30)}
                </div>
            </div>

            <Handle type="source" position={Position.Bottom} className="!bg-gray-400 !w-2 !h-2" />
        </div>
    );
};

const nodeTypes = { agentNode: AgentNode };

const AgentFlowChart: React.FC<AgentFlowChartProps> = ({ traceSteps }) => {
    const [selectedStep, setSelectedStep] = useState<number | null>(null);

    // Convert trace steps to ReactFlow nodes and edges
    const { nodes, edges } = useMemo(() => {
        const flowNodes: Node[] = traceSteps.map((step, idx) => ({
            id: `step-${idx}`,
            type: 'agentNode',
            position: { x: 100, y: idx * 140 },
            data: {
                label: step.node,
                action: step.action,
                durationMs: step.durationMs,
                confidence: step.confidence,
                status: step.status,
                inputSummary: step.inputSummary,
                outputSummary: step.outputSummary,
                index: idx,
            },
        }));

        const flowEdges: Edge[] = traceSteps.slice(1).map((_, idx) => ({
            id: `edge-${idx}`,
            source: `step-${idx}`,
            target: `step-${idx + 1}`,
            animated: traceSteps[idx + 1]?.status === 'in-progress',
            style: {
                stroke: getStatusColor(traceSteps[idx].status).border,
                strokeWidth: 2,
            },
        }));

        return { nodes: flowNodes, edges: flowEdges };
    }, [traceSteps]);

    const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
        const idx = parseInt(node.id.replace('step-', ''), 10);
        setSelectedStep(prev => (prev === idx ? null : idx));
    }, []);

    if (traceSteps.length === 0) {
        return (
            <div className="text-center py-8 text-gray-500" data-testid="empty-flow">
                <div className="text-3xl mb-2">&#x1F4CA;</div>
                <div className="text-sm">No agent trace steps available</div>
            </div>
        );
    }

    const selected = selectedStep !== null ? traceSteps[selectedStep] : null;

    return (
        <div className="flex flex-col h-full" data-testid="agent-flow-chart">
            {/* Flow canvas */}
            <div className="flex-1 min-h-[300px] border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
                <ReactFlowProvider>
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        nodeTypes={nodeTypes}
                        onNodeClick={onNodeClick}
                        fitView
                        fitViewOptions={{ padding: 0.3 }}
                        proOptions={{ hideAttribution: true }}
                        nodesDraggable={false}
                        nodesConnectable={false}
                        zoomOnScroll={false}
                        panOnScroll
                        minZoom={0.5}
                        maxZoom={1.5}
                    />
                </ReactFlowProvider>
            </div>

            {/* Detail panel (expandable) */}
            {selected && selectedStep !== null && (
                <div
                    className="mt-3 p-4 bg-white border border-gray-200 rounded-lg shadow-sm animate-in slide-in-from-top-2 duration-200"
                    data-testid="detail-panel"
                >
                    <div className="flex items-center justify-between mb-3">
                        <h4 className="text-sm font-semibold text-gray-900">
                            Step {selectedStep + 1}: {selected.node}
                        </h4>
                        <button
                            onClick={() => setSelectedStep(null)}
                            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
                            aria-label="Close detail panel"
                        >
                            Close
                        </button>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-xs mb-3">
                        <div>
                            <span className="text-gray-500 font-medium">Action:</span>
                            <span className="ml-1 text-gray-800">{selected.action}</span>
                        </div>
                        <div>
                            <span className="text-gray-500 font-medium">Status:</span>
                            <span className={`ml-1 font-medium ${getStatusColor(selected.status).badge.split(' ')[1]}`}>
                                {selected.status}
                            </span>
                        </div>
                        <div>
                            <span className="text-gray-500 font-medium">Duration:</span>
                            <span className="ml-1 font-mono text-gray-800">{selected.durationMs}ms</span>
                        </div>
                        <div>
                            <span className="text-gray-500 font-medium">Confidence:</span>
                            <span className="ml-1 text-gray-800">{selected.confidence}</span>
                        </div>
                    </div>

                    {/* Full I/O */}
                    <div className="space-y-2">
                        <div>
                            <span className="text-xs font-medium text-gray-600 block mb-1">Full Input</span>
                            <pre className="text-xs font-mono bg-gray-50 border border-gray-200 rounded p-2 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">
                                {selected.inputSummary || 'No input data'}
                            </pre>
                        </div>
                        <div>
                            <span className="text-xs font-medium text-gray-600 block mb-1">Full Output</span>
                            <pre className="text-xs font-mono bg-gray-50 border border-gray-200 rounded p-2 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">
                                {selected.outputSummary || 'No output data'}
                            </pre>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AgentFlowChart;
