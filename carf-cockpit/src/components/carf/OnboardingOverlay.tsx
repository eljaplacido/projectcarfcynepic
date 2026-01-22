import React from 'react';
import type { ScenarioMetadata } from '../../types/carf';

interface OnboardingOverlayProps {
    scenarios: ScenarioMetadata[];
    onSelectScenario: (scenarioId: string) => void;
    onUploadData: () => void;
    onStartChat: () => void;
    onDismiss: () => void;
}

const OnboardingOverlay: React.FC<OnboardingOverlayProps> = ({
    scenarios,
    onSelectScenario,
    onUploadData,
    onStartChat,
    onDismiss,
}) => {
    const getDomainColor = (domain?: string) => {
        switch (domain) {
            case 'complicated': return 'bg-blue-500';
            case 'complex': return 'bg-purple-500';
            case 'clear': return 'bg-green-500';
            case 'chaotic': return 'bg-red-500';
            default: return 'bg-gray-500';
        }
    };

    const getDomainLabel = (domain?: string) => {
        switch (domain) {
            case 'complicated': return 'Causal Analysis';
            case 'complex': return 'Bayesian Inference';
            case 'clear': return 'Deterministic';
            case 'chaotic': return 'Circuit Breaker';
            default: return 'Auto-detect';
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="p-6 border-b border-gray-100 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                            <span className="text-white text-xl">🎯</span>
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Welcome to CARF</h2>
                            <p className="text-sm text-gray-500">Complex-Adaptive Reasoning Fabric</p>
                        </div>
                    </div>
                    <button
                        onClick={onDismiss}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-400 hover:text-gray-600"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="p-6">
                    <div className="text-center mb-6">
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">Try an Example Scenario</h3>
                        <p className="text-sm text-gray-600">
                            Explore CARF's causal inference and Bayesian analysis capabilities with pre-built scenarios
                        </p>
                    </div>

                    {/* Scenario Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                        {scenarios.slice(0, 3).map((scenario) => (
                            <div
                                key={scenario.id}
                                className="group bg-gray-50 hover:bg-white border border-gray-200 hover:border-primary/30 rounded-xl p-5 transition-all cursor-pointer hover:shadow-lg"
                                onClick={() => onSelectScenario(scenario.id)}
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <span className="text-3xl">{scenario.emoji || '📊'}</span>
                                    <span className={`badge text-white text-xs ${getDomainColor(scenario.domain)}`}>
                                        {getDomainLabel(scenario.domain)}
                                    </span>
                                </div>
                                <h4 className="font-semibold text-gray-900 mb-2 group-hover:text-primary transition-colors">
                                    {scenario.name}
                                </h4>
                                <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                                    {scenario.description}
                                </p>
                                <button className="w-full py-2 px-4 bg-primary/10 text-primary text-sm font-medium rounded-lg group-hover:bg-primary group-hover:text-white transition-colors">
                                    Load Scenario →
                                </button>
                            </div>
                        ))}
                    </div>

                    {/* More Scenarios Link */}
                    {scenarios.length > 3 && (
                        <div className="text-center mb-8">
                            <button className="text-sm text-primary hover:underline">
                                View all {scenarios.length} scenarios →
                            </button>
                        </div>
                    )}

                    {/* Divider */}
                    <div className="relative mb-8">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-gray-200"></div>
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="px-4 bg-white text-gray-500">OR</span>
                        </div>
                    </div>

                    {/* Alternative Actions */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <button
                            onClick={onUploadData}
                            className="flex items-center gap-4 p-4 border border-gray-200 rounded-xl hover:border-accent/30 hover:bg-accent/5 transition-all group"
                        >
                            <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                                <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                </svg>
                            </div>
                            <div className="text-left">
                                <div className="font-semibold text-gray-900">Upload Your Own Data</div>
                                <div className="text-sm text-gray-500">CSV or JSON up to 5,000 rows</div>
                            </div>
                        </button>

                        <button
                            onClick={onStartChat}
                            className="flex items-center gap-4 p-4 border border-gray-200 rounded-xl hover:border-primary/30 hover:bg-primary/5 transition-all group"
                        >
                            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                                <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                </svg>
                            </div>
                            <div className="text-left">
                                <div className="font-semibold text-gray-900">Start with a Question</div>
                                <div className="text-sm text-gray-500">Ask anything about your data</div>
                            </div>
                        </button>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-4 bg-gray-50 border-t border-gray-100 rounded-b-2xl">
                    <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                        <span>First time here?</span>
                        <button className="text-primary hover:underline font-medium">
                            Take a guided tour →
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default OnboardingOverlay;
