/**
 * ExecutiveKPIPanel.tsx
 *
 * Comprehensive KPI dashboard for Executive View featuring:
 * - Key Performance Indicators with visual gauges
 * - Executive text summary of analysis
 * - Modular/filterable metrics
 * - Decision impact visualization
 */

import React, { useState } from 'react';
import type { QueryResponse, CausalAnalysisResult, BayesianBeliefState, GuardianDecision } from '../../types/carf';

interface ExecutiveKPIProps {
  queryResponse: QueryResponse | null;
  causalResult: CausalAnalysisResult | null;
  bayesianResult: BayesianBeliefState | null;
  guardianResult: GuardianDecision | null;
  onDrillDown?: (kpiId: string) => void;
}

interface KPIMetric {
  id: string;
  label: string;
  value: number | string;
  unit?: string;
  status: 'excellent' | 'good' | 'warning' | 'critical';
  trend?: 'up' | 'down' | 'stable';
  description: string;
  category: 'confidence' | 'quality' | 'compliance' | 'performance';
}

const statusColors = {
  excellent: 'bg-green-500',
  good: 'bg-blue-500',
  warning: 'bg-yellow-500',
  critical: 'bg-red-500',
};

const statusBgColors = {
  excellent: 'bg-green-50 border-green-200',
  good: 'bg-blue-50 border-blue-200',
  warning: 'bg-yellow-50 border-yellow-200',
  critical: 'bg-red-50 border-red-200',
};

const trendIcons = {
  up: '↑',
  down: '↓',
  stable: '→',
};

export const ExecutiveKPIPanel: React.FC<ExecutiveKPIProps> = ({
  queryResponse,
  causalResult,
  bayesianResult,
  guardianResult,
  onDrillDown,
}) => {
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  // Calculate KPI metrics from analysis results
  const calculateKPIs = (): KPIMetric[] => {
    const kpis: KPIMetric[] = [];

    // Domain Confidence KPI
    if (queryResponse?.domainConfidence) {
      const confidence = queryResponse.domainConfidence * 100;
      kpis.push({
        id: 'domain-confidence',
        label: 'Domain Confidence',
        value: Math.round(confidence),
        unit: '%',
        status: confidence >= 85 ? 'excellent' : confidence >= 70 ? 'good' : confidence >= 50 ? 'warning' : 'critical',
        description: `System confidence in ${queryResponse.domain} classification`,
        category: 'confidence',
      });
    }

    // Causal Effect KPI
    if (causalResult?.effect !== undefined) {
      const effectAbs = Math.abs(causalResult.effect);
      kpis.push({
        id: 'causal-effect',
        label: 'Causal Effect Size',
        value: causalResult.effect.toFixed(3),
        status: effectAbs >= 0.3 ? 'excellent' : effectAbs >= 0.1 ? 'good' : 'warning',
        trend: causalResult.effect > 0 ? 'up' : causalResult.effect < 0 ? 'down' : 'stable',
        description: `Treatment effect on outcome: ${causalResult.treatment} → ${causalResult.outcome}`,
        category: 'performance',
      });
    }

    // Refutation Tests KPI
    if (causalResult) {
      const passed = causalResult.refutationsPassed || 0;
      const total = causalResult.refutationsTotal || 0;
      const rate = total > 0 ? (passed / total) * 100 : 0;
      kpis.push({
        id: 'refutation-rate',
        label: 'Causal Robustness',
        value: `${passed}/${total}`,
        status: rate === 100 ? 'excellent' : rate >= 80 ? 'good' : rate >= 60 ? 'warning' : 'critical',
        description: 'Refutation tests passed - validates causal claim reliability',
        category: 'quality',
      });
    }

    // Epistemic Uncertainty KPI
    if (bayesianResult?.epistemicUncertainty !== undefined) {
      const epistemic = bayesianResult.epistemicUncertainty * 100;
      kpis.push({
        id: 'epistemic-uncertainty',
        label: 'Knowledge Gap',
        value: Math.round(epistemic),
        unit: '%',
        status: epistemic <= 15 ? 'excellent' : epistemic <= 30 ? 'good' : epistemic <= 50 ? 'warning' : 'critical',
        description: 'Reducible uncertainty - can be lowered with more data',
        category: 'quality',
      });
    }

    // Guardian Compliance KPI
    if (guardianResult) {
      const passed = guardianResult.policiesPassed || 0;
      const total = guardianResult.policiesTotal || 0;
      const rate = total > 0 ? (passed / total) * 100 : 100;
      kpis.push({
        id: 'policy-compliance',
        label: 'Policy Compliance',
        value: Math.round(rate),
        unit: '%',
        status: rate === 100 ? 'excellent' : rate >= 90 ? 'good' : rate >= 70 ? 'warning' : 'critical',
        description: `${passed} of ${total} governance policies passed`,
        category: 'compliance',
      });
    }

    // Risk Level KPI
    if (guardianResult?.riskLevel) {
      const riskMap: Record<string, { value: string; status: KPIMetric['status'] }> = {
        low: { value: 'LOW', status: 'excellent' },
        medium: { value: 'MEDIUM', status: 'warning' },
        high: { value: 'HIGH', status: 'critical' },
      };
      const riskInfo = riskMap[guardianResult.riskLevel.toLowerCase()] || riskMap.medium;
      kpis.push({
        id: 'risk-level',
        label: 'Risk Assessment',
        value: riskInfo.value,
        status: riskInfo.status,
        description: 'Overall risk level based on Guardian analysis',
        category: 'compliance',
      });
    }

    return kpis;
  };

  const kpis = calculateKPIs();
  const filteredKPIs = activeCategory ? kpis.filter(k => k.category === activeCategory) : kpis;
  const categories = [...new Set(kpis.map(k => k.category))];

  // Generate executive summary text
  const generateSummary = (): string => {
    if (!queryResponse) {
      return 'Submit a query to receive an executive summary of the analysis.';
    }

    const parts: string[] = [];

    // Domain context
    const domainConf = Math.round((queryResponse.domainConfidence || 0) * 100);
    parts.push(`The analysis classified this query as a **${queryResponse.domain?.toUpperCase()}** domain problem with ${domainConf}% confidence.`);

    // Causal findings
    if (causalResult) {
      const effect = causalResult.effect;
      const direction = effect > 0 ? 'positive' : effect < 0 ? 'negative' : 'neutral';
      const magnitude = Math.abs(effect) >= 0.3 ? 'strong' : Math.abs(effect) >= 0.1 ? 'moderate' : 'weak';
      parts.push(`Causal analysis reveals a **${magnitude} ${direction}** relationship (effect size: ${effect.toFixed(3)}) between ${causalResult.treatment || 'treatment'} and ${causalResult.outcome || 'outcome'}.`);

      if (causalResult.refutationsPassed !== undefined) {
        const reliability = causalResult.refutationsPassed === causalResult.refutationsTotal ? 'highly reliable' : 'reasonably reliable';
        parts.push(`This finding passed ${causalResult.refutationsPassed}/${causalResult.refutationsTotal} robustness tests, making it **${reliability}**.`);
      }
    }

    // Bayesian uncertainty
    if (bayesianResult) {
      const totalUncertainty = ((bayesianResult.epistemicUncertainty || 0) + (bayesianResult.aleatoricUncertainty || 0)) * 100;
      parts.push(`Total uncertainty in the analysis is ${Math.round(totalUncertainty)}%, with ${Math.round((bayesianResult.epistemicUncertainty || 0) * 100)}% being reducible through additional data collection.`);
    }

    // Guardian verdict
    if (guardianResult) {
      const verdict = queryResponse.guardianVerdict || 'pending';
      if (verdict === 'approved') {
        parts.push('**Recommendation**: This analysis is approved for decision-making.');
      } else if (verdict === 'requires_human_approval') {
        parts.push('**Action Required**: Human review is needed before proceeding with decisions based on this analysis.');
      } else {
        parts.push('**Warning**: Policy violations detected. Review Guardian feedback before proceeding.');
      }
    }

    return parts.join('\n\n');
  };

  return (
    <div className="space-y-6">
      {/* KPI Category Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-medium text-gray-500">Filter:</span>
        <button
          onClick={() => setActiveCategory(null)}
          className={`px-3 py-1 text-sm rounded-full transition-colors ${activeCategory === null ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
        >
          All KPIs
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1 text-sm rounded-full capitalize transition-colors ${activeCategory === cat ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {filteredKPIs.map(kpi => (
          <div
            key={kpi.id}
            onClick={() => onDrillDown?.(kpi.id)}
            className={`p-4 rounded-xl border cursor-pointer transition-all hover:shadow-md ${statusBgColors[kpi.status]}`}
          >
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">{kpi.category}</span>
              {kpi.trend && (
                <span className={`text-sm font-bold ${kpi.trend === 'up' ? 'text-green-600' : kpi.trend === 'down' ? 'text-red-600' : 'text-gray-500'
                  }`}>
                  {trendIcons[kpi.trend]}
                </span>
              )}
            </div>
            <div className="flex items-baseline gap-1 mb-1">
              <span className="text-2xl font-bold text-gray-900">{kpi.value}</span>
              {kpi.unit && <span className="text-sm text-gray-500">{kpi.unit}</span>}
            </div>
            <div className="text-sm font-medium text-gray-700 mb-2">{kpi.label}</div>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${statusColors[kpi.status]}`} />
              <span className="text-xs text-gray-500 capitalize">{kpi.status}</span>
            </div>
          </div>
        ))}

        {filteredKPIs.length === 0 && (
          <div className="col-span-full p-8 text-center text-gray-500 bg-gray-50 rounded-xl">
            No KPI data available. Run an analysis to generate metrics.
          </div>
        )}
      </div>

      {/* Executive Summary */}
      <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl p-6 border border-slate-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <span>📋</span> Executive Summary
          </h3>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-sm text-primary hover:text-primary/80 transition-colors"
          >
            {showDetails ? 'Hide Details' : 'Show Details'}
          </button>
        </div>
        <div className="prose prose-sm max-w-none text-gray-700">
          {generateSummary().split('\n\n').map((para, idx) => (
            <p key={idx} className="mb-3 last:mb-0" dangerouslySetInnerHTML={{
              __html: para.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            }} />
          ))}
        </div>

        {/* Detailed Breakdown (collapsible) */}
        {showDetails && queryResponse && (
          <div className="mt-6 pt-6 border-t border-slate-200 space-y-4">
            <h4 className="font-medium text-gray-900">Detailed Metrics</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Session ID:</span>
                <span className="ml-2 font-mono text-xs">{queryResponse.sessionId?.slice(0, 12)}...</span>
              </div>
              <div>
                <span className="text-gray-500">Domain Entropy:</span>
                <span className="ml-2">{((queryResponse.domainEntropy || 0) * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span className="text-gray-500">Analysis Method:</span>
                <span className="ml-2">{queryResponse.triggeredMethod || 'Not specified'}</span>
              </div>
              <div>
                <span className="text-gray-500">Human Review:</span>
                <span className={`ml-2 ${queryResponse.requiresHuman ? 'text-orange-600' : 'text-green-600'}`}>
                  {queryResponse.requiresHuman ? 'Required' : 'Not Required'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Decision Actions */}
      {queryResponse && (
        <div className="flex items-center gap-3 pt-4 border-t">
          <button className="flex-1 px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-colors">
            Export Report
          </button>
          <button className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors">
            Share Analysis
          </button>
          <button className="px-4 py-2 text-gray-500 hover:text-gray-700 transition-colors">
            <span className="text-xl">⚙️</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default ExecutiveKPIPanel;
