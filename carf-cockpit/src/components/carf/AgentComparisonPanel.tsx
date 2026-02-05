/**
 * AgentComparisonPanel Component
 *
 * Provides LLM/Agent workflow transparency with:
 * - Agent performance comparison
 * - Cost/latency/quality tradeoffs visualization
 * - Historical performance trends
 * - Execution trace view
 */

import React, { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface AgentStats {
    agent_id: string;
    agent_name: string;
    total_executions: number;
    successful_executions: number;
    failed_executions: number;
    success_rate: number;
    average_latency_ms: number;
    average_quality_score: number | null;
    total_tokens_used: number;
    total_cost_usd: number;
    last_execution: string | null;
}

interface WorkflowTrace {
    trace_id: string;
    session_id: string;
    workflow_name: string;
    domain: string | null;
    started_at: string;
    completed_at: string | null;
    total_latency_ms: number;
    executions_count: number;
}

interface AgentComparisonPanelProps {
    sessionId?: string;
    className?: string;
}

const AgentComparisonPanel: React.FC<AgentComparisonPanelProps> = ({
    sessionId,
    className = '',
}) => {
    const [agents, setAgents] = useState<AgentStats[]>([]);
    const [recentTraces, setRecentTraces] = useState<WorkflowTrace[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'agents' | 'traces' | 'costs'>('agents');
    const [sortBy, setSortBy] = useState<'latency' | 'quality' | 'cost' | 'executions'>('executions');
    const [selectedTrace, setSelectedTrace] = useState<string | null>(null);
    const [traceDetails, setTraceDetails] = useState<any | null>(null);

    // Fetch agent comparison data
    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                // Fetch agent stats
                const statsRes = await fetch(`${API_BASE_URL}/agents/stats`);
                if (statsRes.ok) {
                    const data = await statsRes.json();
                    setAgents(data.agents || []);
                }

                // Fetch recent traces
                const tracesRes = await fetch(`${API_BASE_URL}/workflow/recent?limit=10`);
                if (tracesRes.ok) {
                    const data = await tracesRes.json();
                    setRecentTraces(data.traces || []);
                }
            } catch (err) {
                console.error('Failed to fetch agent data:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        // Refresh every 30 seconds
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    // Fetch trace details when selected
    useEffect(() => {
        if (!selectedTrace) {
            setTraceDetails(null);
            return;
        }

        const fetchTraceDetails = async () => {
            try {
                const res = await fetch(`${API_BASE_URL}/workflow/trace/${selectedTrace}`);
                if (res.ok) {
                    const data = await res.json();
                    setTraceDetails(data);
                }
            } catch (err) {
                console.error('Failed to fetch trace details:', err);
            }
        };

        fetchTraceDetails();
    }, [selectedTrace]);

    // Sort agents based on selected criteria
    const sortedAgents = [...agents].sort((a, b) => {
        switch (sortBy) {
            case 'latency':
                return a.average_latency_ms - b.average_latency_ms;
            case 'quality':
                return (b.average_quality_score || 0) - (a.average_quality_score || 0);
            case 'cost':
                return a.total_cost_usd - b.total_cost_usd;
            case 'executions':
            default:
                return b.total_executions - a.total_executions;
        }
    });

    // Calculate totals
    const totalExecutions = agents.reduce((sum, a) => sum + a.total_executions, 0);
    const totalTokens = agents.reduce((sum, a) => sum + a.total_tokens_used, 0);
    const totalCost = agents.reduce((sum, a) => sum + a.total_cost_usd, 0);
    const avgLatency = agents.length > 0
        ? agents.reduce((sum, a) => sum + a.average_latency_ms, 0) / agents.length
        : 0;

    const getStatusColor = (rate: number) => {
        if (rate >= 0.95) return 'text-green-600 dark:text-green-400';
        if (rate >= 0.8) return 'text-blue-600 dark:text-blue-400';
        if (rate >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
        return 'text-red-600 dark:text-red-400';
    };

    const getLatencyColor = (ms: number) => {
        if (ms < 500) return 'bg-green-500';
        if (ms < 1000) return 'bg-blue-500';
        if (ms < 2000) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    if (loading) {
        return (
            <div className={`p-6 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 ${className}`}>
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
                </div>
            </div>
        );
    }

    return (
        <div className={`bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 ${className}`}>
            {/* Header */}
            <div className="p-4 border-b border-gray-200 dark:border-slate-700">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-900 dark:text-slate-100 flex items-center gap-2">
                        <span>🤖</span>
                        Agent Performance
                    </h3>
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 dark:text-slate-400">
                            {totalExecutions} total executions
                        </span>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex gap-1 bg-gray-100 dark:bg-slate-700 rounded-lg p-1">
                    {(['agents', 'traces', 'costs'] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                                activeTab === tab
                                    ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-slate-100 shadow-sm'
                                    : 'text-gray-600 dark:text-slate-400 hover:text-gray-900 dark:hover:text-slate-200'
                            }`}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-4 gap-4 p-4 border-b border-gray-200 dark:border-slate-700">
                <div className="text-center">
                    <div className="text-xl font-bold text-gray-900 dark:text-slate-100">
                        {agents.length}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-slate-400">Agents</div>
                </div>
                <div className="text-center">
                    <div className="text-xl font-bold text-gray-900 dark:text-slate-100">
                        {avgLatency.toFixed(0)}ms
                    </div>
                    <div className="text-xs text-gray-500 dark:text-slate-400">Avg Latency</div>
                </div>
                <div className="text-center">
                    <div className="text-xl font-bold text-gray-900 dark:text-slate-100">
                        {(totalTokens / 1000).toFixed(1)}k
                    </div>
                    <div className="text-xs text-gray-500 dark:text-slate-400">Tokens</div>
                </div>
                <div className="text-center">
                    <div className="text-xl font-bold text-gray-900 dark:text-slate-100">
                        ${totalCost.toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-slate-400">Total Cost</div>
                </div>
            </div>

            {/* Content */}
            <div className="p-4">
                {/* Agents Tab */}
                {activeTab === 'agents' && (
                    <div className="space-y-4">
                        {/* Sort Controls */}
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-500 dark:text-slate-400">Sort by:</span>
                            {(['executions', 'latency', 'quality', 'cost'] as const).map(option => (
                                <button
                                    key={option}
                                    onClick={() => setSortBy(option)}
                                    className={`px-2 py-1 text-xs rounded transition-colors capitalize ${
                                        sortBy === option
                                            ? 'bg-primary text-white'
                                            : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-600'
                                    }`}
                                >
                                    {option}
                                </button>
                            ))}
                        </div>

                        {/* Agent List */}
                        <div className="space-y-2">
                            {sortedAgents.length === 0 ? (
                                <div className="text-center py-8 text-gray-500 dark:text-slate-400">
                                    <span className="text-2xl block mb-2">📊</span>
                                    <p className="text-sm">No agent data available yet</p>
                                </div>
                            ) : (
                                sortedAgents.map(agent => (
                                    <div
                                        key={agent.agent_id}
                                        className="p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-200 dark:border-slate-600"
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="font-medium text-gray-900 dark:text-slate-100 text-sm">
                                                {agent.agent_name}
                                            </div>
                                            <div className={`text-sm font-medium ${getStatusColor(agent.success_rate)}`}>
                                                {(agent.success_rate * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                        <div className="grid grid-cols-4 gap-2 text-xs">
                                            <div>
                                                <span className="text-gray-500 dark:text-slate-400">Runs:</span>
                                                <span className="ml-1 text-gray-700 dark:text-slate-300">{agent.total_executions}</span>
                                            </div>
                                            <div>
                                                <span className="text-gray-500 dark:text-slate-400">Latency:</span>
                                                <span className="ml-1 text-gray-700 dark:text-slate-300">{agent.average_latency_ms.toFixed(0)}ms</span>
                                            </div>
                                            <div>
                                                <span className="text-gray-500 dark:text-slate-400">Quality:</span>
                                                <span className="ml-1 text-gray-700 dark:text-slate-300">
                                                    {agent.average_quality_score != null ? `${(agent.average_quality_score * 100).toFixed(0)}%` : 'N/A'}
                                                </span>
                                            </div>
                                            <div>
                                                <span className="text-gray-500 dark:text-slate-400">Cost:</span>
                                                <span className="ml-1 text-gray-700 dark:text-slate-300">${agent.total_cost_usd.toFixed(3)}</span>
                                            </div>
                                        </div>
                                        {/* Latency Bar */}
                                        <div className="mt-2 h-1.5 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full ${getLatencyColor(agent.average_latency_ms)}`}
                                                style={{ width: `${Math.min((agent.average_latency_ms / 3000) * 100, 100)}%` }}
                                            />
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {/* Traces Tab */}
                {activeTab === 'traces' && (
                    <div className="space-y-3">
                        {recentTraces.length === 0 ? (
                            <div className="text-center py-8 text-gray-500 dark:text-slate-400">
                                <span className="text-2xl block mb-2">📜</span>
                                <p className="text-sm">No workflow traces available</p>
                            </div>
                        ) : (
                            recentTraces.map(trace => (
                                <div
                                    key={trace.trace_id}
                                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                                        selectedTrace === trace.trace_id
                                            ? 'bg-primary/10 border-primary dark:bg-primary/20'
                                            : 'bg-gray-50 dark:bg-slate-700/50 border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500'
                                    }`}
                                    onClick={() => setSelectedTrace(selectedTrace === trace.trace_id ? null : trace.trace_id)}
                                >
                                    <div className="flex items-center justify-between mb-1">
                                        <div className="font-medium text-gray-900 dark:text-slate-100 text-sm">
                                            {trace.workflow_name}
                                        </div>
                                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                                            trace.completed_at
                                                ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                                                : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300'
                                        }`}>
                                            {trace.completed_at ? 'Complete' : 'In Progress'}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-slate-400">
                                        <span>{trace.domain || 'Unknown domain'}</span>
                                        <span>{trace.executions_count} agents</span>
                                        <span>{trace.total_latency_ms}ms</span>
                                        <span>{new Date(trace.started_at).toLocaleTimeString()}</span>
                                    </div>

                                    {/* Expanded Trace Details */}
                                    {selectedTrace === trace.trace_id && traceDetails && (
                                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-slate-600">
                                            <div className="text-xs font-medium text-gray-700 dark:text-slate-300 mb-2">
                                                Execution Timeline:
                                            </div>
                                            <div className="space-y-1">
                                                {traceDetails.executions?.map((exec: any, idx: number) => (
                                                    <div key={exec.execution_id || idx} className="flex items-center gap-2 text-xs">
                                                        <span className={`w-2 h-2 rounded-full ${
                                                            exec.status === 'completed' ? 'bg-green-500' :
                                                            exec.status === 'failed' ? 'bg-red-500' : 'bg-yellow-500'
                                                        }`} />
                                                        <span className="text-gray-700 dark:text-slate-300">{exec.agent_name}</span>
                                                        <span className="text-gray-400 dark:text-slate-500 ml-auto">{exec.latency_ms}ms</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                )}

                {/* Costs Tab */}
                {activeTab === 'costs' && (
                    <div className="space-y-4">
                        <div className="p-4 bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/30 dark:to-purple-900/30 rounded-lg border border-blue-200 dark:border-blue-700">
                            <div className="text-center">
                                <div className="text-3xl font-bold text-gray-900 dark:text-slate-100">
                                    ${totalCost.toFixed(4)}
                                </div>
                                <div className="text-sm text-gray-500 dark:text-slate-400 mt-1">
                                    Total API Cost
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4 mt-4">
                                <div className="text-center">
                                    <div className="text-lg font-semibold text-gray-700 dark:text-slate-300">
                                        {(totalTokens / 1000).toFixed(1)}k
                                    </div>
                                    <div className="text-xs text-gray-500 dark:text-slate-400">Total Tokens</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-lg font-semibold text-gray-700 dark:text-slate-300">
                                        ${totalExecutions > 0 ? (totalCost / totalExecutions).toFixed(4) : '0.00'}
                                    </div>
                                    <div className="text-xs text-gray-500 dark:text-slate-400">Avg per Run</div>
                                </div>
                            </div>
                        </div>

                        {/* Cost Breakdown by Agent */}
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-gray-700 dark:text-slate-300">Cost by Agent:</div>
                            {sortedAgents
                                .filter(a => a.total_cost_usd > 0)
                                .sort((a, b) => b.total_cost_usd - a.total_cost_usd)
                                .map(agent => (
                                    <div key={agent.agent_id} className="flex items-center gap-2">
                                        <span className="text-xs text-gray-600 dark:text-slate-400 w-32 truncate">
                                            {agent.agent_name}
                                        </span>
                                        <div className="flex-1 h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-primary"
                                                style={{ width: `${totalCost > 0 ? (agent.total_cost_usd / totalCost) * 100 : 0}%` }}
                                            />
                                        </div>
                                        <span className="text-xs text-gray-700 dark:text-slate-300 w-16 text-right">
                                            ${agent.total_cost_usd.toFixed(3)}
                                        </span>
                                    </div>
                                ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AgentComparisonPanel;
