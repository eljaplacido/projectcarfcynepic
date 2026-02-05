import React, { useState, useEffect } from 'react';

export type WalkthroughTrack = 'quick-demo' | 'analyst' | 'executive' | 'contributor' | 'production';

interface WalkthroughStep {
    id: string;
    title: string;
    content: string;
    targetSelector?: string; // CSS selector for element to highlight
    action?: string; // Description of action user should take
    position?: 'top' | 'bottom' | 'left' | 'right';
}

interface WalkthroughTrackConfig {
    id: WalkthroughTrack;
    name: string;
    description: string;
    duration: string;
    icon: string;
    steps: WalkthroughStep[];
}

const WALKTHROUGH_TRACKS: WalkthroughTrackConfig[] = [
    {
        id: 'quick-demo',
        name: 'Quick Demo',
        description: 'Show me what CARF can do',
        duration: '~2 minutes',
        icon: '🎯',
        steps: [
            {
                id: 'qd-1',
                title: 'Welcome to CARF',
                content: 'CARF is a Complex-Adaptive Reasoning Fabric that combines causal inference, Bayesian analysis, and LLM capabilities for transparent decision-making.',
            },
            {
                id: 'qd-2',
                title: 'Select a Scenario',
                content: 'Click the scenario dropdown and select "Discount vs Churn" to load a pre-built causal analysis scenario.',
                targetSelector: '[data-tour="scenario-selector"]',
                action: 'Select a scenario from the dropdown',
                position: 'bottom',
            },
            {
                id: 'qd-3',
                title: 'Review the Query',
                content: 'Notice how the query input is pre-populated with a suggested question. You can modify it or use the suggested queries below.',
                targetSelector: '[data-tour="query-input"]',
                position: 'right',
            },
            {
                id: 'qd-4',
                title: 'Run Analysis',
                content: 'Click "Send" to submit your query. CARF will route it to the appropriate cognitive engine based on the Cynefin framework.',
                targetSelector: '[data-tour="submit-button"]',
                action: 'Click Send to run the analysis',
                position: 'top',
            },
            {
                id: 'qd-5',
                title: 'Explore Results',
                content: 'View the causal DAG, effect estimates, refutation tests, and Guardian policy evaluation. Each panel shows transparent reasoning.',
                targetSelector: '[data-tour="results-area"]',
                position: 'left',
            },
        ],
    },
    {
        id: 'analyst',
        name: 'Analyst Onboarding',
        description: 'I want to use my own data',
        duration: '~5 minutes',
        icon: '📊',
        steps: [
            {
                id: 'ao-1',
                title: 'Data Analysis with CARF',
                content: 'Learn how to upload your own data and configure causal or Bayesian analysis.',
            },
            {
                id: 'ao-2',
                title: 'Upload Your Data',
                content: 'Click "Upload Your Own Data" to start the guided data onboarding wizard. CARF accepts CSV and JSON files up to 5,000 rows.',
                action: 'Click the upload button',
            },
            {
                id: 'ao-3',
                title: 'Preview & Confirm',
                content: 'Review your data columns and types. CARF will auto-detect numeric, categorical, and binary variables.',
            },
            {
                id: 'ao-4',
                title: 'Choose Analysis Type',
                content: 'Select Causal Analysis for "What is the effect of X on Y?" questions, or Bayesian Inference for parameter estimation.',
            },
            {
                id: 'ao-5',
                title: 'Configure Variables',
                content: 'For causal analysis, select your treatment (intervention), outcome (what you measure), and covariates (potential confounders).',
            },
            {
                id: 'ao-6',
                title: 'Compose Your Question',
                content: 'Write your analysis question in natural language. CARF will route it to the appropriate solver.',
            },
            {
                id: 'ao-7',
                title: 'Interpret Results',
                content: 'Review effect estimates, confidence intervals, refutation tests, and uncertainty decomposition. Click any result for methodology details.',
            },
            {
                id: 'ao-8',
                title: 'Iterate & Export',
                content: 'Use suggested follow-up questions to deepen your analysis. Export results as JSON for reproducibility.',
            },
        ],
    },
    {
        id: 'executive',
        name: 'Executive View',
        description: 'I need to make decisions',
        duration: '~3 minutes',
        icon: '📈',
        steps: [
            {
                id: 'ev-1',
                title: 'Executive Dashboard Overview',
                content: 'The Executive View provides a high-level summary of AI-driven insights, KPIs, and recommended actions without technical details.',
            },
            {
                id: 'ev-2',
                title: 'Key Performance Indicators',
                content: 'Monitor critical metrics: Total Impact, Confidence Level, Risk Assessment, and Policy Compliance. Each KPI is derived from the underlying causal analysis.',
            },
            {
                id: 'ev-3',
                title: 'Proposed Actions',
                content: 'View AI-recommended actions ranked by expected impact. Each recommendation includes a confidence score and supporting evidence from the analysis.',
            },
            {
                id: 'ev-4',
                title: 'Risk & Compliance',
                content: 'The Guardian policy layer validates all recommendations against organizational policies. See which actions require approval and why.',
            },
            {
                id: 'ev-5',
                title: 'Transparency & Audit',
                content: 'All AI decisions are fully explainable. Click any metric to see the underlying methodology, data sources, and confidence intervals.',
            },
            {
                id: 'ev-6',
                title: 'Human-in-the-Loop',
                content: 'High-impact or uncertain decisions are flagged for human review. The escalation panel shows pending items requiring your approval.',
            },
        ],
    },
    {
        id: 'contributor',
        name: 'Contributor Guide',
        description: 'I want to extend CARF',
        duration: '~10 minutes',
        icon: '🔧',
        steps: [
            {
                id: 'cg-1',
                title: 'CARF Architecture',
                content: 'CARF uses a 4-layer cognitive stack: Cynefin Router → Domain Solvers → Reasoning Services → Guardian Policy Layer.',
            },
            {
                id: 'cg-2',
                title: 'Key Documentation',
                content: 'Review PRD.md for requirements, LLM_AGENTIC_STRATEGY.md for when LLMs are used, and SELF_HEALING_ARCHITECTURE.md for resilience patterns.',
            },
            {
                id: 'cg-3',
                title: 'Code Structure',
                content: 'src/core/ contains schemas, src/services/ has business logic, src/workflows/ has LangGraph orchestration, src/dashboard/ has UI.',
            },
            {
                id: 'cg-4',
                title: 'Extension Points',
                content: 'Add new solvers in src/services/, new API endpoints in src/main.py, and new UI components in carf-cockpit/src/components/carf/.',
            },
            {
                id: 'cg-5',
                title: 'Adding a New Solver',
                content: 'Create a service class with analyze() method, register it in the workflow graph, and add corresponding UI panel.',
            },
            {
                id: 'cg-6',
                title: 'Testing Patterns',
                content: 'Run pytest tests/ for backend, npm test for frontend. Use CARF_TEST_MODE=1 to run without API keys.',
            },
            {
                id: 'cg-7',
                title: 'Router Training',
                content: 'See ROUTER_TRAINING.md for fine-tuning the DistilBERT router on custom domain data.',
            },
            {
                id: 'cg-8',
                title: 'Contribution Workflow',
                content: 'Fork the repo, create a feature branch, make changes, run tests, and submit a PR with description.',
            },
        ],
    },
    {
        id: 'production',
        name: 'Production Deployment',
        description: 'How do I deploy this?',
        duration: '~5 minutes',
        icon: '🏢',
        steps: [
            {
                id: 'pd-1',
                title: 'Production Requirements',
                content: 'CARF requires Python 3.11+, Node 18+, and optionally Neo4j 5+ and Kafka for persistence and audit.',
            },
            {
                id: 'pd-2',
                title: 'Security Checklist',
                content: 'Review SECURITY.md, ensure API keys are in environment variables, and consider API authentication for production.',
            },
            {
                id: 'pd-3',
                title: 'Docker Deployment',
                content: 'Use docker compose up for the full stack: API, Streamlit/React, Neo4j, Kafka. See docker-compose.yml.',
            },
            {
                id: 'pd-4',
                title: 'Environment Configuration',
                content: 'Copy .env.example to .env, set DEEPSEEK_API_KEY or OPENAI_API_KEY, configure optional services.',
            },
            {
                id: 'pd-5',
                title: 'Database Setup',
                content: 'For persistence, configure Neo4j connection in .env. Run demo/seeds/neo4j_seed.py to populate sample data.',
            },
            {
                id: 'pd-6',
                title: 'Monitoring',
                content: 'Monitor API health at /health, review Kafka audit trail for decision logs, use standard Python logging.',
            },
            {
                id: 'pd-7',
                title: 'Scaling Considerations',
                content: 'For scale, move from SQLite to PostgreSQL, add Redis caching, and deploy behind load balancer.',
            },
        ],
    },
];

interface WalkthroughManagerProps {
    onClose: () => void;
    onTrackComplete?: (trackId: WalkthroughTrack) => void;
}

const WalkthroughManager: React.FC<WalkthroughManagerProps> = ({
    onClose,
    onTrackComplete,
}) => {
    const [selectedTrack, setSelectedTrack] = useState<WalkthroughTrack | null>(null);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);

    const currentTrack = selectedTrack
        ? WALKTHROUGH_TRACKS.find(t => t.id === selectedTrack)
        : null;

    const currentStep = currentTrack?.steps[currentStepIndex];
    const totalSteps = currentTrack?.steps.length || 0;
    const isLastStep = currentStepIndex === totalSteps - 1;
    const isFirstStep = currentStepIndex === 0;

    useEffect(() => {
        // Highlight target element when step changes
        if (currentStep?.targetSelector) {
            const element = document.querySelector(currentStep.targetSelector);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                element.classList.add('tour-highlight');
                return () => element.classList.remove('tour-highlight');
            }
        }
    }, [currentStep]);

    const handleNextStep = () => {
        if (isLastStep) {
            if (onTrackComplete && selectedTrack) {
                onTrackComplete(selectedTrack);
            }
            setSelectedTrack(null);
            setCurrentStepIndex(0);
        } else {
            setCurrentStepIndex(i => i + 1);
        }
    };

    const handlePrevStep = () => {
        if (!isFirstStep) {
            setCurrentStepIndex(i => i - 1);
        }
    };

    const handleSelectTrack = (trackId: WalkthroughTrack) => {
        setSelectedTrack(trackId);
        setCurrentStepIndex(0);
    };

    // Track selection view
    if (!selectedTrack) {
        return (
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
                    {/* Header */}
                    <div className="p-6 border-b border-gray-100 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                                <span className="text-white text-xl">🎓</span>
                            </div>
                            <div>
                                <h2 className="text-xl font-bold text-gray-900">CARF Walkthrough</h2>
                                <p className="text-sm text-gray-500">Choose your learning path</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-400 hover:text-gray-600"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Track Cards */}
                    <div className="p-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {WALKTHROUGH_TRACKS.map((track) => (
                                <button
                                    key={track.id}
                                    onClick={() => handleSelectTrack(track.id)}
                                    className="text-left p-5 bg-gray-50 hover:bg-white border border-gray-200 hover:border-primary/30 rounded-xl transition-all hover:shadow-lg group"
                                >
                                    <div className="flex items-start gap-4">
                                        <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center text-2xl group-hover:bg-primary/20 transition-colors">
                                            {track.icon}
                                        </div>
                                        <div className="flex-grow">
                                            <div className="font-semibold text-gray-900 group-hover:text-primary transition-colors">
                                                {track.name}
                                            </div>
                                            <div className="text-sm text-gray-600 mt-1">{track.description}</div>
                                            <div className="text-xs text-gray-500 mt-2">{track.duration} · {track.steps.length} steps</div>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="p-4 bg-gray-50 border-t border-gray-100 rounded-b-2xl text-center">
                        <button
                            onClick={onClose}
                            className="text-sm text-gray-500 hover:text-gray-700"
                        >
                            Skip tour for now
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Step view
    return (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-end justify-center p-4">
            {/* Step Card */}
            <div className="bg-white rounded-2xl shadow-2xl max-w-xl w-full mb-20">
                {/* Progress Bar */}
                <div className="h-1 bg-gray-200 rounded-t-2xl overflow-hidden">
                    <div
                        className="h-full bg-primary transition-all duration-300"
                        style={{ width: `${((currentStepIndex + 1) / totalSteps) * 100}%` }}
                    />
                </div>

                {/* Content */}
                <div className="p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <span className="text-2xl">{currentTrack?.icon}</span>
                            <span className="text-sm text-gray-500">
                                {currentTrack?.name} · Step {currentStepIndex + 1}/{totalSteps}
                            </span>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors text-gray-400"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    <h3 className="text-lg font-bold text-gray-900 mb-2">{currentStep?.title}</h3>
                    <p className="text-sm text-gray-600 mb-4">{currentStep?.content}</p>

                    {currentStep?.action && (
                        <div className="p-3 bg-primary/10 border border-primary/20 rounded-lg mb-4">
                            <div className="text-xs font-semibold text-primary mb-1">👆 ACTION</div>
                            <div className="text-sm text-gray-700">{currentStep.action}</div>
                        </div>
                    )}

                    {/* Navigation */}
                    <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                        <button
                            onClick={handlePrevStep}
                            disabled={isFirstStep}
                            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            ← Back
                        </button>
                        <button
                            onClick={handleNextStep}
                            className="px-6 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary-light transition-colors"
                        >
                            {isLastStep ? 'Finish' : 'Next →'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default WalkthroughManager;

// CSS to add to index.css for tour highlighting
/*
.tour-highlight {
    position: relative;
    z-index: 51;
    box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.3), 0 0 0 8px rgba(124, 58, 237, 0.1);
    border-radius: 8px;
}
*/
