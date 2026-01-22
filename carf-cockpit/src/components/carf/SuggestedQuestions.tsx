import React from 'react';

interface SuggestedQuestion {
    question: string;
    category: 'follow-up' | 'deep-dive' | 'alternative' | 'explore';
    icon?: string;
    reason?: string;
}

interface SuggestedQuestionsProps {
    questions: SuggestedQuestion[];
    onSelectQuestion: (question: string) => void;
    title?: string;
}

const categoryConfig = {
    'follow-up': { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: '🎯' },
    'deep-dive': { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', icon: '🔬' },
    'alternative': { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', icon: '🔄' },
    'explore': { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', icon: '🔍' },
};

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
    questions,
    onSelectQuestion,
    title = 'CARF Suggests',
}) => {
    if (questions.length === 0) {
        return null;
    }

    return (
        <div className="space-y-3">
            <div className="flex items-center gap-2">
                <span className="text-lg">💡</span>
                <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
            </div>

            <p className="text-sm text-gray-600">
                Based on your analysis, you may want to explore:
            </p>

            <div className="space-y-2">
                {questions.map((q, idx) => {
                    const config = categoryConfig[q.category];
                    return (
                        <button
                            key={idx}
                            onClick={() => onSelectQuestion(q.question)}
                            className={`w-full text-left p-3 rounded-lg border ${config.bg} ${config.border} hover:shadow-md transition-all group`}
                        >
                            <div className="flex items-start gap-3">
                                <span className="text-lg flex-shrink-0">{q.icon || config.icon}</span>
                                <div className="flex-grow">
                                    <div className={`text-sm font-medium ${config.text} group-hover:underline`}>
                                        {q.question}
                                    </div>
                                    {q.reason && (
                                        <div className="text-xs text-gray-500 mt-1">
                                            {q.reason}
                                        </div>
                                    )}
                                </div>
                                <svg
                                    className={`w-4 h-4 ${config.text} opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-0.5`}
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            </div>
                        </button>
                    );
                })}
            </div>

            <div className="pt-2 border-t border-gray-200">
                <button className="text-sm text-primary hover:underline flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                    Ask your own follow-up question...
                </button>
            </div>
        </div>
    );
};

export default SuggestedQuestions;

// Helper function to generate suggested questions based on analysis results
export function generateSuggestedQuestions(
    domain: string,
    treatment?: string,
    outcome?: string,
    confounders?: string[]
): SuggestedQuestion[] {
    const questions: SuggestedQuestion[] = [];

    if (domain === 'complicated' && treatment && outcome) {
        questions.push({
            question: `Does the effect of ${treatment} on ${outcome} vary by segment?`,
            category: 'deep-dive',
            reason: 'Explore heterogeneous treatment effects',
        });
        questions.push({
            question: `What is the optimal level of ${treatment} for maximizing ${outcome}?`,
            category: 'follow-up',
            reason: 'Find the optimal intervention point',
        });
        if (confounders && confounders.length > 0) {
            questions.push({
                question: `How sensitive is the effect to unmeasured confounders?`,
                category: 'alternative',
                reason: `Currently controlling for: ${confounders.join(', ')}`,
            });
        }
    }

    if (domain === 'complex') {
        questions.push({
            question: 'What experiments could reduce uncertainty the most?',
            category: 'explore',
            reason: 'Design optimal probes for complex domains',
        });
        questions.push({
            question: 'How does belief change with different prior assumptions?',
            category: 'alternative',
            reason: 'Sensitivity analysis for Bayesian inference',
        });
    }

    return questions;
}
