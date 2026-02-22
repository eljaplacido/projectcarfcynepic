import { describe, it, expect } from 'vitest';
import { computeHighlights } from '../hooks/useProactiveHighlight';
import type { QueryResponse } from '../types/carf';

/**
 * Helper to build a minimal QueryResponse with sensible defaults.
 * Override any field you need for a specific test.
 */
function makeResponse(overrides: Partial<QueryResponse> = {}): QueryResponse {
    return {
        sessionId: 'test-session',
        domain: 'complicated',
        domainConfidence: 0.85,
        domainEntropy: 0.15,
        guardianVerdict: null,
        response: 'Analysis complete',
        requiresHuman: false,
        reasoningChain: [
            {
                node: 'router',
                action: 'classify',
                confidence: '0.85',
                timestamp: new Date().toISOString(),
                durationMs: 50,
            },
        ],
        causalResult: null,
        bayesianResult: null,
        guardianResult: null,
        error: null,
        ...overrides,
    };
}

describe('computeHighlights', () => {
    // -----------------------------------------------------------------------
    // Null / undefined input
    // -----------------------------------------------------------------------
    it('returns empty highlights for null input', () => {
        const result = computeHighlights(null);
        expect(result.highlightedPanels).toEqual([]);
        expect(result.highlightReasons).toEqual({});
    });

    it('returns empty highlights for undefined input', () => {
        const result = computeHighlights(undefined);
        expect(result.highlightedPanels).toEqual([]);
        expect(result.highlightReasons).toEqual({});
    });

    // -----------------------------------------------------------------------
    // Rule 1: Low causal p-value -> highlight causal-results
    // -----------------------------------------------------------------------
    it('highlights causal-results when p-value < 0.05', () => {
        const response = makeResponse({
            causalResult: {
                effect: -3.2,
                unit: 'percentage points',
                pValue: 0.01,
                confidenceInterval: [-4.5, -1.9],
                description: 'Significant effect',
                refutationsPassed: 3,
                refutationsTotal: 3,
                refutationDetails: [],
                confoundersControlled: [],
                evidenceBase: 'observational',
                metaAnalysis: false,
                studies: 1,
                treatment: 'discount',
                outcome: 'churn',
            },
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).toContain('causal-results');
        expect(result.highlightReasons['causal-results']).toContain('p = 0.0100');
    });

    it('does NOT highlight causal-results when p-value >= 0.05', () => {
        const response = makeResponse({
            causalResult: {
                effect: -1.0,
                unit: 'percentage points',
                pValue: 0.15,
                confidenceInterval: [-3.0, 1.0],
                description: 'Non-significant',
                refutationsPassed: 2,
                refutationsTotal: 3,
                refutationDetails: [],
                confoundersControlled: [],
                evidenceBase: 'observational',
                metaAnalysis: false,
                studies: 1,
                treatment: 'discount',
                outcome: 'churn',
            },
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).not.toContain('causal-results');
    });

    it('does NOT highlight causal-results when p-value is null', () => {
        const response = makeResponse({
            causalResult: {
                effect: -1.0,
                unit: 'percentage points',
                pValue: null,
                confidenceInterval: [-3.0, 1.0],
                description: 'Missing p-value',
                refutationsPassed: 0,
                refutationsTotal: 0,
                refutationDetails: [],
                confoundersControlled: [],
                evidenceBase: 'observational',
                metaAnalysis: false,
                studies: 1,
                treatment: 'discount',
                outcome: 'churn',
            },
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).not.toContain('causal-results');
    });

    // -----------------------------------------------------------------------
    // Rule 2: Guardian rejected -> highlight guardian
    // -----------------------------------------------------------------------
    it('highlights guardian panel when verdict is rejected', () => {
        const response = makeResponse({
            guardianVerdict: 'rejected',
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).toContain('guardian');
        expect(result.highlightReasons['guardian']).toContain('rejected');
    });

    it('does NOT highlight guardian when verdict is approved', () => {
        const response = makeResponse({
            guardianVerdict: 'approved',
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).not.toContain('guardian');
    });

    it('does NOT highlight guardian when verdict is null', () => {
        const response = makeResponse({
            guardianVerdict: null,
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).not.toContain('guardian');
    });

    // -----------------------------------------------------------------------
    // Rule 3: High Bayesian uncertainty -> highlight bayesian
    // -----------------------------------------------------------------------
    it('highlights bayesian panel when total uncertainty > 0.7', () => {
        const response = makeResponse({
            bayesianResult: {
                variable: 'churn_rate',
                priorMean: 0.1,
                priorStd: 0.05,
                posteriorMean: 0.12,
                posteriorStd: 0.04,
                confidenceLevel: 'low',
                interpretation: 'Uncertain',
                epistemicUncertainty: 0.5,
                aleatoricUncertainty: 0.3,
                totalUncertainty: 0.8,
            },
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).toContain('bayesian');
        expect(result.highlightReasons['bayesian']).toContain('80%');
    });

    it('does NOT highlight bayesian panel when uncertainty <= 0.7', () => {
        const response = makeResponse({
            bayesianResult: {
                variable: 'churn_rate',
                priorMean: 0.1,
                priorStd: 0.05,
                posteriorMean: 0.12,
                posteriorStd: 0.04,
                confidenceLevel: 'high',
                interpretation: 'Confident',
                epistemicUncertainty: 0.1,
                aleatoricUncertainty: 0.1,
                totalUncertainty: 0.2,
            },
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).not.toContain('bayesian');
    });

    // -----------------------------------------------------------------------
    // Rule 4: Missing data -> highlight transparency
    // -----------------------------------------------------------------------
    it('highlights transparency panel when error is present', () => {
        const response = makeResponse({
            error: 'Data source unavailable',
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).toContain('transparency');
        expect(result.highlightReasons['transparency']).toContain('Incomplete');
    });

    it('highlights transparency when causal pValue is null (missing data)', () => {
        const response = makeResponse({
            causalResult: {
                effect: -1.0,
                unit: 'percentage points',
                pValue: null,
                confidenceInterval: [-3.0, 1.0],
                description: 'Missing p-value',
                refutationsPassed: 0,
                refutationsTotal: 0,
                refutationDetails: [],
                confoundersControlled: [],
                evidenceBase: 'observational',
                metaAnalysis: false,
                studies: 1,
                treatment: 'discount',
                outcome: 'churn',
            },
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).toContain('transparency');
    });

    it('highlights transparency when reasoning chain is empty and response is null', () => {
        const response = makeResponse({
            reasoningChain: [],
            response: null,
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).toContain('transparency');
    });

    // -----------------------------------------------------------------------
    // Multiple rules can fire simultaneously
    // -----------------------------------------------------------------------
    it('highlights multiple panels when several conditions are met', () => {
        const response = makeResponse({
            causalResult: {
                effect: -3.2,
                unit: 'percentage points',
                pValue: 0.001,
                confidenceInterval: [-4.5, -1.9],
                description: 'Significant',
                refutationsPassed: 3,
                refutationsTotal: 3,
                refutationDetails: [],
                confoundersControlled: [],
                evidenceBase: 'observational',
                metaAnalysis: false,
                studies: 1,
                treatment: 'discount',
                outcome: 'churn',
            },
            guardianVerdict: 'rejected',
            bayesianResult: {
                variable: 'churn_rate',
                priorMean: 0.1,
                priorStd: 0.05,
                posteriorMean: 0.12,
                posteriorStd: 0.04,
                confidenceLevel: 'low',
                interpretation: 'Uncertain',
                epistemicUncertainty: 0.5,
                aleatoricUncertainty: 0.3,
                totalUncertainty: 0.9,
            },
            error: 'Partial data',
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).toContain('causal-results');
        expect(result.highlightedPanels).toContain('guardian');
        expect(result.highlightedPanels).toContain('bayesian');
        expect(result.highlightedPanels).toContain('transparency');
        expect(result.highlightedPanels).toHaveLength(4);
    });

    // -----------------------------------------------------------------------
    // Clean response -> no highlights
    // -----------------------------------------------------------------------
    it('returns no highlights for a clean response with no issues', () => {
        const response = makeResponse({
            causalResult: {
                effect: -1.0,
                unit: 'percentage points',
                pValue: 0.25,
                confidenceInterval: [-3.0, 1.0],
                description: 'Not significant',
                refutationsPassed: 3,
                refutationsTotal: 3,
                refutationDetails: [],
                confoundersControlled: [],
                evidenceBase: 'observational',
                metaAnalysis: false,
                studies: 1,
                treatment: 'discount',
                outcome: 'churn',
            },
            guardianVerdict: 'approved',
            bayesianResult: {
                variable: 'churn_rate',
                priorMean: 0.1,
                priorStd: 0.05,
                posteriorMean: 0.12,
                posteriorStd: 0.04,
                confidenceLevel: 'high',
                interpretation: 'Confident',
                epistemicUncertainty: 0.1,
                aleatoricUncertainty: 0.1,
                totalUncertainty: 0.2,
            },
            error: null,
        });

        const result = computeHighlights(response);
        expect(result.highlightedPanels).toHaveLength(0);
        expect(Object.keys(result.highlightReasons)).toHaveLength(0);
    });
});
