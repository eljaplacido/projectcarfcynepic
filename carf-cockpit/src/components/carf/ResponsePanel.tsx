import React from 'react';
import type { QueryResponse } from '../../types/carf';

interface ResponsePanelProps {
    response: QueryResponse | null;
}

const ResponsePanel: React.FC<ResponsePanelProps> = ({ response }) => {
    if (!response || !response.response) {
        return (
            <div className="text-sm text-gray-500 italic">
                Response summary will appear here after analysis completes
            </div>
        );
    }

    const getConfidenceColor = (conf: number): string => {
        if (conf >= 0.8) return 'bg-confidence-high';
        if (conf >= 0.5) return 'bg-confidence-medium';
        return 'bg-confidence-low';
    };

    return (
        <div className="space-y-4">
            {/* Confidence Badge */}
            <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-900">Analysis Complete</span>
                <span className={`badge ${getConfidenceColor(response.domainConfidence)} text-white`}>
                    {Math.round(response.domainConfidence * 100)}% Confident
                </span>
            </div>

            {/* Main Response */}
            <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="text-sm text-gray-900 leading-relaxed whitespace-pre-wrap">
                    {response.response}
                </div>
            </div>

            {/* Key Insights */}
            {response.keyInsights && response.keyInsights.length > 0 && (
                <div>
                    <div className="text-sm font-semibold text-gray-900 mb-2">💡 Key Insights</div>
                    <ul className="space-y-2">
                        {response.keyInsights.map((insight, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                                <span className="text-primary mt-0.5">•</span>
                                <span>{insight}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Next Steps */}
            {response.nextSteps && response.nextSteps.length > 0 && (
                <div>
                    <div className="text-sm font-semibold text-gray-900 mb-2">→ Next Steps</div>
                    <ul className="space-y-2">
                        {response.nextSteps.map((step, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                                <span className="text-accent mt-0.5">→</span>
                                <span>{step}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Error Display */}
            {response.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded">
                    <div className="text-sm font-semibold text-red-900 mb-1">⚠️ Error</div>
                    <div className="text-sm text-red-700">{response.error}</div>
                </div>
            )}
        </div>
    );
};

export default ResponsePanel;
