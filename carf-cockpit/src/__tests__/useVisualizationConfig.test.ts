import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useVisualizationConfig } from '../hooks/useVisualizationConfig';

// Mock the apiService
vi.mock('../services/apiService', () => ({
    getVisualizationConfig: vi.fn(),
}));

import { getVisualizationConfig } from '../services/apiService';
const mockGetVizConfig = vi.mocked(getVisualizationConfig);

describe('useVisualizationConfig', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('returns fallback config when domain is null', () => {
        const { result } = renderHook(() => useVisualizationConfig(null));
        expect(result.current.domainConfig.domain).toBe('disorder');
        expect(result.current.loading).toBe(false);
    });

    it('fetches config when domain is provided', async () => {
        mockGetVizConfig.mockResolvedValueOnce({
            domain: {
                domain: 'complicated', primary_chart: 'dag',
                secondary_charts: ['waterfall'], color_scheme: ['#3B82F6'],
                interaction_mode: 'explore', detail_level: 'detailed',
                recommended_panels: ['CausalDAG'],
            },
            context: {
                context: 'financial', chart_type: 'waterfall',
                color_scheme: ['#3B82F6'], kpi_templates: [],
                recommended_panels: [], title_template: 'Financial',
                insight_prompt: 'Evaluate.',
            },
        });

        const { result } = renderHook(() =>
            useVisualizationConfig('complicated', 'financial')
        );

        await waitFor(() => {
            expect(result.current.domainConfig.domain).toBe('complicated');
        });
        expect(mockGetVizConfig).toHaveBeenCalledWith('financial', 'complicated');
    });

    it('keeps fallback on API error', async () => {
        mockGetVizConfig.mockRejectedValueOnce(new Error('Network error'));

        const { result } = renderHook(() => useVisualizationConfig('complex'));

        await waitFor(() => {
            expect(result.current.error).toBeInstanceOf(Error);
        });
        // Fallback config still active
        expect(result.current.domainConfig.domain).toBe('disorder');
    });

    it('caches results for same domain+context', async () => {
        mockGetVizConfig.mockResolvedValue({
            domain: { domain: 'clear', primary_chart: 'bar', secondary_charts: [], color_scheme: ['#10B981'], interaction_mode: 'checklist', detail_level: 'summary', recommended_panels: [] },
            context: { context: 'general', chart_type: 'line', color_scheme: ['#6B7280'], kpi_templates: [], recommended_panels: [], title_template: '', insight_prompt: '' },
        });

        const { result, rerender } = renderHook(
            ({ domain }) => useVisualizationConfig(domain),
            { initialProps: { domain: 'clear' as const } }
        );

        await waitFor(() => expect(result.current.domainConfig.domain).toBe('clear'));
        expect(mockGetVizConfig).toHaveBeenCalledTimes(1);

        // Re-render with same props should use cache
        rerender({ domain: 'clear' as const });
        expect(mockGetVizConfig).toHaveBeenCalledTimes(1); // no new call
    });
});
