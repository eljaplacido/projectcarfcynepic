/**
 * Developer View Component
 *
 * Provides real-time debugging and monitoring capabilities:
 * - Architecture visualization (4-layer cognitive stack)
 * - Live log streaming via WebSocket
 * - State inspection
 * - Execution timeline
 * - Experience buffer for learning replay
 */

import React, { useState, useEffect, useRef } from 'react';
import type { ExecutionTraceStep, QueryResponse } from '../../types/carf';
import { useDeveloperState } from '../../hooks/useCarfApi';
import api, { type LogEntry, type DeveloperState } from '../../services/apiService';
import ExperienceBufferPanel from './ExperienceBufferPanel';
import DataFlowPanel from './DataFlowPanel';
import DataLayerInspector from './DataLayerInspector';

interface DeveloperViewProps {
    response: QueryResponse | null;
    executionTrace: ExecutionTraceStep[];
    isProcessing?: boolean;
}

// Architecture layer colors
const LAYER_COLORS = {
    router: { bg: 'bg-blue-100', border: 'border-blue-400', text: 'text-blue-700', dot: 'bg-blue-500' },
    mesh: { bg: 'bg-purple-100', border: 'border-purple-400', text: 'text-purple-700', dot: 'bg-purple-500' },
    services: { bg: 'bg-green-100', border: 'border-green-400', text: 'text-green-700', dot: 'bg-green-500' },
    guardian: { bg: 'bg-orange-100', border: 'border-orange-400', text: 'text-orange-700', dot: 'bg-orange-500' },
};

// Log level colors
const LOG_LEVEL_COLORS = {
    DEBUG: 'text-gray-500',
    INFO: 'text-blue-600',
    WARNING: 'text-yellow-600',
    ERROR: 'text-red-600',
    CRITICAL: 'text-red-700 font-bold',
};

// Architecture Panel Component with Real-time Status
// Architecture Panel Component - Enhanced Flow Graph
// Architecture Panel Component - Enhanced Flow Graph
const ArchitecturePanel: React.FC<{
    activeLayer?: string;
    systemState?: DeveloperState['system'] | null;
    onLayerSelect?: (layerId: string) => void;
    selectedLayer?: string | null;
}> = ({ activeLayer, systemState, onLayerSelect, selectedLayer }) => {
    const layers = [
        {
            id: 'router',
            name: 'Cynefin Router',
            icon: '🧭',
            description: 'Domain classification & Routing',
            components: ['Classifier', 'Entropy'],
            color: 'blue'
        },
        {
            id: 'mesh',
            name: 'Cognitive Mesh',
            icon: '🕸️',
            description: 'Agent orchestration',
            components: ['LangGraph', 'Tools'],
            color: 'purple'
        },
        {
            id: 'services',
            name: 'Service Layer',
            icon: '⚙️',
            description: 'Causal & Bayesian engines',
            components: ['DoWhy', 'PyMC'],
            color: 'green'
        },
        {
            id: 'guardian',
            name: 'Guardian Layer',
            icon: '🛡️',
            description: 'Safety & Policy enforcement',
            components: ['Policy', 'Audit'],
            color: 'orange'
        },
    ];

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-gray-900">Execution Flow</div>
                {systemState && (
                    <div className="flex items-center gap-2 px-2 py-1 bg-gray-50 rounded-md border border-gray-100">
                        <span className={`w-2 h-2 rounded-full ${systemState.is_processing ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
                        <span className="text-xs text-gray-500 font-mono">
                            {systemState.is_processing ? 'RUNNING' : 'IDLE'}
                        </span>
                    </div>
                )}
            </div>

            {/* Flow Visualization */}
            <div className="relative py-2 pl-4">
                {/* Vertical Connection Line */}
                <div className="absolute left-[29px] top-6 bottom-10 w-0.5 bg-gradient-to-b from-blue-200 via-purple-200 to-orange-200" />

                {/* Active Flow Indicator (Animated) */}
                {systemState?.is_processing && (
                    <div className="absolute left-[26px] top-6 w-2 h-2 bg-blue-500 rounded-full animate-ping"
                        style={{
                            animationDuration: '2s',
                            top: activeLayer === 'router' ? '12%' :
                                activeLayer === 'mesh' ? '37%' :
                                    activeLayer === 'services' ? '62%' : '87%'
                        }}
                    />
                )}

                <div className="space-y-6">
                    {layers.map((layer, idx) => {
                        const isActive = activeLayer === layer.id || systemState?.current_layer === layer.id;
                        const isSelected = selectedLayer === layer.id;

                        return (
                            <div
                                key={layer.id}
                                className="relative flex items-start gap-4 group cursor-pointer"
                                onClick={() => onLayerSelect && onLayerSelect(layer.id)}
                            >
                                {/* Node Icon */}
                                <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${isActive || isSelected
                                    ? `bg-white border-${layer.color}-500 shadow-md scale-110`
                                    : `bg-gray-50 border-gray-200 grayscale`
                                    }`}>
                                    <span className="text-sm">{layer.icon}</span>
                                    {isActive && (
                                        <span className={`absolute -inset-1 rounded-full border border-${layer.color}-400 animate-ping opacity-20`} />
                                    )}
                                </div>

                                {/* Node Content */}
                                <div className={`flex-1 p-3 rounded-lg border transition-all duration-300 ${isActive || isSelected
                                    ? `bg-${layer.color}-50 border-${layer.color}-200 shadow-sm translate-x-1`
                                    : 'bg-white border-gray-100 opacity-80'
                                    }`}>
                                    <div className="flex justify-between items-start mb-1">
                                        <div className="font-medium text-sm text-gray-900">{layer.name}</div>
                                        {(isActive || isSelected) && <div className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">
                                            {isActive ? 'Active' : 'Inspecting'}
                                        </div>}
                                    </div>
                                    <div className="text-xs text-gray-500 mb-2">{layer.description}</div>

                                    {/* Sub-components badges */}
                                    <div className="flex gap-1.5 flex-wrap">
                                        {layer.components.map(c => (
                                            <span key={c} className={`text-[10px] px-1.5 py-0.5 rounded border ${isActive || isSelected
                                                ? `bg-white border-${layer.color}-200 text-${layer.color}-700`
                                                : 'bg-gray-50 border-gray-200 text-gray-400'
                                                }`}>
                                                {c}
                                            </span>
                                        ))}
                                    </div>

                                    {/* Expanded Details (Drill Down) */}
                                    {isSelected && (
                                        <div className="mt-3 pt-3 border-t border-gray-200 animate-in slide-in-from-top-2 duration-200">
                                            <div className="grid grid-cols-2 gap-2 text-xs">
                                                <div>
                                                    <span className="font-semibold text-gray-600 block mb-1">Inputs</span>
                                                    <div className="bg-white p-1.5 rounded border border-gray-200 text-gray-500 font-mono">
                                                        {'{ "query": "..." }'}
                                                    </div>
                                                </div>
                                                <div>
                                                    <span className="font-semibold text-gray-600 block mb-1">Outputs</span>
                                                    <div className="bg-white p-1.5 rounded border border-gray-200 text-gray-500 font-mono">
                                                        {'{ "status": "ok" }'}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="mt-2 text-right">
                                                <button className="text-[10px] text-blue-600 hover:underline">
                                                    View {layer.components.length} components →
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Connection Arrow for active step */}
                                {idx < layers.length - 1 && (
                                    <div className="absolute left-[15px] -bottom-4 z-0">
                                        <svg className={`w-3 h-3 text-gray-300 ${isActive ? `text-${layer.color}-400` : ''}`} viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M12 2L12 22M9 19L12 22L15 19" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
                                        </svg>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* System Telemetry Compact */}
            {systemState && (
                <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-gray-100">
                    <div className="text-center">
                        <div className="text-[10px] text-gray-400 uppercase tracking-wide">Avg Latency</div>
                        <div className="text-xs font-mono font-medium text-gray-700">142ms</div>
                    </div>
                    <div className="text-center">
                        <div className="text-[10px] text-gray-400 uppercase tracking-wide">Success Rate</div>
                        <div className="text-xs font-mono font-medium text-green-600">99.8%</div>
                    </div>
                    <div className="text-center">
                        <div className="text-[10px] text-gray-400 uppercase tracking-wide">Queries</div>
                        <div className="text-xs font-mono font-medium text-blue-600">{systemState.queries_processed}</div>
                    </div>
                </div>
            )}
        </div>
    );
};

// Live Log Stream Component
const LiveLogStream: React.FC<{
    initialLogs?: LogEntry[];
}> = ({ initialLogs = [] }) => {
    const [logs, setLogs] = useState<LogEntry[]>(initialLogs);
    const [isConnected, setIsConnected] = useState(false);
    const [filter, setFilter] = useState<{ layer: string; level: string }>({ layer: 'all', level: 'all' });
    const [isPaused, setIsPaused] = useState(false);
    const logContainerRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);

    // Connect to WebSocket
    useEffect(() => {
        if (isPaused) return;

        try {
            const ws = api.connectDeveloperWebSocket(
                (log) => {
                    setLogs(prev => [...prev.slice(-99), log]); // Keep last 100 logs
                },
                () => setIsConnected(false),
                () => setIsConnected(false)
            );

            wsRef.current = ws;
            ws.onopen = () => setIsConnected(true);

            return () => {
                ws.close();
                wsRef.current = null;
            };
        } catch {
            // WebSocket not available, fall back to polling
            const interval = setInterval(async () => {
                try {
                    const { logs: newLogs } = await api.getDeveloperLogs({ limit: 20 });
                    setLogs(newLogs);
                } catch {
                    // Ignore polling errors
                }
            }, 2000);

            return () => clearInterval(interval);
        }
    }, [isPaused]);

    // Auto-scroll to bottom
    useEffect(() => {
        if (logContainerRef.current && !isPaused) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [logs, isPaused]);

    const filteredLogs = logs.filter(log => {
        if (filter.layer !== 'all' && log.layer !== filter.layer) return false;
        if (filter.level !== 'all' && log.level !== filter.level) return false;
        return true;
    });

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="text-sm font-semibold text-gray-900">Live Logs</div>
                    <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setIsPaused(!isPaused)}
                        className={`px-2 py-1 text-xs rounded ${isPaused ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}
                    >
                        {isPaused ? '▶ Resume' : '⏸ Pause'}
                    </button>
                    <button
                        onClick={() => setLogs([])}
                        className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                    >
                        Clear
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div className="flex gap-2">
                <select
                    value={filter.layer}
                    onChange={(e) => setFilter(prev => ({ ...prev, layer: e.target.value }))}
                    className="text-xs border border-gray-300 rounded px-2 py-1"
                >
                    <option value="all">All Layers</option>
                    <option value="router">Router</option>
                    <option value="mesh">Mesh</option>
                    <option value="services">Services</option>
                    <option value="guardian">Guardian</option>
                </select>
                <select
                    value={filter.level}
                    onChange={(e) => setFilter(prev => ({ ...prev, level: e.target.value }))}
                    className="text-xs border border-gray-300 rounded px-2 py-1"
                >
                    <option value="all">All Levels</option>
                    <option value="DEBUG">Debug</option>
                    <option value="INFO">Info</option>
                    <option value="WARNING">Warning</option>
                    <option value="ERROR">Error</option>
                </select>
            </div>

            {/* Log stream */}
            <div
                ref={logContainerRef}
                className="h-64 overflow-y-auto bg-gray-900 rounded-lg p-3 font-mono text-xs"
            >
                {filteredLogs.length === 0 ? (
                    <div className="text-gray-500 italic">Waiting for logs...</div>
                ) : (
                    filteredLogs.map((log, idx) => {
                        const levelColor = LOG_LEVEL_COLORS[log.level as keyof typeof LOG_LEVEL_COLORS] || 'text-gray-400';
                        const layerColor = LAYER_COLORS[log.layer as keyof typeof LAYER_COLORS]?.text || 'text-gray-400';

                        return (
                            <div key={idx} className="flex items-start gap-2 py-0.5 hover:bg-gray-800 rounded">
                                <span className="text-gray-500 flex-shrink-0 w-20">
                                    {new Date(log.timestamp).toLocaleTimeString()}
                                </span>
                                <span className={`flex-shrink-0 w-16 ${levelColor}`}>
                                    [{log.level}]
                                </span>
                                <span className={`flex-shrink-0 w-16 ${layerColor}`}>
                                    [{log.layer}]
                                </span>
                                <span className="text-gray-300">{log.message}</span>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
};

// Execution Timeline Component
const ExecutionTimeline: React.FC<{
    trace: ExecutionTraceStep[];
    executionSteps?: DeveloperState['execution_timeline'];
}> = ({ trace, executionSteps = [] }) => {
    const [expanded, setExpanded] = useState<string | null>(null);

    // Merge local trace with API execution steps
    const steps = executionSteps.length > 0
        ? executionSteps.map(step => ({
            layer: step.layer,
            node: step.name,
            action: step.name,
            durationMs: step.duration_ms || 0,
            confidence: step.status,
            timestamp: new Date(step.start_time * 1000).toISOString(),
            metadata: { input: step.input_summary, output: step.output_summary },
        }))
        : trace;

    if (steps.length === 0) {
        return (
            <div className="text-sm text-gray-500 italic">
                No execution trace available
            </div>
        );
    }

    const totalDuration = steps.reduce((sum, step) => sum + (step.durationMs || 0), 0);

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-gray-900">Execution Timeline</div>
                <div className="text-xs text-gray-500">Total: {totalDuration}ms</div>
            </div>

            {/* Timeline visualization */}
            <div className="flex h-4 rounded-full overflow-hidden bg-gray-200">
                {steps.map((step, idx) => {
                    const width = totalDuration > 0 ? (step.durationMs || 0) / totalDuration * 100 : 0;
                    const colors = LAYER_COLORS[step.layer as keyof typeof LAYER_COLORS] || LAYER_COLORS.services;
                    return (
                        <div
                            key={idx}
                            className={`${colors.dot} border-r border-white/50 last:border-r-0 hover:opacity-80 cursor-pointer transition-opacity`}
                            style={{ width: `${Math.max(width, 2)}%` }}
                            title={`${step.node}: ${step.durationMs}ms`}
                            onClick={() => setExpanded(expanded === `${idx}` ? null : `${idx}`)}
                        />
                    );
                })}
            </div>

            {/* Step list */}
            <div className="space-y-1 max-h-64 overflow-y-auto">
                {steps.map((step, idx) => {
                    const colors = LAYER_COLORS[step.layer as keyof typeof LAYER_COLORS] || LAYER_COLORS.services;
                    const isExpanded = expanded === `${idx}`;
                    const widthPercent = totalDuration > 0 ? Math.round((step.durationMs || 0) / totalDuration * 100) : 0;

                    return (
                        <div key={idx} className="border border-gray-200 rounded-lg overflow-hidden">
                            <button
                                onClick={() => setExpanded(isExpanded ? null : `${idx}`)}
                                className="w-full p-2 flex items-center justify-between hover:bg-gray-50 text-left"
                            >
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${colors.dot}`} />
                                    <span className="text-xs font-mono text-gray-700 truncate">{step.node}</span>
                                    <span className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 ${colors.bg} ${colors.text}`}>
                                        {step.layer}
                                    </span>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                        <div className={`h-full ${colors.dot}`} style={{ width: `${widthPercent}%` }} />
                                    </div>
                                    <span className="text-xs text-gray-500 w-12 text-right">{step.durationMs}ms</span>
                                    <svg
                                        className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </div>
                            </button>
                            {isExpanded && (
                                <div className="p-3 bg-gray-50 border-t border-gray-200">
                                    <div className="grid grid-cols-2 gap-3 text-xs">
                                        <div>
                                            <span className="text-gray-500">Action:</span>
                                            <span className="ml-1 text-gray-700">{step.action}</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500">Status:</span>
                                            <span className="ml-1 text-gray-700">{step.confidence}</span>
                                        </div>
                                        {step.timestamp && (
                                            <div className="col-span-2">
                                                <span className="text-gray-500">Timestamp:</span>
                                                <span className="ml-1 font-mono text-gray-700">{step.timestamp}</span>
                                            </div>
                                        )}
                                    </div>
                                    {step.metadata && Object.keys(step.metadata).length > 0 && (
                                        <div className="mt-2">
                                            <span className="text-xs text-gray-500">Metadata:</span>
                                            <pre className="mt-1 p-2 bg-gray-100 rounded text-xs overflow-x-auto">
                                                {JSON.stringify(step.metadata, null, 2)}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

// State Inspector Component
const StateInspector: React.FC<{ response: QueryResponse | null }> = ({ response }) => {
    const [activeTab, setActiveTab] = useState<'epistemic' | 'causal' | 'bayesian' | 'guardian'>('epistemic');
    const [searchTerm, setSearchTerm] = useState('');

    if (!response) {
        return (
            <div className="text-sm text-gray-500 italic">
                No state to inspect
            </div>
        );
    }

    const epistemicState = {
        domain: response.domain,
        confidence: response.domainConfidence,
        entropy: response.domainEntropy,
        sessionId: response.sessionId,
        requiresHuman: response.requiresHuman,
    };

    const tabs = [
        { id: 'epistemic', label: 'Epistemic', data: epistemicState },
        { id: 'causal', label: 'Causal', data: response.causalResult },
        { id: 'bayesian', label: 'Bayesian', data: response.bayesianResult },
        { id: 'guardian', label: 'Guardian', data: response.guardianResult },
    ];

    const currentData = tabs.find(t => t.id === activeTab)?.data;
    const jsonString = currentData ? JSON.stringify(currentData, null, 2) : 'No data available';

    // Filter JSON by search term
    const filteredJson = searchTerm
        ? jsonString.split('\n').filter(line => line.toLowerCase().includes(searchTerm.toLowerCase())).join('\n')
        : jsonString;

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-gray-900">State Inspector</div>
                <button
                    onClick={() => navigator.clipboard.writeText(jsonString)}
                    className="text-xs text-primary hover:underline"
                >
                    Copy JSON
                </button>
            </div>

            {/* Search */}
            <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search state..."
                className="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
            />

            {/* Tabs */}
            <div className="flex border-b border-gray-200">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as typeof activeTab)}
                        className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${activeTab === tab.id
                            ? 'border-primary text-primary'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                            }`}
                    >
                        {tab.label}
                        {tab.data && <span className="ml-1 text-green-500">•</span>}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="p-3 bg-gray-900 rounded-lg max-h-64 overflow-y-auto">
                <pre className="text-xs font-mono text-green-400 whitespace-pre-wrap">
                    {filteredJson}
                </pre>
            </div>
        </div>
    );
};

// Main Developer View Component
const DeveloperView: React.FC<DeveloperViewProps> = ({ response, executionTrace, isProcessing }) => {
    const [activePanel, setActivePanel] = useState<'architecture' | 'logs' | 'timeline' | 'state' | 'experience' | 'dataflow' | 'datalayer'>('architecture');
    const [selectedLayer, setSelectedLayer] = useState<string | null>(null);
    const { state: developerState, loading, error, fetchState } = useDeveloperState();

    // Auto-refresh developer state when processing
    useEffect(() => {
        if (isProcessing) {
            const interval = setInterval(fetchState, 1000);
            return () => clearInterval(interval);
        }
    }, [isProcessing, fetchState]);

    // Determine current active layer based on processing
    const activeLayer = isProcessing
        ? executionTrace.length > 0
            ? executionTrace[executionTrace.length - 1].layer
            : 'router'
        : undefined;

    const panels = [
        { id: 'architecture', label: 'Architecture', icon: '🏗️' },
        { id: 'dataflow', label: 'Data Flow', icon: '🌊' },
        { id: 'logs', label: 'Live Logs', icon: '📋' },
        { id: 'timeline', label: 'Timeline', icon: '⏱️' },
        { id: 'state', label: 'State', icon: '📊' },
        { id: 'experience', label: 'Experience', icon: '💾' },
    ];

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-gray-200 mb-4">
                <div className="flex items-center gap-2">
                    <span className="text-lg">🔧</span>
                    <span className="text-sm font-semibold text-gray-900">Developer Cockpit</span>
                </div>
                <div className="flex items-center gap-2">
                    {loading && (
                        <span className="animate-spin w-3 h-3 border-2 border-primary border-t-transparent rounded-full" />
                    )}
                    {isProcessing && (
                        <div className="flex items-center gap-1 text-xs text-green-600">
                            <span className="animate-pulse w-2 h-2 rounded-full bg-green-500" />
                            Processing
                        </div>
                    )}
                    <button
                        onClick={fetchState}
                        className="p-1 hover:bg-gray-100 rounded"
                        title="Refresh"
                    >
                        <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                    </button>
                </div>
            </div>

            {/* Panel Tabs */}
            <div className="flex gap-1 mb-4">
                {panels.map(panel => (
                    <button
                        key={panel.id}
                        onClick={() => setActivePanel(panel.id as typeof activePanel)}
                        className={`flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${activePanel === panel.id
                            ? 'bg-primary text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }`}
                    >
                        <span>{panel.icon}</span>
                        <span>{panel.label}</span>
                    </button>
                ))}
            </div>

            {/* Error banner */}
            {error && (
                <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                    {error.message}
                </div>
            )}

            {/* Panel Content */}
            <div className="flex-1 overflow-y-auto">
                {activePanel === 'architecture' && (
                    <ArchitecturePanel
                        activeLayer={activeLayer}
                        systemState={developerState?.system}
                        selectedLayer={selectedLayer}
                        onLayerSelect={setSelectedLayer}
                    />
                )}
                {activePanel === 'dataflow' && (
                    <DataFlowPanel
                        response={response}
                        isProcessing={isProcessing}
                        className="border-none shadow-none"
                    />
                )}
                {activePanel === 'datalayer' && (
                    <DataLayerInspector
                        context={response?.context}
                        className="border-none shadow-none"
                    />
                )}
                {activePanel === 'logs' && (
                    <LiveLogStream initialLogs={developerState?.recent_logs} />
                )}
                {activePanel === 'timeline' && (
                    <ExecutionTimeline
                        trace={executionTrace}
                        executionSteps={developerState?.execution_timeline}
                    />
                )}
                {activePanel === 'state' && <StateInspector response={response} />}
                {activePanel === 'experience' && (
                    <ExperienceBufferPanel
                        sessionId={response?.sessionId}
                        onApplyLearning={(pattern) => {
                            console.log('[CYNEPIC] Apply learning:', pattern);
                            alert(`Learning pattern applied: ${pattern}`);
                        }}
                    />
                )}
            </div>

            {/* Export Button */}
            <div className="pt-3 border-t border-gray-200 mt-4">
                <button
                    onClick={() => {
                        const data = {
                            timestamp: new Date().toISOString(),
                            response,
                            executionTrace,
                            developerState,
                        };
                        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `carf-debug-${Date.now()}.json`;
                        a.click();
                        URL.revokeObjectURL(url);
                    }}
                    className="w-full px-3 py-2 bg-gray-100 text-gray-700 text-xs font-medium rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center gap-2"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Export Debug Data
                </button>
            </div>

            {/* Developer Feedback Panel */}
            <div className="pt-3 border-t border-gray-200 mt-2">
                <div className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
                    </svg>
                    Feedback & Corrections
                </div>
                <div className="grid grid-cols-2 gap-2">
                    <button
                        onClick={() => {
                            const issue = prompt('Describe the issue you encountered:');
                            if (issue) {
                                const feedbackData = {
                                    type: 'issue',
                                    timestamp: new Date().toISOString(),
                                    description: issue,
                                    context: {
                                        sessionId: response?.sessionId,
                                        domain: response?.domain,
                                        executionSteps: executionTrace.length,
                                    },
                                };
                                console.log('[CYNEPIC Feedback]', feedbackData);
                                // In production, this would POST to /api/feedback
                                alert('Thank you! Your issue has been logged for review.');
                            }
                        }}
                        className="px-3 py-2 bg-red-50 text-red-700 text-xs font-medium rounded-lg hover:bg-red-100 transition-colors flex items-center justify-center gap-1"
                    >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        Report Issue
                    </button>
                    <button
                        onClick={() => {
                            const suggestion = prompt('Suggest an improvement for the analysis:');
                            if (suggestion) {
                                const feedbackData = {
                                    type: 'improvement',
                                    timestamp: new Date().toISOString(),
                                    description: suggestion,
                                    context: {
                                        sessionId: response?.sessionId,
                                        domain: response?.domain,
                                        confidence: response?.domainConfidence,
                                    },
                                };
                                console.log('[CYNEPIC Feedback]', feedbackData);
                                // In production, this would POST to /api/feedback
                                alert('Thank you! Your suggestion has been recorded.');
                            }
                        }}
                        className="px-3 py-2 bg-blue-50 text-blue-700 text-xs font-medium rounded-lg hover:bg-blue-100 transition-colors flex items-center justify-center gap-1"
                    >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        Suggest Improvement
                    </button>
                </div>
                <p className="text-[10px] text-gray-500 mt-2 text-center">
                    Feedback helps improve system accuracy and routing decisions
                </p>
            </div>
        </div>
    );
};

export default DeveloperView;
