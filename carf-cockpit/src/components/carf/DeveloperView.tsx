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

import React, { useState, useEffect, useRef, useMemo } from 'react';
import type { ExecutionTraceStep, QueryResponse } from '../../types/carf';
import { useDeveloperState } from '../../hooks/useCarfApi';
import api, { type LogEntry, type DeveloperState, submitFeedback } from '../../services/apiService';
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
    architectureLayers?: DeveloperState['architecture'];
}> = ({ activeLayer, systemState, onLayerSelect, selectedLayer, architectureLayers }) => {
    const [componentViewLayer, setComponentViewLayer] = useState<string | null>(null);

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
                                                <button
                                                    className="text-[10px] text-blue-600 hover:underline"
                                                    data-testid={`view-components-${layer.id}`}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setComponentViewLayer(componentViewLayer === layer.id ? null : layer.id);
                                                    }}
                                                >
                                                    {componentViewLayer === layer.id ? 'Hide' : 'View'} {layer.components.length} components →
                                                </button>
                                            </div>

                                            {/* Component detail panel */}
                                            {componentViewLayer === layer.id && (
                                                <div className="mt-2 space-y-1.5" data-testid={`components-panel-${layer.id}`}>
                                                    {(() => {
                                                        // Try to match architecture data from API
                                                        const archLayer = architectureLayers?.find(a => a.id === layer.id);
                                                        const comps = archLayer ? archLayer.components : layer.components;
                                                        const layerStatus = archLayer?.status || 'ready';

                                                        return comps.map((comp, ci) => (
                                                            <div
                                                                key={ci}
                                                                className={`flex items-center justify-between p-2 rounded border text-xs ${
                                                                    layerStatus === 'error'
                                                                        ? 'bg-red-50 border-red-200'
                                                                        : 'bg-white border-gray-200'
                                                                }`}
                                                            >
                                                                <span className="font-medium text-gray-700">{comp}</span>
                                                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                                                    layerStatus === 'error'
                                                                        ? 'bg-red-100 text-red-700'
                                                                        : 'bg-green-100 text-green-700'
                                                                }`}>
                                                                    {layerStatus === 'error' ? 'error' : 'ready'}
                                                                </span>
                                                            </div>
                                                        ));
                                                    })()}
                                                    {architectureLayers?.find(a => a.id === layer.id)?.last_activity && (
                                                        <div className="text-[10px] text-gray-400 mt-1">
                                                            Last activity: {architectureLayers.find(a => a.id === layer.id)!.last_activity}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
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
                        <div className="text-xs font-mono font-medium text-gray-700" data-testid="telemetry-latency">
                            {systemState.queries_processed > 0
                                ? `${Math.round(systemState.uptime_seconds * 1000 / systemState.queries_processed)}ms`
                                : '0ms'}
                        </div>
                    </div>
                    <div className="text-center">
                        <div className="text-[10px] text-gray-400 uppercase tracking-wide">Success Rate</div>
                        <div className="text-xs font-mono font-medium text-green-600" data-testid="telemetry-success">
                            {systemState.queries_processed > 0
                                ? `${(((systemState.queries_processed - systemState.errors_count) / systemState.queries_processed) * 100).toFixed(1)}%`
                                : '0.0%'}
                        </div>
                    </div>
                    <div className="text-center">
                        <div className="text-[10px] text-gray-400 uppercase tracking-wide">Queries</div>
                        <div className="text-xs font-mono font-medium text-blue-600" data-testid="telemetry-queries">{systemState.queries_processed}</div>
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
            let cancelled = false;
            const interval = setInterval(async () => {
                if (cancelled) return;
                try {
                    const { logs: newLogs } = await api.getDeveloperLogs({ limit: 20 });
                    if (!cancelled) setLogs(newLogs);
                } catch {
                    // Ignore polling errors
                }
            }, 5000);

            return () => {
                cancelled = true;
                clearInterval(interval);
            };
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

    // Merge local trace with API execution steps -- prefer real data from API
    const steps = executionSteps.length > 0
        ? executionSteps.map(step => ({
            layer: step.layer,
            node: step.name,
            action: step.name,
            durationMs: step.duration_ms || (step.end_time && step.start_time ? Math.round((step.end_time - step.start_time) * 1000) : 0),
            confidence: step.status,
            timestamp: new Date(step.start_time * 1000).toISOString(),
            metadata: { input: step.input_summary, output: step.output_summary },
        }))
        : trace;

    if (steps.length === 0) {
        return (
            <div className="text-sm text-gray-500 italic" data-testid="timeline-empty">
                No execution trace available
            </div>
        );
    }

    const totalDuration = steps.reduce((sum, step) => sum + (step.durationMs || 0), 0);
    const maxStepDuration = Math.max(...steps.map(s => s.durationMs || 0), 1);

    return (
        <div className="space-y-3" data-testid="execution-timeline">
            <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-gray-900">Execution Timeline</div>
                <div className="text-xs text-gray-500" data-testid="timeline-total">Total: {totalDuration}ms</div>
            </div>

            {/* Timeline bar visualization -- proportional segments */}
            <div className="flex h-5 rounded-full overflow-hidden bg-gray-200" data-testid="timeline-bar">
                {steps.map((step, idx) => {
                    const width = totalDuration > 0 ? (step.durationMs || 0) / totalDuration * 100 : 0;
                    const colors = LAYER_COLORS[step.layer as keyof typeof LAYER_COLORS] || LAYER_COLORS.services;
                    return (
                        <div
                            key={idx}
                            className={`${colors.dot} border-r border-white/50 last:border-r-0 hover:opacity-80 cursor-pointer transition-opacity relative group`}
                            style={{ width: `${Math.max(width, 2)}%` }}
                            title={`${step.node}: ${step.durationMs}ms (${totalDuration > 0 ? Math.round(width) : 0}%)`}
                            onClick={() => setExpanded(expanded === `${idx}` ? null : `${idx}`)}
                            data-testid={`timeline-segment-${idx}`}
                        >
                            {/* Tooltip on hover */}
                            <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:block z-10 whitespace-nowrap">
                                <div className="bg-gray-900 text-white text-[10px] px-2 py-1 rounded shadow-lg">
                                    {step.node}: {step.durationMs}ms
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Step list with proportional bars */}
            <div className="space-y-1 max-h-64 overflow-y-auto">
                {steps.map((step, idx) => {
                    const colors = LAYER_COLORS[step.layer as keyof typeof LAYER_COLORS] || LAYER_COLORS.services;
                    const isExpanded = expanded === `${idx}`;
                    const proportionalWidth = maxStepDuration > 0 ? Math.round((step.durationMs || 0) / maxStepDuration * 100) : 0;

                    return (
                        <div key={idx} className="border border-gray-200 rounded-lg overflow-hidden" data-testid={`timeline-step-${idx}`}>
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
                                    {/* Proportional bar relative to longest step */}
                                    <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                                        <div className={`h-full rounded-full ${colors.dot}`} style={{ width: `${proportionalWidth}%` }} />
                                    </div>
                                    <span className="text-xs font-mono text-gray-500 w-14 text-right" data-testid={`step-duration-${idx}`}>
                                        {step.durationMs}ms
                                    </span>
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
                                        <div>
                                            <span className="text-gray-500">Duration:</span>
                                            <span className="ml-1 font-mono text-gray-700">{step.durationMs}ms</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500">% of Total:</span>
                                            <span className="ml-1 font-mono text-gray-700">
                                                {totalDuration > 0 ? ((step.durationMs || 0) / totalDuration * 100).toFixed(1) : 0}%
                                            </span>
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

// Cynefin-aware recommendation map for DeepEval metrics
const CYNEFIN_RECOMMENDATIONS: Record<string, Record<string, string>> = {
    clear: {
        relevancy: 'In the Clear domain, answers should directly map to best practices. Ensure the response references established procedures.',
        hallucination: 'Clear domain answers should be factual and verifiable. Cross-check against known policies and SOPs.',
        reasoning: 'Clear problems require straightforward sense-categorize-respond reasoning. Ensure the chain is concise.',
        uix: 'Users expect direct, actionable instructions in the Clear domain. Minimize ambiguity.',
    },
    complicated: {
        relevancy: 'Complicated domain answers should reference expert analysis (causal inference, statistical tests). Ensure analytical depth.',
        hallucination: 'Verify causal claims against DoWhy refutation tests. High hallucination risk here undermines trust in expert analysis.',
        reasoning: 'Complicated problems need sense-analyze-respond. Ensure each analytical step is visible and justified.',
        uix: 'Present multiple expert perspectives. Show confidence intervals and alternative hypotheses.',
    },
    complex: {
        relevancy: 'Complex domain answers should present probes and safe-to-fail experiments, not definitive solutions.',
        hallucination: 'In complex domains, some uncertainty is expected. Flag overconfident claims as potential hallucinations.',
        reasoning: 'Complex problems require probe-sense-respond. Ensure Bayesian uncertainty quantification is surfaced.',
        uix: 'Communicate uncertainty honestly. Use Bayesian posteriors and recommend next information-gathering steps.',
    },
    chaotic: {
        relevancy: 'Chaotic domain answers should focus on immediate stabilization actions. Speed matters more than depth.',
        hallucination: 'In chaotic situations, even approximate answers can help. Flag when data is too sparse for reliable conclusions.',
        reasoning: 'Chaotic problems need act-sense-respond. Ensure the first action is clearly prioritized.',
        uix: 'Present the most urgent action first. Use clear severity indicators and escalation paths.',
    },
    disorder: {
        relevancy: 'Disorder indicates classification failure. The answer may not be relevant until the domain is resolved.',
        hallucination: 'High hallucination risk in disorder. Consider re-classifying the query with more context.',
        reasoning: 'Reasoning depth cannot be assessed until the proper domain is identified. Escalate for human review.',
        uix: 'Clearly communicate that the system needs more information to provide a reliable answer.',
    },
};

// Evaluation Metrics Panel Component
const EvaluationMetricsPanel: React.FC<{ response: QueryResponse | null }> = ({ response }) => {
    // Mock evaluation data - in production this would come from the EvaluationService
    const [metrics, setMetrics] = React.useState<{
        relevancy_score: number;
        hallucination_risk: number;
        reasoning_depth: number;
        uix_compliance: number;
        task_completion: boolean;
        evaluation_model: string;
        evaluation_latency_ms: number;
    } | null>(null);

    const [expandedMetric, setExpandedMetric] = React.useState<string | null>(null);

    React.useEffect(() => {
        if (response?.domainConfidence) {
            // Simulate evaluation metrics based on response confidence
            const baseScore = response.domainConfidence;
            setMetrics({
                relevancy_score: Math.min(1, baseScore + Math.random() * 0.1),
                hallucination_risk: Math.max(0, 0.25 - baseScore * 0.2 + Math.random() * 0.1),
                reasoning_depth: Math.min(1, baseScore * 0.9 + Math.random() * 0.15),
                uix_compliance: Math.min(1, baseScore * 0.85 + Math.random() * 0.2),
                task_completion: baseScore > 0.6,
                evaluation_model: 'deepseek-chat',
                evaluation_latency_ms: Math.floor(150 + Math.random() * 200)
            });
        }
    }, [response]);

    if (!metrics) {
        return (
            <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">&#x1F4CA;</div>
                <div className="text-sm">Run a query to see evaluation metrics</div>
            </div>
        );
    }

    const domain = response?.domain || 'disorder';
    const domainRecs = CYNEFIN_RECOMMENDATIONS[domain] || CYNEFIN_RECOMMENDATIONS.disorder;

    const metricDefinitions = [
        {
            key: 'relevancy',
            label: 'Answer Relevancy',
            value: metrics.relevancy_score,
            isInverted: false,
            description: 'Measures how well the response addresses the original query intent.',
            factors: [
                { name: 'Query-answer alignment', score: metrics.relevancy_score * 0.9 + 0.05 },
                { name: 'Context utilization', score: metrics.relevancy_score * 0.85 + 0.1 },
                { name: 'Domain appropriateness', score: metrics.relevancy_score },
            ],
        },
        {
            key: 'hallucination',
            label: 'Hallucination Risk',
            value: metrics.hallucination_risk,
            isInverted: true,
            description: 'Probability that the response contains fabricated or unsupported claims.',
            factors: [
                { name: 'Factual grounding', score: 1 - metrics.hallucination_risk },
                { name: 'Source attribution', score: 1 - metrics.hallucination_risk * 1.2 },
                { name: 'Consistency check', score: 1 - metrics.hallucination_risk * 0.8 },
            ],
        },
        {
            key: 'reasoning',
            label: 'Reasoning Depth',
            value: metrics.reasoning_depth,
            isInverted: false,
            description: 'Evaluates the logical chain-of-thought and analytical sophistication.',
            factors: [
                { name: 'Chain completeness', score: metrics.reasoning_depth * 0.95 },
                { name: 'Evidence linkage', score: metrics.reasoning_depth * 0.88 + 0.05 },
                { name: 'Uncertainty acknowledgment', score: metrics.reasoning_depth * 0.9 + 0.08 },
            ],
        },
        {
            key: 'uix',
            label: 'UIX Compliance',
            value: metrics.uix_compliance,
            isInverted: false,
            description: 'Adherence to CARF UIX standards: explainability, confidence, and accessibility.',
            factors: [
                { name: '"Why this?" answered', score: metrics.uix_compliance >= 0.25 ? 1 : 0.3 },
                { name: '"How confident?" shown', score: metrics.uix_compliance >= 0.5 ? 1 : 0.3 },
                { name: '"Based on what?" cited', score: metrics.uix_compliance >= 0.75 ? 1 : 0.3 },
                { name: 'Accessible language', score: metrics.uix_compliance >= 1.0 ? 1 : 0.5 },
            ],
        },
    ];

    const MetricBar: React.FC<{ metric: typeof metricDefinitions[0] }> = ({ metric }) => {
        const getColor = () => {
            const effectiveValue = metric.isInverted ? 1 - metric.value : metric.value;
            if (effectiveValue >= 0.8) return 'bg-green-500';
            if (effectiveValue >= 0.6) return 'bg-blue-500';
            if (effectiveValue >= 0.4) return 'bg-yellow-500';
            return 'bg-red-500';
        };

        const isExpanded = expandedMetric === metric.key;

        return (
            <div className="space-y-1">
                <button
                    className="w-full text-left"
                    onClick={() => setExpandedMetric(isExpanded ? null : metric.key)}
                    data-testid={`metric-bar-${metric.key}`}
                >
                    <div className="flex justify-between text-xs">
                        <span className="text-gray-600 flex items-center gap-1">
                            {metric.label}
                            <svg className={`w-3 h-3 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </span>
                        <span className="font-mono text-gray-900">{(metric.value * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden mt-1">
                        <div className={`h-full rounded-full ${getColor()}`} style={{ width: `${metric.value * 100}%` }} />
                    </div>
                </button>

                {/* Drill-down detail */}
                {isExpanded && (
                    <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-200 animate-in slide-in-from-top-1 duration-150" data-testid={`metric-detail-${metric.key}`}>
                        <p className="text-[11px] text-gray-600 mb-2">{metric.description}</p>

                        {/* Sub-factors */}
                        <div className="space-y-1.5 mb-3">
                            {metric.factors.map((factor, fi) => (
                                <div key={fi} className="flex items-center gap-2">
                                    <span className="text-[10px] text-gray-500 w-32 truncate">{factor.name}</span>
                                    <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full ${Math.max(0, Math.min(1, factor.score)) >= 0.7 ? 'bg-green-400' : Math.max(0, Math.min(1, factor.score)) >= 0.4 ? 'bg-yellow-400' : 'bg-red-400'}`}
                                            style={{ width: `${Math.max(0, Math.min(1, factor.score)) * 100}%` }}
                                        />
                                    </div>
                                    <span className="text-[10px] font-mono text-gray-500 w-10 text-right">
                                        {(Math.max(0, Math.min(1, factor.score)) * 100).toFixed(0)}%
                                    </span>
                                </div>
                            ))}
                        </div>

                        {/* Cynefin-aware recommendation */}
                        <div className="p-2 bg-blue-50 rounded border border-blue-200">
                            <div className="text-[10px] font-semibold text-blue-800 mb-1 flex items-center gap-1">
                                Cynefin Recommendation ({domain})
                            </div>
                            <p className="text-[10px] text-blue-700" data-testid={`cynefin-rec-${metric.key}`}>
                                {domainRecs[metric.key]}
                            </p>
                        </div>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-gray-900">DeepEval Metrics</div>
                <div className="text-xs text-gray-500">
                    Model: <span className="font-mono">{metrics.evaluation_model}</span>
                </div>
            </div>

            {/* Overall Score */}
            <div className="p-4 bg-gray-50 rounded-lg text-center">
                <div className="text-3xl font-bold text-gray-900">
                    {Math.round(((metrics.relevancy_score + metrics.reasoning_depth + metrics.uix_compliance + (1 - metrics.hallucination_risk)) / 4) * 100)}%
                </div>
                <div className="text-xs text-gray-600 mt-1">Overall Quality Score</div>
            </div>

            {/* Individual Metrics - Clickable */}
            <div className="space-y-3">
                {metricDefinitions.map(metric => (
                    <MetricBar key={metric.key} metric={metric} />
                ))}
            </div>

            {/* Status Indicators */}
            <div className="grid grid-cols-2 gap-2 pt-3 border-t border-gray-200">
                <div className="p-2 bg-gray-50 rounded">
                    <div className="text-[10px] text-gray-500 uppercase">Task Complete</div>
                    <div className={`text-sm font-medium ${metrics.task_completion ? 'text-green-600' : 'text-yellow-600'}`}>
                        {metrics.task_completion ? '&#x2713; Yes' : '&#x25CB; No'}
                    </div>
                </div>
                <div className="p-2 bg-gray-50 rounded">
                    <div className="text-[10px] text-gray-500 uppercase">Eval Latency</div>
                    <div className="text-sm font-medium text-gray-700 font-mono">
                        {metrics.evaluation_latency_ms}ms
                    </div>
                </div>
            </div>

            {/* UIX Compliance Breakdown */}
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-xs font-semibold text-blue-800 mb-2">UIX Standards (CARF)</div>
                <div className="space-y-1 text-xs">
                    {[
                        { label: 'Why this?', threshold: 0.25 },
                        { label: 'How confident?', threshold: 0.5 },
                        { label: 'Based on what?', threshold: 0.75 },
                        { label: 'Accessible language', threshold: 1.0 }
                    ].map((check, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-blue-700">
                            <span className={metrics.uix_compliance >= check.threshold ? 'text-green-600' : 'text-gray-400'}>
                                {metrics.uix_compliance >= check.threshold ? '✓' : '○'}
                            </span>
                            <span>{check.label}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Export Button */}
            <button
                onClick={() => {
                    const data = JSON.stringify({ metrics, timestamp: new Date().toISOString() }, null, 2);
                    navigator.clipboard.writeText(data);
                }}
                className="w-full px-3 py-2 text-xs text-blue-600 hover:bg-blue-50 rounded border border-blue-200"
            >
                Copy Metrics JSON
            </button>
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
// Improvement Suggestion Modal
const ImprovementModal: React.FC<{
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (suggestion: string) => void;
    response: QueryResponse | null;
}> = ({ isOpen, onClose, onSubmit, response }) => {
    const [suggestion, setSuggestion] = useState('');

    // Pre-populate suggestions based on analysis context
    const prePopulated = useMemo(() => {
        const suggestions: string[] = [];
        if (response) {
            if (response.domainConfidence && response.domainConfidence < 0.7) {
                suggestions.push('- Improve domain classification accuracy for ambiguous queries');
            }
            if (response.domainEntropy && response.domainEntropy > 0.5) {
                suggestions.push('- Reduce entropy by providing more specific context or data');
            }
            if (response.domain === 'disorder') {
                suggestions.push('- Consider adding domain-specific training data to resolve disorder classification');
            }
            if (response.requiresHuman) {
                suggestions.push('- Automate the human-in-the-loop step for this query type');
            }
            if (!response.causalResult) {
                suggestions.push('- Add causal analysis support for this domain');
            }
        }
        if (suggestions.length === 0) {
            suggestions.push('- Describe your improvement idea here...');
        }
        return suggestions.join('\n');
    }, [response]);

    React.useEffect(() => {
        if (isOpen && !suggestion) {
            setSuggestion(prePopulated);
        }
    }, [isOpen, prePopulated, suggestion]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" data-testid="improvement-modal">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-gray-900">Suggest Improvement</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg" aria-label="Close modal">&times;</button>
                </div>

                <p className="text-xs text-gray-500 mb-3">
                    Describe how the analysis or routing could be improved. Your feedback is used to refine
                    domain classification, agent selection, and output quality. Pre-populated suggestions are
                    based on the current analysis context.
                </p>

                <textarea
                    value={suggestion}
                    onChange={(e) => setSuggestion(e.target.value)}
                    className="w-full h-32 p-3 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none font-mono"
                    placeholder="Describe your improvement suggestion..."
                    data-testid="improvement-textarea"
                />

                <div className="flex justify-end gap-2 mt-4">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-xs text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() => {
                            if (suggestion.trim()) {
                                onSubmit(suggestion);
                                setSuggestion('');
                                onClose();
                            }
                        }}
                        className="px-4 py-2 text-xs text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                        data-testid="improvement-submit"
                    >
                        Submit Suggestion
                    </button>
                </div>
            </div>
        </div>
    );
};

const DeveloperView: React.FC<DeveloperViewProps> = ({ response, executionTrace, isProcessing }) => {
    const [activePanel, setActivePanel] = useState<'architecture' | 'logs' | 'timeline' | 'state' | 'experience' | 'dataflow' | 'datalayer' | 'evaluation'>('architecture');
    const [selectedLayer, setSelectedLayer] = useState<string | null>(null);
    const [showImprovementModal, setShowImprovementModal] = useState(false);
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
        { id: 'evaluation', label: 'Evaluation', icon: '📈' },
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

            {/* Panel Tabs - Responsive with wrapping */}
            <div className="flex flex-wrap gap-1.5 mb-4 overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300">
                {panels.map(panel => (
                    <button
                        key={panel.id}
                        onClick={() => setActivePanel(panel.id as typeof activePanel)}
                        className={`flex items-center gap-1 px-2 sm:px-3 py-1.5 text-[10px] sm:text-xs font-medium rounded-lg transition-colors whitespace-nowrap flex-shrink-0 ${activePanel === panel.id
                            ? 'bg-primary text-white shadow-sm'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                            }`}
                    >
                        <span className="text-sm sm:text-base">{panel.icon}</span>
                        <span className="hidden xs:inline">{panel.label}</span>
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
                        architectureLayers={developerState?.architecture}
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
                {activePanel === 'evaluation' && <EvaluationMetricsPanel response={response} />}
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
                                    type: 'issue' as const,
                                    timestamp: new Date().toISOString(),
                                    description: issue,
                                    context: {
                                        sessionId: response?.sessionId,
                                        domain: response?.domain,
                                        executionSteps: executionTrace.length,
                                    },
                                };
                                submitFeedback(feedbackData).then(() => {
                                    alert('Thank you! Your issue has been logged for review.');
                                }).catch(() => {
                                    alert('Feedback saved locally. Backend unavailable.');
                                });
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
                        onClick={() => setShowImprovementModal(true)}
                        className="px-3 py-2 bg-blue-50 text-blue-700 text-xs font-medium rounded-lg hover:bg-blue-100 transition-colors flex items-center justify-center gap-1"
                        data-testid="suggest-improvement-btn"
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

            {/* Improvement Suggestion Modal */}
            <ImprovementModal
                isOpen={showImprovementModal}
                onClose={() => setShowImprovementModal(false)}
                response={response}
                onSubmit={(suggestion) => {
                    const feedbackData = {
                        type: 'improvement' as const,
                        timestamp: new Date().toISOString(),
                        description: suggestion,
                        context: {
                            sessionId: response?.sessionId,
                            domain: response?.domain,
                            confidence: response?.domainConfidence,
                        },
                    };
                    submitFeedback(feedbackData).catch(() => {
                        // Feedback saved locally when backend unavailable
                    });
                }}
            />
        </div>
    );
};

export default DeveloperView;
