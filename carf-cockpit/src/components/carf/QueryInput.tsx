import React, { useState } from 'react';
import type { KeyboardEvent, ChangeEvent } from 'react';

interface QueryInputProps {
    onSubmit: (query: string) => void;
    suggestedQueries: string[];
    isProcessing?: boolean;
}

const QueryInput: React.FC<QueryInputProps> = ({
    onSubmit,
    suggestedQueries,
    isProcessing = false,
}) => {
    const [query, setQuery] = useState<string>('');

    const handleSubmit = () => {
        if (query.trim() && !isProcessing) {
            onSubmit(query);
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const handleSuggestionClick = (suggestion: string) => {
        setQuery(suggestion);
    };

    const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
        const value = e.target.value;
        if (value.length <= 2000) {
            setQuery(value);
        }
    };

    return (
        <div className="space-y-3">
            <div className="relative">
                <textarea
                    value={query}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask a question about your data..."
                    disabled={isProcessing}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-sm"
                    rows={4}
                    style={{ minHeight: '100px', maxHeight: '300px' }}
                />
                <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                    {query.length}/2000
                </div>
            </div>

            <div className="flex gap-2">
                <button
                    onClick={() => setQuery('')}
                    disabled={!query || isProcessing}
                    className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    Clear
                </button>
                <button
                    onClick={handleSubmit}
                    disabled={!query.trim() || isProcessing}
                    className="flex-1 px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary-light disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                    {isProcessing ? (
                        <>
                            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Analyzing...
                        </>
                    ) : (
                        <>
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            Send
                        </>
                    )}
                </button>
            </div>

            {suggestedQueries.length > 0 && (
                <div className="space-y-2">
                    <p className="text-xs font-medium text-gray-700">SUGGESTED QUERIES</p>
                    <div className="flex flex-wrap gap-2">
                        {suggestedQueries.map((suggestion, idx) => (
                            <button
                                key={idx}
                                onClick={() => handleSuggestionClick(suggestion)}
                                disabled={isProcessing}
                                className="badge bg-primary/10 text-primary hover:bg-primary/20 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {suggestion}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default QueryInput;
