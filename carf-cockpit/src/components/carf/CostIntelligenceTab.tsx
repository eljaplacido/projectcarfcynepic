/**
 * CostIntelligenceTab — PRICE pillar visualization.
 *
 * KPI cards + recharts bar/pie charts for cost breakdown.
 * Board-aware: shows board context when selected.
 */

import React, { useEffect, useState } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend,
} from 'recharts';
import type { CostBreakdown } from '../../types/carf';
import { getCostAggregate, getCostROI } from '../../services/apiService';

const COLORS = ['#3B82F6', '#10B981', '#EF4444', '#F59E0B'];

interface CostIntelligenceTabProps {
    sessionId?: string;
    selectedBoardId?: string | null;
}

interface KPICardProps {
    label: string;
    value: string;
    subtitle?: string;
    color?: string;
}

const KPICard: React.FC<KPICardProps> = ({ label, value, subtitle, color = '#60A5FA' }) => (
    <div style={{
        padding: '16px',
        borderRadius: '8px',
        backgroundColor: '#1F2937',
        border: '1px solid #374151',
        flex: 1,
        minWidth: '150px',
    }}>
        <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            {label}
        </div>
        <div style={{ fontSize: '24px', fontWeight: 700, color, marginTop: '4px' }}>
            {value}
        </div>
        {subtitle && (
            <div style={{ fontSize: '11px', color: '#6B7280', marginTop: '2px' }}>{subtitle}</div>
        )}
    </div>
);

const CostIntelligenceTab: React.FC<CostIntelligenceTabProps> = ({ sessionId, selectedBoardId }) => {
    const [aggregate, setAggregate] = useState<Record<string, unknown> | null>(null);
    const [roi, setROI] = useState<Record<string, unknown> | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const [aggData, roiData] = await Promise.all([
                    getCostAggregate(),
                    getCostROI(),
                ]);
                if (!cancelled) {
                    setAggregate(aggData);
                    setROI(roiData);
                }
            } catch {
                // Governance may not be enabled
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, [sessionId, selectedBoardId]);

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', color: '#9CA3AF' }}>
                Loading cost intelligence...
            </div>
        );
    }

    const totalCost = (aggregate?.total_cost as number) || 0;
    const avgCost = (aggregate?.average_cost_per_query as number) || 0;
    const totalTokens = (aggregate?.total_tokens as number) || 0;
    const roiPct = (roi?.roi_percentage as number) || 0;

    // Bar chart data from cost by category
    const costByCategory = (aggregate?.cost_by_category as Record<string, number>) || {};
    const barData = Object.entries(costByCategory).map(([category, amount]) => ({
        name: category.charAt(0).toUpperCase() + category.slice(1),
        cost: Number(amount.toFixed(4)),
    }));

    // Pie chart data
    const pieData = barData.map((item, i) => ({
        name: item.name,
        value: item.cost,
        color: COLORS[i % COLORS.length],
    }));

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Board context indicator */}
            {selectedBoardId && (
                <div style={{
                    padding: '6px 12px', backgroundColor: '#1F2937', borderRadius: '6px',
                    border: '1px solid #374151', fontSize: '12px', color: '#9CA3AF',
                }}>
                    Viewing costs filtered by board
                </div>
            )}

            {/* KPI Cards */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <KPICard label="Total Cost" value={`$${totalCost.toFixed(4)}`} subtitle="All sessions" color="#3B82F6" />
                <KPICard label="Cost/Insight" value={`$${avgCost.toFixed(4)}`} subtitle="Average per query" color="#10B981" />
                <KPICard label="ROI" value={`${roiPct.toFixed(0)}%`} subtitle="vs manual analysis" color="#F59E0B" />
                <KPICard label="Tokens Used" value={totalTokens.toLocaleString()} subtitle="Input + Output" color="#8B5CF6" />
            </div>

            {/* Charts */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                {/* Bar Chart */}
                <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '16px', border: '1px solid #374151' }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '12px' }}>
                        Cost Breakdown by Category
                    </div>
                    {barData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={250}>
                            <BarChart data={barData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                <XAxis dataKey="name" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                                <YAxis tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '6px' }}
                                    labelStyle={{ color: '#D1D5DB' }}
                                />
                                <Bar dataKey="cost" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <div style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6B7280' }}>
                            No cost data yet. Run a query with governance enabled.
                        </div>
                    )}
                </div>

                {/* Pie Chart */}
                <div style={{ backgroundColor: '#1F2937', borderRadius: '8px', padding: '16px', border: '1px solid #374151' }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '12px' }}>
                        Cost Distribution
                    </div>
                    {pieData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={250}>
                            <PieChart>
                                <Pie
                                    data={pieData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={50}
                                    outerRadius={90}
                                    dataKey="value"
                                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                >
                                    {pieData.map((entry, idx) => (
                                        <Cell key={idx} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Legend />
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : (
                        <div style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6B7280' }}>
                            No cost data available.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CostIntelligenceTab;
