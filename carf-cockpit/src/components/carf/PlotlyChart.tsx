/**
 * PlotlyChart — Unified wrapper for Plotly.js chart types.
 *
 * Data flow mapping:
 *   chartType="waterfall" + data from queryResponse.causalResult
 *     → causalResult.effect, treatment, outcome, confidenceInterval
 *   chartType="radar" + data from queryResponse.domainScores
 *     → domainScores: Record<CynefinDomain, number>
 *   chartType="sankey" + data from queryResponse.causalResult
 *     → causalResult.confoundersControlled, treatment, outcome
 */

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import type { Data, Layout } from 'plotly.js';

export interface PlotlyChartProps {
    chartType: 'waterfall' | 'radar' | 'sankey' | 'gauge';
    data: Record<string, unknown>;
    colorScheme?: string[];
    title?: string;
    height?: number;
    darkMode?: boolean;
}

const PlotlyChart: React.FC<PlotlyChartProps> = ({
    chartType,
    data,
    colorScheme = ['#3B82F6', '#1D4ED8', '#6366F1'],
    title,
    height = 300,
    darkMode = false,
}) => {
    const bgColor = darkMode ? '#1e293b' : '#ffffff';
    const textColor = darkMode ? '#e2e8f0' : '#1e293b';
    const gridColor = darkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';

    const { plotData, layout } = useMemo(() => {
        let plotData: Data[] = [];
        const baseLayout: Partial<Layout> = {
            title: title ? { text: title, font: { color: textColor, size: 14 } } : undefined,
            height,
            margin: { l: 50, r: 30, t: title ? 40 : 20, b: 40 },
            paper_bgcolor: bgColor,
            plot_bgcolor: bgColor,
            font: { color: textColor },
        };

        switch (chartType) {
            case 'waterfall': {
                const measures = (data.measures as string[]) || ['relative', 'relative', 'total'];
                const x = (data.labels as string[]) || ['Treatment', 'Confounders', 'Net Effect'];
                const y = (data.values as number[]) || [0, 0, 0];
                plotData = [{
                    type: 'waterfall',
                    x, y,
                    measure: measures,
                    connector: { line: { color: colorScheme[1] } },
                    increasing: { marker: { color: colorScheme[0] } },
                    decreasing: { marker: { color: '#EF4444' } },
                    totals: { marker: { color: colorScheme[2] } },
                }];
                break;
            }
            case 'radar': {
                const categories = (data.categories as string[]) || [];
                const values = (data.values as number[]) || [];
                plotData = [{
                    type: 'scatterpolar',
                    r: [...values, values[0]], // close the polygon
                    theta: [...categories, categories[0]],
                    fill: 'toself',
                    fillcolor: `${colorScheme[0]}33`,
                    line: { color: colorScheme[0] },
                }];
                Object.assign(baseLayout, {
                    polar: {
                        radialaxis: { visible: true, range: [0, 1], gridcolor: gridColor },
                        bgcolor: bgColor,
                    },
                });
                break;
            }
            case 'sankey': {
                const nodes = (data.nodes as string[]) || [];
                const sources = (data.sources as number[]) || [];
                const targets = (data.targets as number[]) || [];
                const flowValues = (data.flowValues as number[]) || [];
                plotData = [{
                    type: 'sankey',
                    orientation: 'h',
                    node: {
                        label: nodes,
                        color: nodes.map((_, i) => colorScheme[i % colorScheme.length]),
                    },
                    link: { source: sources, target: targets, value: flowValues },
                }] as Data[];
                break;
            }
            case 'gauge': {
                const value = (data.value as number) || 0;
                const maxVal = (data.max as number) || 100;
                const label = (data.label as string) || 'Score';
                plotData = [{
                    type: 'indicator',
                    mode: 'gauge+number',
                    value,
                    title: { text: label, font: { color: textColor } },
                    gauge: {
                        axis: { range: [0, maxVal], tickcolor: textColor },
                        bar: { color: colorScheme[0] },
                        bgcolor: bgColor,
                        bordercolor: gridColor,
                        steps: [
                            { range: [0, maxVal * 0.33], color: '#FEF2F2' },
                            { range: [maxVal * 0.33, maxVal * 0.66], color: '#FEF9C3' },
                            { range: [maxVal * 0.66, maxVal], color: '#D1FAE5' },
                        ],
                    },
                }] as Data[];
                break;
            }
        }

        return { plotData, layout: baseLayout as Layout };
    }, [chartType, data, colorScheme, title, height, bgColor, textColor, gridColor]);

    return (
        <Plot
            data={plotData}
            layout={layout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
        />
    );
};

export default PlotlyChart;
