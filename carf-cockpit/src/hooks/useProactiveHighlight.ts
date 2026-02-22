/**
 * useProactiveHighlight
 *
 * Analyzes a QueryResponse and returns a list of panels that should be
 * visually highlighted, together with the reason for each highlight.
 *
 * Rules:
 *   1. Low causal p-value (< 0.05)          -> highlight "causal-results"
 *   2. Guardian verdict rejected             -> highlight "guardian" with warning
 *   3. High Bayesian uncertainty (> 0.7)     -> highlight "bayesian"
 *   4. Missing / incomplete data indicators  -> highlight "transparency"
 */

import { useMemo } from 'react';
import type { QueryResponse } from '../types/carf';

export interface ProactiveHighlightResult {
    highlightedPanels: string[];
    highlightReasons: Record<string, string>;
}

/** Pure function so it can be tested without React. */
export function computeHighlights(
    queryResponse: QueryResponse | null | undefined,
): ProactiveHighlightResult {
    const highlightedPanels: string[] = [];
    const highlightReasons: Record<string, string> = {};

    if (!queryResponse) {
        return { highlightedPanels, highlightReasons };
    }

    // 1. Low causal p-value -> highlight causal results panel
    const pValue = queryResponse.causalResult?.pValue;
    if (pValue !== null && pValue !== undefined && pValue < 0.05) {
        highlightedPanels.push('causal-results');
        highlightReasons['causal-results'] =
            `Statistically significant causal effect detected (p = ${pValue.toFixed(4)})`;
    }

    // 2. Guardian rejected -> highlight guardian panel with warning
    if (queryResponse.guardianVerdict === 'rejected') {
        highlightedPanels.push('guardian');
        highlightReasons['guardian'] =
            'Guardian policy layer rejected the proposed action — review required';
    }

    // 3. High Bayesian uncertainty -> highlight Bayesian panel
    const totalUncertainty = queryResponse.bayesianResult?.totalUncertainty;
    if (totalUncertainty !== null && totalUncertainty !== undefined && totalUncertainty > 0.7) {
        highlightedPanels.push('bayesian');
        highlightReasons['bayesian'] =
            `High uncertainty detected (${(totalUncertainty * 100).toFixed(0)}%) — Bayesian estimates may need more data`;
    }

    // 4. Missing data indicators -> highlight transparency panel
    const hasMissingData =
        queryResponse.error !== null ||
        (queryResponse.causalResult !== null &&
            queryResponse.causalResult.pValue === null) ||
        (queryResponse.reasoningChain.length === 0 && queryResponse.response === null);

    if (hasMissingData) {
        highlightedPanels.push('transparency');
        highlightReasons['transparency'] =
            'Incomplete or missing data detected — check transparency panel for details';
    }

    return { highlightedPanels, highlightReasons };
}

/**
 * React hook wrapping the pure computation with memoisation.
 */
export function useProactiveHighlight(
    queryResponse: QueryResponse | null | undefined,
): ProactiveHighlightResult {
    return useMemo(() => computeHighlights(queryResponse), [queryResponse]);
}

export default useProactiveHighlight;
