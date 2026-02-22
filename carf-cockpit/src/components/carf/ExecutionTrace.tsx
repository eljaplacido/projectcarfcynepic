import React from 'react';
import type { ReasoningStep } from '../../types/carf';

interface ExecutionTraceProps {
    steps: ReasoningStep[];
    sessionId: string;
}

const ExecutionTrace: React.FC<ExecutionTraceProps> = ({ steps, sessionId }) => {
    if (steps.length === 0) {
        return (
            <div className="text-sm text-gray-500 italic">
                Execution trace will appear here after query processing
            </div>
        );
    }

    const getStatusIcon = (status?: string) => {
        switch (status) {
            case 'completed': return <span className="text-green-500">✓</span>;
            case 'in_progress': return <span className="text-blue-500 animate-spin">↻</span>;
            case 'pending': return <span className="text-gray-400">○</span>;
            default: return <span className="text-green-500">✓</span>;
        }
    };

    const handleExport = () => {
        const data = { sessionId, steps };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `carf-trace-${sessionId}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="space-y-4">
            {/* Session ID */}
            <div className="flex items-center justify-between">
                <div>
                    <div className="text-xs text-gray-500">Session ID</div>
                    <div className="text-sm font-mono text-gray-900">{sessionId.slice(0, 20)}...</div>
                </div>
                <button
                    onClick={handleExport}
                    className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                >
                    Export JSON
                </button>
            </div>

            {/* Timeline */}
            <div className="relative">
                <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200"></div>
                <div className="space-y-4">
                    {steps.map((step, idx) => (
                        <div key={idx} className="relative pl-10">
                            <div className="absolute left-2 top-1 w-4 h-4 bg-white border-2 border-primary rounded-full flex items-center justify-center">
                                {getStatusIcon(step.status)}
                            </div>
                            <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-sm font-semibold text-gray-900">{step.node}</span>
                                    <span className="text-xs text-gray-500">
                                        {step.durationMs > 0 ? `${step.durationMs}ms` : '< 1ms'}
                                    </span>
                                </div>
                                <div className="text-sm text-gray-700">{step.action}</div>
                                <div className="flex items-center gap-2 mt-2">
                                    <span
                                        className={`badge text-xs ${step.confidence === 'high' ? 'bg-confidence-high text-white' :
                                            step.confidence === 'medium' ? 'bg-confidence-medium text-white' :
                                                'bg-confidence-low text-white'
                                            }`}
                                        title={
                                            step.confidence === 'high'
                                                ? 'High confidence: Strong evidence supports this step. The result is well-validated and reliable.'
                                                : step.confidence === 'medium'
                                                    ? 'Medium confidence: Moderate evidence. The result is reasonable but may benefit from additional validation.'
                                                    : 'Low confidence: Limited evidence. Treat this result with caution and consider gathering more data.'
                                        }
                                    >
                                        {step.confidence}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default ExecutionTrace;
