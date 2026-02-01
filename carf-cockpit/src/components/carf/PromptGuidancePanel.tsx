import React from 'react';

export interface Suggestion {
    id: string;
    type: 'prompt_refinement' | 'next_step' | 'methodology';
    text: string;
    action_payload?: string;
}

interface PromptGuidancePanelProps {
    suggestions: Suggestion[];
    onApplySuggestion: (suggestion: Suggestion) => void;
    isLoading?: boolean;
}

const PromptGuidancePanel: React.FC<PromptGuidancePanelProps> = ({
    suggestions,
    onApplySuggestion,
    isLoading = false
}) => {
    const actionableSuggestions = suggestions.filter((suggestion) => Boolean(suggestion.action_payload));

    if (isLoading) {
        return (
            <div className="animate-pulse space-y-2 p-4 bg-white rounded-lg shadow-sm border border-gray-100">
                <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                <div className="h-10 bg-gray-100 rounded"></div>
            </div>
        );
    }

    if (actionableSuggestions.length === 0) return null;

    return (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-lg p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">✨</span>
                <h3 className="text-sm font-semibold text-blue-900">AI Suggestions</h3>
            </div>

            <div className="space-y-2">
                {actionableSuggestions.map((suggestion) => (
                    <button
                        key={suggestion.id}
                        onClick={() => onApplySuggestion(suggestion)}
                        className="w-full flex items-center justify-between p-3 bg-white hover:bg-blue-50 border border-blue-100 hover:border-blue-200 rounded-md transition-all group text-left"
                    >
                        <div className="flex flex-col">
                            <span className="text-sm font-medium text-gray-800">{suggestion.text}</span>
                            {suggestion.type === 'methodology' && (
                                <span className="text-xs text-purple-600 mt-0.5">Methodology Change</span>
                            )}
                        </div>
                        <span className="text-blue-400 group-hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
                            Apply →
                        </span>
                    </button>
                ))}
            </div>

            <div className="mt-3 flex justify-end">
                <span className="text-[10px] text-blue-400 font-medium">Powered by CARF Agent</span>
            </div>
        </div>
    );
};

export default PromptGuidancePanel;
