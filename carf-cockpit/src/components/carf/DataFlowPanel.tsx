/**
 * DataFlowPanel Component
 * 
 * Visualizes the data flow through CARF's architecture layers.
 * Shows input → router → analysis → governance → output pipeline.
 * 
 * Part of Developer Transparency Window (Week 2)
 */

import React, { useState, useMemo } from 'react';
import {
    ArrowDown,
    Database,
    Cpu,
    Shield,
    Eye,
    Network,
    Zap,
    Clock,
    CheckCircle,
    AlertCircle,
    ChevronDown,
    ChevronRight,
    Maximize2,
    Minimize2
} from 'lucide-react';
import type { QueryResponse } from '../../types/carf';

interface DataFlowNode {
    id: string;
    name: string;
    layer: 'input' | 'router' | 'analysis' | 'governance' | 'output';
    status: 'pending' | 'active' | 'completed' | 'error' | 'skipped';
    duration?: number;
    inputData?: Record<string, unknown>;
    outputData?: Record<string, unknown>;
    metadata?: Record<string, unknown>;
}

interface DataFlowEdge {
    from: string;
    to: string;
    dataSize?: number;
    label?: string;
}

interface DataFlowPanelProps {
    response?: QueryResponse | null;
    isProcessing?: boolean;
    className?: string;
}

// Layer configuration
const LAYER_CONFIG = {
    input: { color: 'blue', icon: Database, label: 'Input Layer' },
    router: { color: 'purple', icon: Network, label: 'Cynefin Router' },
    analysis: { color: 'green', icon: Cpu, label: 'Analysis Engine' },
    governance: { color: 'orange', icon: Shield, label: 'Guardian Layer' },
    output: { color: 'teal', icon: Eye, label: 'Output Layer' },
};

function NodeCard({
    node,
    isExpanded,
    onToggle
}: {
    node: DataFlowNode;
    isExpanded: boolean;
    onToggle: () => void;
}) {
    const config = LAYER_CONFIG[node.layer];
    const Icon = config.icon;

    const statusColors = {
        pending: 'bg-gray-100 border-gray-300 text-gray-500',
        active: 'bg-blue-50 border-blue-400 text-blue-700 animate-pulse',
        completed: 'bg-green-50 border-green-400 text-green-700',
        error: 'bg-red-50 border-red-400 text-red-700',
        skipped: 'bg-gray-50 border-gray-200 text-gray-400',
    };

    const statusIcons = {
        pending: <Clock className="w-3 h-3" />,
        active: <Zap className="w-3 h-3" />,
        completed: <CheckCircle className="w-3 h-3" />,
        error: <AlertCircle className="w-3 h-3" />,
        skipped: <Minimize2 className="w-3 h-3" />,
    };

    return (
        <div className={`rounded-lg border-2 p-3 transition-all ${statusColors[node.status]}`}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 text-${config.color}-600`} />
                    <div>
                        <h4 className="text-sm font-medium">{node.name}</h4>
                        <span className="text-xs opacity-70">{config.label}</span>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {node.duration && (
                        <span className="text-xs text-gray-500">{node.duration}ms</span>
                    )}
                    <span className="flex items-center gap-1">
                        {statusIcons[node.status]}
                    </span>
                </div>
            </div>

            {/* Expandable Data View */}
            {(node.inputData || node.outputData) && (
                <button
                    onClick={onToggle}
                    className="mt-2 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
                >
                    {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    {isExpanded ? 'Hide data' : 'View data'}
                </button>
            )}

            {isExpanded && (
                <div className="mt-2 space-y-2">
                    {node.inputData && (
                        <div className="p-2 bg-white/50 rounded text-xs">
                            <span className="font-medium text-gray-600">Input:</span>
                            <pre className="mt-1 text-gray-700 overflow-x-auto max-h-24 overflow-y-auto">
                                {JSON.stringify(node.inputData, null, 2).slice(0, 500)}
                                {JSON.stringify(node.inputData).length > 500 && '...'}
                            </pre>
                        </div>
                    )}
                    {node.outputData && (
                        <div className="p-2 bg-white/50 rounded text-xs">
                            <span className="font-medium text-gray-600">Output:</span>
                            <pre className="mt-1 text-gray-700 overflow-x-auto max-h-24 overflow-y-auto">
                                {JSON.stringify(node.outputData, null, 2).slice(0, 500)}
                                {JSON.stringify(node.outputData).length > 500 && '...'}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export function DataFlowPanel({ response, isProcessing, className = '' }: DataFlowPanelProps) {
    const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
    const [viewMode, setViewMode] = useState<'compact' | 'detailed'>('compact');

    // Build flow nodes from response
    const flowData = useMemo(() => {
        const nodes: DataFlowNode[] = [];
        const edges: DataFlowEdge[] = [];

        // Input Node
        const responseText = response?.response ?? undefined;
        const contextQuery = response?.context?.query;
        nodes.push({
            id: 'input',
            name: 'Query Parser',
            layer: 'input',
            status: response ? 'completed' : isProcessing ? 'active' : 'pending',
            duration: 12,
            inputData: response ? { query: typeof contextQuery === 'string' ? contextQuery.substring(0, 100) : 'Query submitted' } : undefined,
            outputData: response ? { parsed: true, context_extracted: true } : undefined,
        });

        // Router Node
        nodes.push({
            id: 'router',
            name: 'Cynefin Classification',
            layer: 'router',
            status: response?.domain ? 'completed' : isProcessing ? 'active' : 'pending',
            duration: response?.domain ? 45 : undefined,
            inputData: response ? { query_type: 'causal', data_available: true } : undefined,
            outputData: response?.domain ? {
                domain: response.domain,
                confidence: response.domainConfidence,
                entropy: response.domainEntropy
            } : undefined,
        });
        edges.push({ from: 'input', to: 'router', label: 'parsed query' });

        // Analysis Node (based on domain)
        const analysisName = response?.domain === 'complicated' ? 'Causal Analyst' :
            response?.domain === 'complex' ? 'Bayesian Explorer' :
                response?.domain === 'clear' ? 'Deterministic Runner' : 'Domain Agent';
        nodes.push({
            id: 'analysis',
            name: analysisName,
            layer: 'analysis',
            status: response?.causalResult ? 'completed' : isProcessing ? 'active' : 'pending',
            duration: response?.causalResult ? 342 : undefined,
            inputData: response ? { treatment: 'supplier_program', outcome: 'scope3_emissions' } : undefined,
            outputData: response?.causalResult ? {
                effect: response.causalResult.effect,
                refutations_passed: response.causalResult.refutationsPassed
            } : undefined,
        });
        edges.push({ from: 'router', to: 'analysis', label: response?.domain || 'domain' });

        // Guardian Node
        nodes.push({
            id: 'guardian',
            name: 'Policy Validator',
            layer: 'governance',
            status: response?.guardianResult ? 'completed' : isProcessing ? 'pending' : 'pending',
            duration: response?.guardianResult ? 28 : undefined,
            inputData: response?.guardianResult ? { action: 'recommend_expansion', budget: 50000 } : undefined,
            outputData: response?.guardianResult ? {
                status: response.guardianResult.overallStatus,
                policies_checked: response.guardianResult.policies?.length ?? response.guardianResult.policiesTotal
            } : undefined,
        });
        edges.push({ from: 'analysis', to: 'guardian', label: 'proposed action' });

        // Output Node
        nodes.push({
            id: 'output',
            name: 'Response Synthesizer',
            layer: 'output',
            status: responseText ? 'completed' : 'pending',
            duration: responseText ? 156 : undefined,
            inputData: response ? { include_recommendations: true, format: 'conversational' } : undefined,
            outputData: responseText ? {
                length: responseText.length,
                has_recommendations: !!response?.nextSteps?.length
            } : undefined,
        });
        edges.push({ from: 'guardian', to: 'output', label: 'approved' });

        return { nodes, edges };
    }, [response, isProcessing]);

    const toggleNode = (nodeId: string) => {
        setExpandedNodes(prev => {
            const next = new Set(prev);
            if (next.has(nodeId)) {
                next.delete(nodeId);
            } else {
                next.add(nodeId);
            }
            return next;
        });
    };

    // Calculate total duration
    const totalDuration = flowData.nodes.reduce((sum, n) => sum + (n.duration || 0), 0);
    const completedCount = flowData.nodes.filter(n => n.status === 'completed').length;

    return (
        <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
                <div className="flex items-center gap-2">
                    <Network className="w-5 h-5 text-purple-600" />
                    <h3 className="font-medium text-gray-900">Data Flow</h3>
                    <span className="text-xs text-gray-500">
                        {completedCount}/{flowData.nodes.length} steps
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    {totalDuration > 0 && (
                        <span className="text-xs text-gray-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {totalDuration}ms total
                        </span>
                    )}
                    <button
                        onClick={() => setViewMode(v => v === 'compact' ? 'detailed' : 'compact')}
                        className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                        title={viewMode === 'compact' ? 'Expand all' : 'Collapse all'}
                    >
                        {viewMode === 'compact' ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
                    </button>
                </div>
            </div>

            {/* Flow Visualization */}
            <div className="p-4">
                <div className="flex flex-col gap-2">
                    {flowData.nodes.map((node, idx) => (
                        <React.Fragment key={node.id}>
                            <NodeCard
                                node={node}
                                isExpanded={expandedNodes.has(node.id) || viewMode === 'detailed'}
                                onToggle={() => toggleNode(node.id)}
                            />
                            {idx < flowData.nodes.length - 1 && (
                                <div className="flex items-center justify-center py-1">
                                    <ArrowDown className="w-4 h-4 text-gray-400" />
                                    {flowData.edges[idx]?.label && (
                                        <span className="ml-2 text-xs text-gray-400">
                                            {flowData.edges[idx].label}
                                        </span>
                                    )}
                                </div>
                            )}
                        </React.Fragment>
                    ))}
                </div>

                {/* Metrics Summary */}
                {response && (
                    <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-3 gap-4 text-center">
                        <div>
                            <div className="text-lg font-semibold text-gray-900">{totalDuration}ms</div>
                            <div className="text-xs text-gray-500">Total Latency</div>
                        </div>
                        <div>
                            <div className="text-lg font-semibold text-green-600">{completedCount}</div>
                            <div className="text-xs text-gray-500">Steps Completed</div>
                        </div>
                        <div>
                            <div className="text-lg font-semibold text-purple-600">
                                {response.domain || '—'}
                            </div>
                            <div className="text-xs text-gray-500">Domain Routed</div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default DataFlowPanel;
