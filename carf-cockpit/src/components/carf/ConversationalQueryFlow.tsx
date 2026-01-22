import React, { useState, useCallback } from 'react';

interface ConversationStep {
    id: string;
    type: 'question' | 'user-input' | 'option-select' | 'confirmation';
    question: string;
    options?: { id: string; label: string; description?: string }[];
    answer?: string;
    completed: boolean;
}

interface QueryContext {
    dataset: string | null;
    treatment: string | null;
    outcome: string | null;
    confounders: string[];
    hypothesis: string | null;
    constraints: string[];
}

interface ConversationalQueryFlowProps {
    onSubmitQuery: (query: string, context: QueryContext) => void;
    suggestedQueries?: string[];
    hasDataset?: boolean;
    datasetName?: string;
    availableVariables?: string[];
    isProcessing?: boolean;
}

const ConversationalQueryFlow: React.FC<ConversationalQueryFlowProps> = ({
    onSubmitQuery,
    suggestedQueries = [],
    hasDataset = false,
    datasetName,
    availableVariables = [],
    isProcessing = false,
}) => {
    const [mode, setMode] = useState<'quick' | 'guided' | null>(null);
    const [quickQuery, setQuickQuery] = useState('');
    const [currentStep, setCurrentStep] = useState(0);
    const [context, setContext] = useState<QueryContext>({
        dataset: datasetName || null,
        treatment: null,
        outcome: null,
        confounders: [],
        hypothesis: null,
        constraints: [],
    });

    const [conversationHistory, setConversationHistory] = useState<ConversationStep[]>([]);

    // Guided flow steps
    const guidedSteps: Omit<ConversationStep, 'answer' | 'completed'>[] = [
        {
            id: 'data-source',
            type: 'option-select',
            question: "First, let me understand your data context. Which data source should I analyze?",
            options: hasDataset
                ? [
                    { id: 'current', label: `Use ${datasetName || 'loaded dataset'}`, description: 'Analyze the currently loaded data' },
                    { id: 'upload', label: 'Upload new data', description: 'Start fresh with a new dataset' },
                    { id: 'demo', label: 'Use demo scenario', description: 'Try with sample data' },
                ]
                : [
                    { id: 'upload', label: 'Upload your data', description: 'CSV, JSON, or connect to database' },
                    { id: 'demo', label: 'Use demo scenario', description: 'Try with sample data first' },
                ],
        },
        {
            id: 'main-question',
            type: 'user-input',
            question: "What question do you want to answer? Try to phrase it as a causal question (e.g., 'Does X cause Y?')",
        },
        {
            id: 'treatment',
            type: availableVariables.length > 0 ? 'option-select' : 'user-input',
            question: "What is the treatment or intervention you want to study? (The variable you can change)",
            options: availableVariables.length > 0
                ? availableVariables.slice(0, 6).map(v => ({ id: v, label: v }))
                : undefined,
        },
        {
            id: 'outcome',
            type: availableVariables.length > 0 ? 'option-select' : 'user-input',
            question: "What outcome are you trying to affect? (The variable you want to measure)",
            options: availableVariables.length > 0
                ? availableVariables.slice(0, 6).map(v => ({ id: v, label: v }))
                : undefined,
        },
        {
            id: 'confounders',
            type: 'user-input',
            question: "Are there any known confounders? (Variables that might affect both treatment and outcome)\n\nList them separated by commas, or type 'none' if unsure.",
        },
        {
            id: 'confirmation',
            type: 'confirmation',
            question: "Here's your analysis setup. Ready to run?",
        },
    ];

    const handleQuickSubmit = useCallback(() => {
        if (quickQuery.trim() && !isProcessing) {
            onSubmitQuery(quickQuery.trim(), context);
        }
    }, [quickQuery, context, onSubmitQuery, isProcessing]);

    const handleSuggestionClick = (suggestion: string) => {
        setQuickQuery(suggestion);
    };

    const handleGuidedAnswer = useCallback((answer: string) => {
        const step = guidedSteps[currentStep];

        // Update conversation history
        setConversationHistory(prev => [
            ...prev,
            { ...step, answer, completed: true },
        ]);

        // Update context based on step
        switch (step.id) {
            case 'data-source':
                setContext(prev => ({ ...prev, dataset: answer }));
                break;
            case 'main-question':
                setContext(prev => ({ ...prev, hypothesis: answer }));
                break;
            case 'treatment':
                setContext(prev => ({ ...prev, treatment: answer }));
                break;
            case 'outcome':
                setContext(prev => ({ ...prev, outcome: answer }));
                break;
            case 'confounders':
                if (answer.toLowerCase() !== 'none') {
                    const confounders = answer.split(',').map(c => c.trim()).filter(Boolean);
                    setContext(prev => ({ ...prev, confounders }));
                }
                break;
        }

        // Move to next step or submit
        if (currentStep < guidedSteps.length - 1) {
            setCurrentStep(prev => prev + 1);
        } else {
            // Final step - submit query
            const finalQuery = context.hypothesis || '';
            onSubmitQuery(finalQuery, context);
        }
    }, [currentStep, guidedSteps, context, onSubmitQuery]);

    const handleConfirmation = (confirmed: boolean) => {
        if (confirmed) {
            const finalQuery = context.hypothesis || '';
            onSubmitQuery(finalQuery, context);
        } else {
            // Reset to start of guided flow
            setCurrentStep(0);
            setConversationHistory([]);
            setContext({
                dataset: datasetName || null,
                treatment: null,
                outcome: null,
                confounders: [],
                hypothesis: null,
                constraints: [],
            });
        }
    };

    const resetFlow = () => {
        setMode(null);
        setQuickQuery('');
        setCurrentStep(0);
        setConversationHistory([]);
        setContext({
            dataset: datasetName || null,
            treatment: null,
            outcome: null,
            confounders: [],
            hypothesis: null,
            constraints: [],
        });
    };

    // Mode selection view
    if (mode === null) {
        return (
            <div className="space-y-4">
                <div className="flex items-center gap-2 mb-2">
                    <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <span className="text-sm font-medium text-gray-700">What would you like to analyze?</span>
                </div>

                {/* Quick mode option */}
                <button
                    onClick={() => setMode('quick')}
                    className="w-full p-4 border border-gray-200 rounded-xl hover:border-primary hover:bg-primary/5 transition-all text-left group"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <div>
                            <div className="font-medium text-gray-900">Quick Query</div>
                            <div className="text-xs text-gray-500">Type your question directly</div>
                        </div>
                    </div>
                </button>

                {/* Guided mode option */}
                <button
                    onClick={() => setMode('guided')}
                    className="w-full p-4 border border-gray-200 rounded-xl hover:border-primary hover:bg-primary/5 transition-all text-left group"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center group-hover:bg-purple-200 transition-colors">
                            <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                            </svg>
                        </div>
                        <div>
                            <div className="font-medium text-gray-900">Guided Setup</div>
                            <div className="text-xs text-gray-500">Step-by-step query builder</div>
                        </div>
                    </div>
                </button>

                {/* Suggested queries */}
                {suggestedQueries.length > 0 && (
                    <div className="pt-2">
                        <div className="text-xs text-gray-500 mb-2">Or try a suggested query:</div>
                        <div className="space-y-2">
                            {suggestedQueries.slice(0, 3).map((query, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => {
                                        setMode('quick');
                                        setQuickQuery(query);
                                    }}
                                    className="w-full text-left text-sm px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-gray-700 transition-colors"
                                >
                                    {query}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    }

    // Quick mode view
    if (mode === 'quick') {
        return (
            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">Quick Query</span>
                    <button
                        onClick={resetFlow}
                        className="text-xs text-gray-500 hover:text-gray-700"
                    >
                        Change mode
                    </button>
                </div>

                <div className="relative">
                    <textarea
                        value={quickQuery}
                        onChange={(e) => setQuickQuery(e.target.value)}
                        placeholder="Ask a question about your data..."
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                        rows={3}
                        disabled={isProcessing}
                    />
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={handleQuickSubmit}
                        disabled={!quickQuery.trim() || isProcessing}
                        className="flex-grow px-4 py-2 bg-gradient-to-r from-primary to-accent text-white rounded-xl font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        {isProcessing ? (
                            <span className="flex items-center justify-center gap-2">
                                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Analyzing...
                            </span>
                        ) : (
                            'Analyze'
                        )}
                    </button>
                </div>

                {/* Quick suggestions */}
                {suggestedQueries.length > 0 && !quickQuery && (
                    <div className="pt-1">
                        <div className="text-xs text-gray-500 mb-2">Suggested:</div>
                        <div className="flex flex-wrap gap-2">
                            {suggestedQueries.slice(0, 3).map((query, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => handleSuggestionClick(query)}
                                    className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-600 transition-colors"
                                >
                                    {query.length > 40 ? query.slice(0, 40) + '...' : query}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    }

    // Guided mode view
    const currentGuidedStep = guidedSteps[currentStep];

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Guided Setup</span>
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                        Step {currentStep + 1} of {guidedSteps.length}
                    </span>
                </div>
                <button
                    onClick={resetFlow}
                    className="text-xs text-gray-500 hover:text-gray-700"
                >
                    Start over
                </button>
            </div>

            {/* Progress bar */}
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-300"
                    style={{ width: `${((currentStep + 1) / guidedSteps.length) * 100}%` }}
                />
            </div>

            {/* Conversation history */}
            {conversationHistory.length > 0 && (
                <div className="space-y-2 max-h-32 overflow-y-auto">
                    {conversationHistory.map((step, idx) => (
                        <div key={idx} className="text-xs">
                            <div className="text-gray-500">{step.question.split('\n')[0]}</div>
                            <div className="text-gray-900 font-medium">{step.answer}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* Current step */}
            <div className="bg-gray-50 rounded-xl p-4">
                <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <div className="flex-grow">
                        <p className="text-sm text-gray-700 whitespace-pre-line">
                            {currentGuidedStep.question}
                        </p>

                        {/* Render input based on step type */}
                        {currentGuidedStep.type === 'option-select' && currentGuidedStep.options && (
                            <div className="mt-3 space-y-2">
                                {currentGuidedStep.options.map(option => (
                                    <button
                                        key={option.id}
                                        onClick={() => handleGuidedAnswer(option.id)}
                                        className="w-full text-left p-3 border border-gray-200 rounded-lg hover:border-primary hover:bg-primary/5 transition-all"
                                    >
                                        <div className="text-sm font-medium text-gray-900">{option.label}</div>
                                        {option.description && (
                                            <div className="text-xs text-gray-500 mt-0.5">{option.description}</div>
                                        )}
                                    </button>
                                ))}
                            </div>
                        )}

                        {currentGuidedStep.type === 'user-input' && (
                            <GuidedInput onSubmit={handleGuidedAnswer} />
                        )}

                        {currentGuidedStep.type === 'confirmation' && (
                            <div className="mt-3">
                                <div className="bg-white rounded-lg p-3 border border-gray-200 mb-3">
                                    <div className="text-xs space-y-1">
                                        <div><span className="text-gray-500">Question:</span> {context.hypothesis}</div>
                                        <div><span className="text-gray-500">Treatment:</span> {context.treatment}</div>
                                        <div><span className="text-gray-500">Outcome:</span> {context.outcome}</div>
                                        {context.confounders.length > 0 && (
                                            <div><span className="text-gray-500">Confounders:</span> {context.confounders.join(', ')}</div>
                                        )}
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => handleConfirmation(true)}
                                        disabled={isProcessing}
                                        className="flex-grow px-4 py-2 bg-gradient-to-r from-primary to-accent text-white rounded-xl font-medium hover:opacity-90 disabled:opacity-50 transition-all"
                                    >
                                        {isProcessing ? 'Analyzing...' : 'Run Analysis'}
                                    </button>
                                    <button
                                        onClick={() => handleConfirmation(false)}
                                        disabled={isProcessing}
                                        className="px-4 py-2 border border-gray-300 text-gray-600 rounded-xl hover:bg-gray-50 transition-colors"
                                    >
                                        Edit
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

// Separate component for guided text input
const GuidedInput: React.FC<{ onSubmit: (value: string) => void }> = ({ onSubmit }) => {
    const [value, setValue] = useState('');

    const handleSubmit = () => {
        if (value.trim()) {
            onSubmit(value.trim());
            setValue('');
        }
    };

    return (
        <div className="mt-3">
            <textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder="Type your answer..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                rows={2}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSubmit();
                    }
                }}
            />
            <button
                onClick={handleSubmit}
                disabled={!value.trim()}
                className="mt-2 px-4 py-1.5 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-light disabled:opacity-50 transition-colors"
            >
                Continue
            </button>
        </div>
    );
};

export default ConversationalQueryFlow;
