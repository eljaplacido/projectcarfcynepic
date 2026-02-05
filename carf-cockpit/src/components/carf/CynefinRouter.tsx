import React, { useState } from 'react';
import type { CynefinDomain, CynefinExplanation } from '../../types/carf';
import ExplainableWrapper from './ExplainableWrapper';

interface CynefinRouterProps {
    domain: CynefinDomain | null;
    confidence: number; // 0-1
    entropy: number; // 0-1
    solver: string;
    isProcessing?: boolean;
    scores?: Record<CynefinDomain, number>;
    reasoning?: string;
    explanation?: CynefinExplanation;
    keyIndicators?: string[]; // Phase 11: Router transparency
    triggeredMethod?: string; // Phase 11: Analysis method triggered
}

// Method Impact Configuration - explains how each domain affects analysis
const DOMAIN_METHOD_IMPACT: Record<string, {
    primaryMethods: string[];
    secondaryMethods: string[];
    guardianRules: string[];
    dataRequirements: string;
    uncertaintyHandling: string;
}> = {
    clear: {
        primaryMethods: ['Rule-based lookup', 'Best practice matching'],
        secondaryMethods: ['Historical case retrieval'],
        guardianRules: ['Standard compliance checks', 'Audit trail logging'],
        dataRequirements: 'Minimal - categorical data sufficient',
        uncertaintyHandling: 'Low tolerance - expects high confidence matches',
    },
    complicated: {
        primaryMethods: ['Causal Inference (DoWhy)', 'Statistical analysis'],
        secondaryMethods: ['Expert system consultation', 'Sensitivity analysis'],
        guardianRules: ['Effect size validation', 'Refutation test requirements'],
        dataRequirements: 'Moderate - structured tabular data with treatment/outcome variables',
        uncertaintyHandling: 'Quantified via confidence intervals and p-values',
    },
    complex: {
        primaryMethods: ['Bayesian Inference (PyMC)', 'Active probing'],
        secondaryMethods: ['Hypothesis generation', 'Pattern emergence detection'],
        guardianRules: ['Epistemic uncertainty thresholds', 'Probe design review'],
        dataRequirements: 'Variable - can work with sparse/incomplete data',
        uncertaintyHandling: 'Embraced - posterior distributions capture belief states',
    },
    chaotic: {
        primaryMethods: ['Rapid response protocols', 'Crisis stabilization'],
        secondaryMethods: ['Parallel action testing', 'Damage control'],
        guardianRules: ['Human escalation mandatory', 'Action time limits'],
        dataRequirements: 'Minimal - real-time signals prioritized',
        uncertaintyHandling: 'Act first, sense after - speed over precision',
    },
    disorder: {
        primaryMethods: ['Human clarification request', 'Query decomposition'],
        secondaryMethods: ['Multi-domain probing', 'Ambiguity resolution'],
        guardianRules: ['Mandatory human review', 'No autonomous action'],
        dataRequirements: 'Insufficient - requires additional context',
        uncertaintyHandling: 'Maximum caution - defer to human judgment',
    },
};

const DOMAIN_CONFIG = {
    clear: { color: 'bg-cynefin-clear', label: 'Clear', icon: '✓' },
    complicated: { color: 'bg-cynefin-complicated', label: 'Complicated', icon: '⚙️' },
    complex: { color: 'bg-cynefin-complex', label: 'Complex', icon: '🔮' },
    chaotic: { color: 'bg-cynefin-chaotic', label: 'Chaotic', icon: '⚡' },
    disorder: { color: 'bg-cynefin-disorder', label: 'Disorder', icon: '❓' },
};

const CynefinRouter: React.FC<CynefinRouterProps> = ({
    domain,
    confidence,
    entropy,
    solver,
    scores,
    reasoning,
    explanation,
    keyIndicators,
    triggeredMethod,
}) => {
    const [showWhy, setShowWhy] = useState(false);
    const [showWhyNot, setShowWhyNot] = useState(false);
    const [showMethodImpact, setShowMethodImpact] = useState(false);

    if (!domain) {
        return (
            <div className="text-sm text-gray-500 italic">
                Submit a query to see domain classification
            </div>
        );
    }

    // Normalize domain to lowercase for lookup
    const normalizedDomain = domain.toLowerCase() as CynefinDomain;
    const config = DOMAIN_CONFIG[normalizedDomain] || DOMAIN_CONFIG.disorder;
    const confidencePercent = Math.round(confidence * 100);
    const entropyPercent = Math.round(entropy * 100);

    // Generate alternative domains sorted by score (excluding current domain)
    const alternativeDomains = scores
        ? Object.entries(scores)
            .filter(([d]) => d.toLowerCase() !== normalizedDomain)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 3)
            .map(([d, score]) => {
                const domainKey = d.toLowerCase() as CynefinDomain;
                return {
                    domain: domainKey,
                    score: Math.round(score * 100),
                    config: DOMAIN_CONFIG[domainKey] || DOMAIN_CONFIG.disorder
                };
            })
        : [];

    const getConfidenceColor = (conf: number): string => {
        if (conf >= 0.8) return 'text-confidence-high';
        if (conf >= 0.5) return 'text-confidence-medium';
        return 'text-confidence-low';
    };

    return (
        <div className="space-y-4">
            {/* Domain Badge */}
            <ExplainableWrapper
                component="cynefin_domain"
                context={{ domain, confidence, entropy }}
                title={`${config.label} Domain`}
            >
                <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-lg ${config.color} flex items-center justify-center text-2xl`}>
                        {config.icon}
                    </div>
                    <div>
                        <div className="text-sm font-medium text-gray-500">DOMAIN</div>
                        <div className="text-lg font-bold">{config.label}</div>
                    </div>
                </div>
            </ExplainableWrapper>

            {/* Confidence Meter */}
            <ExplainableWrapper
                component="cynefin_confidence"
                context={{ confidence, domain }}
                title="Classification Confidence"
            >
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">Confidence</span>
                        <span className={`text-sm font-bold ${getConfidenceColor(confidence)}`}>
                            {confidencePercent}%
                        </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div
                            className={`h-2.5 rounded-full transition-all duration-500 ${confidence >= 0.8 ? 'bg-confidence-high' :
                                confidence >= 0.5 ? 'bg-confidence-medium' :
                                    'bg-confidence-low'
                                }`}
                            style={{ width: `${confidencePercent}%` }}
                        ></div>
                    </div>
                </div>
            </ExplainableWrapper>

            {/* Entropy Indicator */}
            <ExplainableWrapper
                component="cynefin_entropy"
                context={{ entropy, domain }}
                title="Signal Entropy"
            >
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">Signal Entropy</span>
                        <span className="text-sm font-bold text-gray-900">{entropyPercent}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div
                            className="h-2.5 rounded-full bg-purple-500 transition-all duration-500"
                            style={{ width: `${entropyPercent}%` }}
                        ></div>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                        {entropy < 0.3 ? 'Low ambiguity' : entropy < 0.6 ? 'Moderate ambiguity' : 'High ambiguity'}
                    </p>
                </div>
            </ExplainableWrapper>

            {/* Solver Recommendation */}
            <ExplainableWrapper
                component="cynefin_solver"
                context={{ solver, domain }}
                title="Cognitive Engine"
            >
                <div className="pt-3 border-t border-gray-200">
                    <div className="text-sm font-medium text-gray-700 mb-1">Cognitive Engine</div>
                    <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                        </svg>
                        <span className="text-sm font-semibold text-gray-900">{solver}</span>
                    </div>
                </div>
            </ExplainableWrapper>

            {/* Why This Classification? - Expandable */}
            <div className="pt-3 border-t border-gray-200">
                <button
                    onClick={() => setShowWhy(!showWhy)}
                    className="flex items-center justify-between w-full text-left group"
                >
                    <span className="text-sm font-medium text-primary hover:text-primary/80">
                        Why this classification?
                    </span>
                    <svg
                        className={`w-4 h-4 text-gray-400 transition-transform ${showWhy ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </button>

                {showWhy && (
                    <div className="mt-3 space-y-3">
                        {/* Reasoning */}
                        {reasoning && (
                            <div className="bg-gray-50 rounded-lg p-3">
                                <div className="text-xs font-medium text-gray-500 mb-1">Decision Path</div>
                                <p className="text-sm text-gray-700">{reasoning}</p>
                            </div>
                        )}

                        {/* Key Indicators - Use keyIndicators prop (API) or fallback to explanation */}
                        {(keyIndicators && keyIndicators.length > 0) || (explanation?.keyIndicators && explanation.keyIndicators.length > 0) ? (
                            <div>
                                <div className="text-xs font-medium text-gray-500 mb-2">Key Indicators</div>
                                <ul className="space-y-1">
                                    {(keyIndicators || explanation?.keyIndicators || []).map((indicator, idx) => (
                                        <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                                            <svg className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                            </svg>
                                            <span>{indicator}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ) : null}

                        {/* Triggered Method Badge */}
                        {triggeredMethod && (
                            <div className="mt-3 pt-3 border-t border-gray-200">
                                <div className="text-xs font-medium text-gray-500 mb-2">Triggered Analysis</div>
                                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-primary/10 text-primary rounded-full text-sm font-medium">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                    {triggeredMethod.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                </div>
                            </div>
                        )}

                        {/* Domain Scores Visualization */}
                        {scores && (
                            <div>
                                <div className="text-xs font-medium text-gray-500 mb-2">Domain Scores</div>
                                <div className="space-y-2">
                                    {Object.entries(scores)
                                        .sort(([, a], [, b]) => b - a)
                                        .map(([d, score]) => {
                                            const domainKey = d.toLowerCase() as CynefinDomain;
                                            const domainConfig = DOMAIN_CONFIG[domainKey] || DOMAIN_CONFIG.disorder;
                                            const isSelected = domainKey === normalizedDomain;
                                            return (
                                                <div key={d} className="flex items-center gap-2">
                                                    <span className={`text-xs w-20 ${isSelected ? 'font-bold' : 'text-gray-500'}`}>
                                                        {domainConfig.icon} {domainConfig.label}
                                                    </span>
                                                    <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                                                        <div
                                                            className={`h-1.5 rounded-full ${isSelected ? domainConfig.color : 'bg-gray-400'}`}
                                                            style={{ width: `${Math.round(score * 100)}%` }}
                                                        />
                                                    </div>
                                                    <span className={`text-xs w-8 text-right ${isSelected ? 'font-bold' : 'text-gray-500'}`}>
                                                        {Math.round(score * 100)}%
                                                    </span>
                                                </div>
                                            );
                                        })}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* How Does This Affect Analysis? - Method Impact */}
            <div className="pt-3 border-t border-gray-200">
                <button
                    onClick={() => setShowMethodImpact(!showMethodImpact)}
                    className="flex items-center justify-between w-full text-left group"
                >
                    <span className="text-sm font-medium text-primary hover:text-primary/80">
                        How does this affect analysis?
                    </span>
                    <svg
                        className={`w-4 h-4 text-gray-400 transition-transform ${showMethodImpact ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </button>

                {showMethodImpact && (
                    <div className="mt-3 space-y-3">
                        {/* Method Impact Explanation */}
                        {(() => {
                            const impact = DOMAIN_METHOD_IMPACT[normalizedDomain];
                            if (!impact) return null;

                            return (
                                <>
                                    {/* Primary Methods */}
                                    <div className="bg-blue-50 rounded-lg p-3 border border-blue-100">
                                        <div className="text-xs font-medium text-blue-700 mb-2 flex items-center gap-1">
                                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                            </svg>
                                            PRIMARY ANALYSIS METHODS
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {impact.primaryMethods.map((method, idx) => (
                                                <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full font-medium">
                                                    {method}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Secondary Methods */}
                                    <div className="bg-gray-50 rounded-lg p-3">
                                        <div className="text-xs font-medium text-gray-600 mb-2">SUPPORTING METHODS</div>
                                        <div className="flex flex-wrap gap-2">
                                            {impact.secondaryMethods.map((method, idx) => (
                                                <span key={idx} className="px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded-full">
                                                    {method}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Guardian Rules */}
                                    <div className="bg-purple-50 rounded-lg p-3 border border-purple-100">
                                        <div className="text-xs font-medium text-purple-700 mb-2 flex items-center gap-1">
                                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                            </svg>
                                            GUARDIAN POLICIES APPLIED
                                        </div>
                                        <ul className="space-y-1">
                                            {impact.guardianRules.map((rule, idx) => (
                                                <li key={idx} className="text-xs text-purple-800 flex items-center gap-1">
                                                    <span className="w-1 h-1 bg-purple-400 rounded-full" />
                                                    {rule}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>

                                    {/* Data & Uncertainty */}
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="bg-gray-50 rounded-lg p-2">
                                            <div className="text-xs font-medium text-gray-500 mb-1">DATA REQUIREMENTS</div>
                                            <div className="text-xs text-gray-700">{impact.dataRequirements}</div>
                                        </div>
                                        <div className="bg-gray-50 rounded-lg p-2">
                                            <div className="text-xs font-medium text-gray-500 mb-1">UNCERTAINTY HANDLING</div>
                                            <div className="text-xs text-gray-700">{impact.uncertaintyHandling}</div>
                                        </div>
                                    </div>
                                </>
                            );
                        })()}
                    </div>
                )}
            </div>

            {/* Why Not? - Alternative Domains */}
            {alternativeDomains.length > 0 && (
                <div className="pt-3 border-t border-gray-200">
                    <button
                        onClick={() => setShowWhyNot(!showWhyNot)}
                        className="flex items-center justify-between w-full text-left group"
                    >
                        <span className="text-sm font-medium text-gray-500 hover:text-gray-700">
                            Why not other domains?
                        </span>
                        <svg
                            className={`w-4 h-4 text-gray-400 transition-transform ${showWhyNot ? 'rotate-180' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>

                    {showWhyNot && (
                        <div className="mt-3 space-y-2">
                            {alternativeDomains.map((alt) => {
                                const altExplanation = explanation?.alternativeDomains?.find(
                                    (a) => a.domain === alt.domain
                                );
                                return (
                                    <div
                                        key={alt.domain}
                                        className="flex items-start gap-3 p-2 bg-gray-50 rounded-lg"
                                    >
                                        <div className={`w-8 h-8 rounded ${alt.config.color} flex items-center justify-center text-sm flex-shrink-0`}>
                                            {alt.config.icon}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm font-medium text-gray-700">
                                                    {alt.config.label}
                                                </span>
                                                <span className="text-xs text-gray-400">
                                                    {alt.score}%
                                                </span>
                                            </div>
                                            <p className="text-xs text-gray-500 mt-0.5">
                                                {altExplanation?.reason || getDefaultWhyNotReason(domain, alt.domain)}
                                            </p>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

// Generate default "why not" explanations based on domain differences
function getDefaultWhyNotReason(selected: CynefinDomain, alternative: CynefinDomain): string {
    const reasons: Record<string, Record<string, string>> = {
        clear: {
            complicated: 'Query lacks the expert-knowledge requirement typical of complicated domains.',
            complex: 'Outcomes appear predictable; no emergent behavior detected.',
            chaotic: 'No crisis indicators or urgent action requirements identified.',
            disorder: 'Clear categorization signals present.',
        },
        complicated: {
            clear: 'Expert analysis required beyond simple best practices.',
            complex: 'Causal relationships can be determined through analysis.',
            chaotic: 'Situation allows time for structured analysis.',
            disorder: 'Domain characteristics are identifiable.',
        },
        complex: {
            clear: 'Multiple interacting variables with emergent properties.',
            complicated: 'Cause-effect only visible in retrospect; requires probing.',
            chaotic: 'Patterns exist even if emergent; not pure randomness.',
            disorder: 'Domain signals, though ambiguous, point to complexity.',
        },
        chaotic: {
            clear: 'Immediate action required; no time for analysis.',
            complicated: 'System too unstable for structured expert analysis.',
            complex: 'No patterns to probe; requires immediate stabilization.',
            disorder: 'Crisis indicators clearly present.',
        },
        disorder: {
            clear: 'Insufficient information to classify as clear.',
            complicated: 'Cannot identify expert-analysis patterns.',
            complex: 'Cannot identify complexity signals.',
            chaotic: 'No clear crisis indicators.',
        },
    };
    return reasons[selected]?.[alternative] || 'Lower confidence score for this classification.';
}

export default CynefinRouter;
