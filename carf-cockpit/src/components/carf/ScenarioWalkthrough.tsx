/**
 * ScenarioWalkthrough Component
 * 
 * Provides an interactive guided tour through the Scope 3 emissions analysis workflow.
 * Guides users step-by-step through the platform's features with highlights and explanations.
 */

import React, { useState, useEffect } from 'react';
import {
    ChevronLeft,
    ChevronRight,
    X,
    CheckCircle,
    HelpCircle,
    ArrowRight,
    Lightbulb,
    Database,
    MessageSquare,
    Network,
    BarChart3,
    Shield,
    Target
} from 'lucide-react';

interface WalkthroughStep {
    id: number;
    title: string;
    description: string;
    detailedExplanation: string;
    highlightElement?: string; // CSS selector to highlight
    icon: React.ReactNode;
    action?: 'scroll' | 'click' | 'wait';
    targetPanel?: string;
}

const WALKTHROUGH_STEPS: WalkthroughStep[] = [
    {
        id: 1,
        title: "Welcome to Scope 3 Analysis",
        description: "Learn how to analyze supplier emissions impact using causal AI",
        detailedExplanation: "This walkthrough guides you through analyzing Scope 3 emissions - the indirect emissions in your supply chain. You'll see how CARF uses causal inference to determine which supplier programs actually reduce emissions, not just correlate with them.",
        icon: <Lightbulb className="w-6 h-6" />,
    },
    {
        id: 2,
        title: "Understanding Your Data",
        description: "2,000 supplier records with realistic causal structure",
        detailedExplanation: "The dataset includes:\n• supplier_program: Whether supplier participates in emissions reduction program\n• scope3_emissions: Change in emissions (tCO2e) - our outcome\n• region, supplier_size: Covariates that may confound the analysis\n• category: GHG Protocol Scope 3 category (purchased goods, transport, etc.)\n• confidence_score: Data quality indicator (0.4-0.98)",
        icon: <Database className="w-6 h-6" />,
        targetPanel: "data",
    },
    {
        id: 3,
        title: "Ask a Causal Question",
        description: "Formulate a question about program effectiveness",
        detailedExplanation: "Try asking: 'What is the effect of supplier programs on Scope 3 emissions?'\n\nThis is a causal question because it asks about the EFFECT of an intervention, not just a correlation. CARF will route this to the appropriate analysis domain.",
        icon: <MessageSquare className="w-6 h-6" />,
        highlightElement: ".query-input",
        targetPanel: "query",
    },
    {
        id: 4,
        title: "Cynefin Domain Classification",
        description: "The router determines: Complicated → Causal Analysis",
        detailedExplanation: "Based on the query structure and available data, CARF classifies this as a 'Complicated' domain problem:\n• Clear treatment/outcome structure\n• Sufficient data for statistical analysis\n• Known confounders to control for\n\nThis triggers the Causal Analyst agent rather than Bayesian or Circuit Breaker paths.",
        icon: <Network className="w-6 h-6" />,
        highlightElement: ".cynefin-router",
        targetPanel: "router",
    },
    {
        id: 5,
        title: "Causal DAG & Effect Estimation",
        description: "View the causal graph and treatment effect",
        detailedExplanation: "The Causal DAG shows:\n• supplier_program → scope3_emissions (treatment → outcome)\n• supplier_size → supplier_program (confounder - bigger suppliers more likely to join)\n• region affects both program participation and emission reductions\n\nThe Average Treatment Effect (ATE) is approximately -71 tCO2e, meaning the program reduces emissions by 71 tons CO2 equivalent per supplier.",
        icon: <BarChart3 className="w-6 h-6" />,
        highlightElement: ".causal-dag",
        targetPanel: "causal",
    },
    {
        id: 6,
        title: "Refutation Tests",
        description: "Validate the causal estimate's robustness",
        detailedExplanation: "DoWhy runs several refutation tests:\n• Placebo treatment: Replace real treatment with random - should find no effect\n• Random common cause: Add random confounder - estimate should remain stable\n• Data subset: Analyze on subset - effect should be consistent\n\nPassing 3/4 refutations indicates a robust causal estimate.",
        icon: <CheckCircle className="w-6 h-6" />,
        targetPanel: "refutation",
    },
    {
        id: 7,
        title: "Guardian Policy Check",
        description: "Verify recommendations comply with organizational policies",
        detailedExplanation: "Before delivering recommendations, the Guardian validates:\n• Budget constraints: Is the investment within approved limits?\n• Regional restrictions: Are there any policy limitations by geography?\n• Approval thresholds: Does this decision require human review?\n\nThe Guardian shows 'Approved' with any auto-repairs applied.",
        icon: <Shield className="w-6 h-6" />,
        highlightElement: ".guardian-panel",
        targetPanel: "guardian",
    },
    {
        id: 8,
        title: "Actionable Recommendations",
        description: "Get prioritized next steps with causal backing",
        detailedExplanation: "Based on the analysis, CARF recommends:\n1. Prioritize expanding supplier programs in EU region (1.3x effect multiplier)\n2. Focus on large suppliers first (1.5x effect multiplier)\n3. Target suppliers with high baseline emissions (more reduction potential)\n\nEach recommendation is backed by the causal analysis, not just correlation.",
        icon: <Target className="w-6 h-6" />,
        targetPanel: "recommendations",
    },
];

interface ScenarioWalkthroughProps {
    isOpen: boolean;
    onClose: () => void;
    onStepChange?: (step: number) => void;
    scenarioId?: string;
}

export function ScenarioWalkthrough(props: ScenarioWalkthroughProps) {
    const { isOpen, onClose, onStepChange } = props;
    const [currentStep, setCurrentStep] = useState(0);
    const [showDetails, setShowDetails] = useState(false);
    const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());

    const step = WALKTHROUGH_STEPS[currentStep];
    const progress = ((currentStep + 1) / WALKTHROUGH_STEPS.length) * 100;

    useEffect(() => {
        if (onStepChange) {
            onStepChange(currentStep);
        }
    }, [currentStep, onStepChange]);

    const handleNext = () => {
        setCompletedSteps(prev => new Set([...prev, currentStep]));
        if (currentStep < WALKTHROUGH_STEPS.length - 1) {
            setCurrentStep(currentStep + 1);
            setShowDetails(false);
        }
    };

    const handlePrev = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
            setShowDetails(false);
        }
    };

    const handleSkipToStep = (stepIndex: number) => {
        setCurrentStep(stepIndex);
        setShowDetails(false);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-end justify-center pb-8 pointer-events-none">
            {/* Walkthrough Card */}
            <div className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-lg pointer-events-auto animate-in slide-in-from-bottom-4">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-xl">
                    <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-blue-100 rounded-lg text-blue-600">
                            {step.icon}
                        </div>
                        <span className="text-sm font-medium text-gray-500">
                            Step {currentStep + 1} of {WALKTHROUGH_STEPS.length}
                        </span>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors"
                        title="Close walkthrough"
                    >
                        <X className="w-4 h-4 text-gray-500" />
                    </button>
                </div>

                {/* Progress Bar */}
                <div className="h-1 bg-gray-100">
                    <div
                        className="h-1 bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-300"
                        style={{ width: `${progress}%` }}
                    />
                </div>

                {/* Step Indicators */}
                <div className="flex justify-center gap-1.5 py-3 px-4 border-b border-gray-100">
                    {WALKTHROUGH_STEPS.map((_, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleSkipToStep(idx)}
                            className={`w-2 h-2 rounded-full transition-all ${idx === currentStep
                                    ? 'bg-blue-500 scale-125'
                                    : completedSteps.has(idx)
                                        ? 'bg-green-400'
                                        : 'bg-gray-300 hover:bg-gray-400'
                                }`}
                            title={`Step ${idx + 1}: ${WALKTHROUGH_STEPS[idx].title}`}
                        />
                    ))}
                </div>

                {/* Content */}
                <div className="p-5">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {step.title}
                    </h3>
                    <p className="text-gray-600 mb-4">
                        {step.description}
                    </p>

                    {/* Expandable Details */}
                    <div className="mb-4">
                        <button
                            onClick={() => setShowDetails(!showDetails)}
                            className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700 transition-colors"
                        >
                            <HelpCircle className="w-4 h-4" />
                            {showDetails ? "Hide details" : "Why is this important?"}
                        </button>

                        {showDetails && (
                            <div className="mt-3 p-4 bg-blue-50 rounded-lg border border-blue-100">
                                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">
                                    {step.detailedExplanation}
                                </pre>
                            </div>
                        )}
                    </div>

                    {/* Target Panel Indicator */}
                    {step.targetPanel && (
                        <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
                            <ArrowRight className="w-4 h-4" />
                            Look at: <span className="font-medium text-gray-700 capitalize">{step.targetPanel} panel</span>
                        </div>
                    )}
                </div>

                {/* Footer Navigation */}
                <div className="flex items-center justify-between px-5 py-4 bg-gray-50 border-t border-gray-100 rounded-b-xl">
                    <button
                        onClick={handlePrev}
                        disabled={currentStep === 0}
                        className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${currentStep === 0
                                ? 'text-gray-400 cursor-not-allowed'
                                : 'text-gray-600 hover:bg-gray-200'
                            }`}
                    >
                        <ChevronLeft className="w-4 h-4" />
                        Previous
                    </button>

                    {currentStep < WALKTHROUGH_STEPS.length - 1 ? (
                        <button
                            onClick={handleNext}
                            className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            Next
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    ) : (
                        <button
                            onClick={onClose}
                            className="flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors"
                        >
                            <CheckCircle className="w-4 h-4" />
                            Complete
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ScenarioWalkthrough;
