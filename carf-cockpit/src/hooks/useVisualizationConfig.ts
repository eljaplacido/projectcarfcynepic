/**
 * useVisualizationConfig — fetches and caches domain+context visualization config.
 *
 * Data flow:
 *   queryResponse.domain  ─────────────────┐
 *   selectedScenario → context detection ───┤
 *                                           ▼
 *                              GET /api/visualization-config?domain=X&context=Y
 *                                           │
 *                                           ▼
 *                              { domain: CynefinVizConfig, context: ContextualVizConfig }
 */

import { useState, useEffect, useRef } from 'react';
import { getVisualizationConfig } from '../services/apiService';
import type { CynefinVizConfig, ContextualVizConfig } from '../services/apiService';
import type { CynefinDomain } from '../types/carf';

// Hardcoded fallbacks so the UI never breaks if the backend is down
const FALLBACK_DOMAIN_CONFIG: CynefinVizConfig = {
    domain: 'disorder',
    primary_chart: 'radar',
    secondary_charts: [],
    color_scheme: ['#9CA3AF', '#6B7280', '#F3F4F6'],
    interaction_mode: 'triage',
    detail_level: 'summary',
    recommended_panels: ['CynefinRouter'],
};

const FALLBACK_CONTEXT_CONFIG: ContextualVizConfig = {
    context: 'general',
    chart_type: 'line',
    color_scheme: ['#6B7280', '#374151', '#9CA3AF', '#F3F4F6'],
    kpi_templates: [
        { name: 'Impact Score', unit: '/10', trend: 'up_good' },
        { name: 'Confidence', unit: '%', trend: 'up_good' },
    ],
    recommended_panels: ['GeneralSummary'],
    title_template: 'Analysis Overview',
    insight_prompt: 'Provide a general overview.',
};

export interface VizConfig {
    domainConfig: CynefinVizConfig;
    contextConfig: ContextualVizConfig;
    loading: boolean;
    error: Error | null;
}

export function useVisualizationConfig(
    domain: CynefinDomain | null,
    context: string = 'general'
): VizConfig {
    const [domainConfig, setDomainConfig] = useState<CynefinVizConfig>(FALLBACK_DOMAIN_CONFIG);
    const [contextConfig, setContextConfig] = useState<ContextualVizConfig>(FALLBACK_CONTEXT_CONFIG);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const cacheRef = useRef<Record<string, { domain: CynefinVizConfig; context: ContextualVizConfig }>>({});

    useEffect(() => {
        if (!domain) return;

        const cacheKey = `${domain}:${context}`;
        if (cacheRef.current[cacheKey]) {
            setDomainConfig(cacheRef.current[cacheKey].domain);
            setContextConfig(cacheRef.current[cacheKey].context);
            return;
        }

        let cancelled = false;
        setLoading(true);

        getVisualizationConfig(context, domain)
            .then((response) => {
                if (cancelled) return;
                const domConf = response.domain as CynefinVizConfig;
                const ctxConf = response.context as ContextualVizConfig;
                setDomainConfig(domConf);
                setContextConfig(ctxConf);
                cacheRef.current[cacheKey] = { domain: domConf, context: ctxConf };
            })
            .catch((err) => {
                if (cancelled) return;
                setError(err);
                // Keep fallback configs — UI never breaks
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => { cancelled = true; };
    }, [domain, context]);

    return { domainConfig, contextConfig, loading, error };
}
