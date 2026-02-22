/**
 * ExecutiveKPIPanel.tsx
 *
 * Comprehensive KPI dashboard for Executive View featuring:
 * - Key Performance Indicators with visual gauges
 * - Executive text summary of analysis
 * - Modular/filterable metrics
 * - Decision impact visualization
 * - Adaptive visualization: KPI Cards, Bar Chart, Pie Chart (Phase 6A)
 * - Enhanced actionable insights with prioritized checklist (Phase 6B)
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import type { QueryResponse, CausalAnalysisResult, BayesianBeliefState, GuardianDecision } from '../../types/carf';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ExecutiveKPIProps {
  queryResponse: QueryResponse | null;
  causalResult: CausalAnalysisResult | null;
  bayesianResult: BayesianBeliefState | null;
  guardianResult: GuardianDecision | null;
  onDrillDown?: (kpiId: string) => void;
  context?: string; // Analysis context (e.g., 'sustainability')
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

/** Phase 6B: Action item effort levels and linking */
type ActionEffort = 'quick-win' | 'medium-effort' | 'strategic';

interface ActionItem {
  id: string;
  label: string;
  effort: ActionEffort;
  checked: boolean;
  drillDownPanel?: string; // Panel ID to navigate to
}

/** Phase 6B: Roadmap step */
interface RoadmapStep {
  number: number;
  title: string;
  description: string;
  panelLink?: string;
}

/** Phase 6A: Supported chart types */
type ChartType = 'cards' | 'bar' | 'pie';

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
  up: '\u2191',
  down: '\u2193',
  stable: '\u2192',
};

const PIE_COLORS = ['#22c55e', '#3b82f6', '#eab308', '#ef4444', '#8b5cf6', '#06b6d4'];

const effortBadgeStyles: Record<ActionEffort, string> = {
  'quick-win': 'bg-green-100 text-green-800',
  'medium-effort': 'bg-yellow-100 text-yellow-800',
  'strategic': 'bg-purple-100 text-purple-800',
};

const effortLabels: Record<ActionEffort, string> = {
  'quick-win': 'Quick Win',
  'medium-effort': 'Medium Effort',
  'strategic': 'Strategic',
};

// Helper function for safe percentage display
const safePercentage = (value: number | undefined | null, decimals = 0): number => {
  if (value === undefined || value === null || isNaN(value)) {
    return 0;
  }
  return Number((value * 100).toFixed(decimals));
};

// Helper to determine score out of 10
const scoreOutOfTen = (value: number | undefined | null): number => {
  if (value === undefined || value === null || isNaN(value)) {
    return 0;
  }
  return Math.round(value * 10);
};

/**
 * Phase 6A: Determine the best chart type based on the data context.
 * - If most KPIs are in the same category, it is a "distribution" scenario -> pie
 * - If there are multiple categories being compared, it is a "comparison" scenario -> bar
 * - Default to cards
 */
const autoSelectChartType = (kpis: KPIMetric[]): ChartType => {
  if (kpis.length === 0) return 'cards';
  const categoryCounts: Record<string, number> = {};
  for (const kpi of kpis) {
    categoryCounts[kpi.category] = (categoryCounts[kpi.category] || 0) + 1;
  }
  const uniqueCategories = Object.keys(categoryCounts).length;
  // Distribution: many items mostly in one category
  const maxInSingleCat = Math.max(...Object.values(categoryCounts));
  if (uniqueCategories === 1 && kpis.length >= 3) return 'pie';
  if (maxInSingleCat / kpis.length >= 0.7 && kpis.length >= 4) return 'pie';
  // Comparison: items across multiple categories
  if (uniqueCategories >= 2 && kpis.length >= 3) return 'bar';
  return 'cards';
};

/**
 * Phase 6B: Generate action items from the query response data.
 */
const generateActionItems = (
  queryResponse: QueryResponse | null,
  causalResult: CausalAnalysisResult | null,
  bayesianResult: BayesianBeliefState | null,
  guardianResult: GuardianDecision | null,
): ActionItem[] => {
  const items: ActionItem[] = [];

  if (!queryResponse) return items;

  // Quick wins based on available data
  if (queryResponse.domainConfidence != null && queryResponse.domainConfidence < 0.7) {
    items.push({
      id: 'action-improve-confidence',
      label: 'Provide additional context to improve domain classification confidence',
      effort: 'quick-win',
      checked: false,
      drillDownPanel: 'cynefin-panel',
    });
  }

  if (guardianResult) {
    const failedPolicies = guardianResult.policies?.filter(p => p.status === 'failed') || [];
    if (failedPolicies.length > 0) {
      items.push({
        id: 'action-fix-policies',
        label: `Address ${failedPolicies.length} failed policy violation(s) in Guardian`,
        effort: 'quick-win',
        checked: false,
        drillDownPanel: 'guardian-panel',
      });
    }
    if (guardianResult.requiresHumanApproval) {
      items.push({
        id: 'action-human-review',
        label: 'Complete required human approval for this analysis',
        effort: 'medium-effort',
        checked: false,
        drillDownPanel: 'guardian-panel',
      });
    }
  }

  // Medium effort items from analysis quality
  if (causalResult) {
    const passed = causalResult.refutationsPassed ?? 0;
    const total = causalResult.refutationsTotal ?? 0;
    if (total > 0 && passed < total) {
      items.push({
        id: 'action-refutation-gaps',
        label: `Investigate ${total - passed} failed refutation test(s) to strengthen causal claims`,
        effort: 'medium-effort',
        checked: false,
        drillDownPanel: 'causal-results',
      });
    }
  }

  if (bayesianResult) {
    const epistemic = bayesianResult.epistemicUncertainty || 0;
    if (epistemic > 0.3) {
      items.push({
        id: 'action-reduce-uncertainty',
        label: 'Collect additional data to reduce epistemic uncertainty',
        effort: 'medium-effort',
        checked: false,
        drillDownPanel: 'bayesian-panel',
      });
    }
  }

  // Strategic items
  if (queryResponse.domain === 'complex' || queryResponse.domain === 'chaotic') {
    items.push({
      id: 'action-strategic-probing',
      label: `Design safe-to-fail probes for ${queryResponse.domain} domain scenario`,
      effort: 'strategic',
      checked: false,
      drillDownPanel: 'cynefin-panel',
    });
  }

  if (causalResult && Math.abs(causalResult.effect) >= 0.3) {
    items.push({
      id: 'action-intervention-plan',
      label: 'Develop an intervention plan based on the strong causal effect identified',
      effort: 'strategic',
      checked: false,
      drillDownPanel: 'causal-results',
    });
  }

  // Sort by effort: quick-win first, then medium, then strategic
  const effortOrder: Record<ActionEffort, number> = { 'quick-win': 0, 'medium-effort': 1, 'strategic': 2 };
  items.sort((a, b) => effortOrder[a.effort] - effortOrder[b.effort]);

  return items;
};

/**
 * Phase 6B: Generate a roadmap from query response data.
 */
const generateRoadmap = (
  queryResponse: QueryResponse | null,
  causalResult: CausalAnalysisResult | null,
  bayesianResult: BayesianBeliefState | null,
  guardianResult: GuardianDecision | null,
): RoadmapStep[] => {
  const steps: RoadmapStep[] = [];
  if (!queryResponse) return steps;

  steps.push({
    number: 1,
    title: 'Review Domain Classification',
    description: `Analysis classified as ${queryResponse.domain?.toUpperCase() || 'UNKNOWN'} domain with ${Math.round((queryResponse.domainConfidence || 0) * 100)}% confidence.`,
    panelLink: 'cynefin-panel',
  });

  if (causalResult) {
    const effectDirection = causalResult.effect > 0 ? 'positive' : causalResult.effect < 0 ? 'negative' : 'neutral';
    steps.push({
      number: 2,
      title: 'Validate Causal Findings',
      description: `A ${effectDirection} causal effect (${causalResult.effect.toFixed(3)}) was found. Verify ${causalResult.refutationsPassed}/${causalResult.refutationsTotal} refutation results.`,
      panelLink: 'causal-results',
    });
  }

  if (bayesianResult) {
    steps.push({
      number: steps.length + 1,
      title: 'Assess Uncertainty',
      description: `Epistemic uncertainty is ${Math.round((bayesianResult.epistemicUncertainty || 0) * 100)}%. ${bayesianResult.recommendedProbe ? `Recommended probe: ${bayesianResult.recommendedProbe}` : 'Consider additional data collection.'}`,
      panelLink: 'bayesian-panel',
    });
  }

  if (guardianResult) {
    const verdict = queryResponse.guardianVerdict || 'pending';
    steps.push({
      number: steps.length + 1,
      title: 'Confirm Guardian Compliance',
      description: `Guardian verdict: ${verdict}. ${guardianResult.requiresHumanApproval ? 'Human approval is required.' : 'No additional approval needed.'}`,
      panelLink: 'guardian-panel',
    });
  }

  steps.push({
    number: steps.length + 1,
    title: 'Execute Decision',
    description: queryResponse.guardianVerdict === 'approved'
      ? 'Analysis is approved. Proceed with implementing recommendations.'
      : 'Review all findings and obtain necessary approvals before proceeding.',
  });

  return steps;
};

export const ExecutiveKPIPanel: React.FC<ExecutiveKPIProps> = ({
  queryResponse,
  causalResult,
  bayesianResult,
  guardianResult,
  onDrillDown,
  context = 'general'
}) => {
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [vizConfig, setVizConfig] = useState<any>(null);
  const [guardianStatus, setGuardianStatus] = useState<{
    compliance_percentage: number;
    policies_active: number;
    risk_level: string;
  } | null>(null);
  const [insights, setInsights] = useState<any[]>([]);

  // Phase 6A: Chart type state
  const [chartType, setChartType] = useState<ChartType>('cards');
  const [autoDetected, setAutoDetected] = useState<ChartType>('cards');

  // Phase 6B: Action items checklist state
  const [actionChecks, setActionChecks] = useState<Record<string, boolean>>({});

  // Fetch visualization config on mount or context change
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/config/visualization?context=${context}`);
        if (res.ok) {
          const data = await res.json();
          setVizConfig(data);
        }
      } catch (err) {
        console.error("Failed to fetch viz config", err);
        setVizConfig(null);
      }
    };
    fetchConfig();
  }, [context]);

  // Fetch Guardian status for compliance data
  useEffect(() => {
    const fetchGuardianStatus = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/guardian/status`);
        if (res.ok) {
          const data = await res.json();
          setGuardianStatus(data);
        }
      } catch (err) {
        console.error("Failed to fetch guardian status", err);
      }
    };
    fetchGuardianStatus();
  }, []);

  // Fetch insights for executive persona
  useEffect(() => {
    const fetchInsights = async () => {
      if (!queryResponse) return;
      try {
        const res = await fetch(`${API_BASE_URL}/insights/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            persona: 'executive',
            domain: queryResponse.domain,
            domain_confidence: queryResponse.domainConfidence,
            domain_entropy: queryResponse.domainEntropy,
            has_causal_result: !!causalResult,
            causal_effect: causalResult?.effect,
            refutation_pass_rate: causalResult?.refutationsTotal
              ? (causalResult.refutationsPassed || 0) / causalResult.refutationsTotal
              : null,
            has_bayesian_result: !!bayesianResult,
            epistemic_uncertainty: bayesianResult?.epistemicUncertainty,
            aleatoric_uncertainty: bayesianResult?.aleatoricUncertainty,
            guardian_verdict: queryResponse.guardianVerdict,
            policies_passed: guardianResult?.policiesPassed || 0,
            policies_total: guardianResult?.policiesTotal || 0,
          })
        });
        if (res.ok) {
          const data = await res.json();
          setInsights(data.insights || []);
        }
      } catch (err) {
        console.error("Failed to fetch insights", err);
      }
    };
    fetchInsights();
  }, [queryResponse, causalResult, bayesianResult, guardianResult]);

  // Dynamic KPI Value Mapper
  const getDynamicValue = (kpiName: string): Partial<KPIMetric> => {
    // Map abstract KPI names to concrete data points based on available results
    const defaults = { value: 0, status: 'warning' as const, trend: 'stable' as const };

    if (context === 'sustainability') {
      if (kpiName === 'Total Reduction') {
        const effect = causalResult?.effect || 0;
        return {
          value: Math.abs(effect * 1000).toFixed(1), // Mock scaling
          status: effect < 0 ? 'excellent' : 'warning',
          trend: effect < 0 ? 'down' : 'up'
        };
      }
      if (kpiName === 'Supplier Coverage') return { value: 85, status: 'good', trend: 'up' };
      if (kpiName === 'Carbon Intensity') return { value: 1.2, status: 'good', trend: 'down' };
    }

    if (context === 'financial') {
      if (kpiName === 'ROI') return { value: 24, status: 'excellent', trend: 'up' };
      if (kpiName === 'Payback Period') return { value: 18, status: 'good', trend: 'down' };
    }

    // Default Fallbacks (existing logic)
    if (kpiName === 'Domain Confidence') {
      const conf = (queryResponse?.domainConfidence || 0) * 100;
      return {
        value: Math.round(conf),
        status: conf >= 85 ? 'excellent' : conf >= 70 ? 'good' : 'warning',
        trend: 'stable'
      };
    }

    return defaults;
  };

  // Calculate KPI metrics from analysis results
  const calculateKPIs = (): KPIMetric[] => {
    // Dynamic KPIs from Config
    const dynamicKPIs: KPIMetric[] = vizConfig?.kpi_templates?.map((tpl: any, idx: number) => {
      const data = getDynamicValue(tpl.name);
      return {
        id: `kpi-dyn-${idx}`,
        label: tpl.name,
        value: data.value as number | string,
        unit: tpl.unit,
        status: data.status as KPIMetric['status'],
        trend: data.trend as KPIMetric['trend'],
        description: tpl.description || tpl.name,
        category: 'performance'
      };
    }) || [];

    // Core KPIs (Always visible)
    const coreKPIs: KPIMetric[] = [];

    // Overall Quality Score (0-10) - computed from all available metrics
    const computeOverallScore = (): number => {
      const scores: number[] = [];
      if (queryResponse?.domainConfidence != null) {
        scores.push(queryResponse.domainConfidence);
      }
      if (causalResult?.refutationsTotal && causalResult.refutationsTotal > 0) {
        scores.push((causalResult.refutationsPassed || 0) / causalResult.refutationsTotal);
      }
      if (guardianStatus?.compliance_percentage != null) {
        scores.push(guardianStatus.compliance_percentage / 100);
      }
      if (bayesianResult?.epistemicUncertainty != null) {
        scores.push(1 - bayesianResult.epistemicUncertainty); // Lower uncertainty = higher score
      }
      if (scores.length === 0) return 0;
      const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
      return scoreOutOfTen(avg);
    };

    const overallScore = computeOverallScore();
    coreKPIs.push({
      id: 'overall-score',
      label: 'Overall Score',
      value: `${overallScore}/10`,
      status: overallScore >= 8 ? 'excellent' : overallScore >= 6 ? 'good' : overallScore >= 4 ? 'warning' : 'critical',
      description: 'Composite score based on confidence, quality, and compliance',
      category: 'confidence',
    });

    // Domain Confidence (Core) - with null-safe handling
    const confidence = safePercentage(queryResponse?.domainConfidence);
    coreKPIs.push({
      id: 'domain-confidence',
      label: 'Domain Confidence',
      value: confidence > 0 ? confidence : 'N/A',
      unit: confidence > 0 ? '%' : '',
      status: confidence >= 85 ? 'excellent' : confidence >= 70 ? 'good' : confidence >= 50 ? 'warning' : 'critical',
      description: queryResponse?.domain
        ? `System confidence in ${queryResponse.domain} classification`
        : 'Domain classification confidence',
      category: 'confidence',
    });

    // Risk Level (Core) - with fallback
    const riskLevel = guardianResult?.riskLevel || guardianStatus?.risk_level || 'unknown';
    const riskMap: Record<string, { value: string; status: KPIMetric['status'] }> = {
      low: { value: 'LOW', status: 'excellent' },
      medium: { value: 'MEDIUM', status: 'warning' },
      high: { value: 'HIGH', status: 'critical' },
      unknown: { value: 'N/A', status: 'warning' },
    };
    const riskInfo = riskMap[riskLevel.toLowerCase()] || riskMap.unknown;
    coreKPIs.push({
      id: 'risk-level',
      label: 'Risk Assessment',
      value: riskInfo.value,
      status: riskInfo.status,
      description: 'Overall risk level based on Guardian analysis',
      category: 'compliance',
    });

    // Compliance Score - from guardian status
    const complianceScore = guardianStatus?.compliance_percentage ??
      (guardianResult?.policiesTotal && guardianResult.policiesTotal > 0
        ? ((guardianResult.policiesPassed || 0) / guardianResult.policiesTotal) * 100
        : null);
    coreKPIs.push({
      id: 'compliance-score',
      label: 'Policy Compliance',
      value: complianceScore != null ? Math.round(complianceScore) : 'N/A',
      unit: complianceScore != null ? '%' : '',
      status: complianceScore != null
        ? (complianceScore >= 100 ? 'excellent' : complianceScore >= 80 ? 'good' : complianceScore >= 60 ? 'warning' : 'critical')
        : 'warning',
      description: 'Guardian policy compliance rate',
      category: 'compliance',
    });

    // If no dynamic config, fall back to some defaults if available results
    if (dynamicKPIs.length === 0) {
      // Causal Effect KPI
      if (causalResult?.effect !== undefined && causalResult.effect !== null) {
        const effectAbs = Math.abs(causalResult.effect);
        coreKPIs.push({
          id: 'causal-effect',
          label: 'Causal Effect Size',
          value: causalResult.effect.toFixed(3),
          status: effectAbs >= 0.3 ? 'excellent' : effectAbs >= 0.1 ? 'good' : 'warning',
          trend: causalResult.effect > 0 ? 'up' : causalResult.effect < 0 ? 'down' : 'stable',
          description: `Treatment effect: ${causalResult.treatment || 'treatment'} -> ${causalResult.outcome || 'outcome'}`,
          category: 'performance',
        });
      }

      // Refutation (fallback)
      if (causalResult) {
        const passed = causalResult.refutationsPassed ?? 0;
        const total = causalResult.refutationsTotal ?? 0;
        const rate = total > 0 ? (passed / total) * 100 : 0;
        coreKPIs.push({
          id: 'refutation-rate',
          label: 'Causal Robustness',
          value: total > 0 ? `${passed}/${total}` : 'N/A',
          status: total === 0 ? 'warning' : (rate === 100 ? 'excellent' : rate >= 80 ? 'good' : rate >= 60 ? 'warning' : 'critical'),
          description: 'Refutation tests passed',
          category: 'quality',
        });
      }

      // Uncertainty KPI from Bayesian
      if (bayesianResult) {
        const epistemic = safePercentage(bayesianResult.epistemicUncertainty);
        coreKPIs.push({
          id: 'uncertainty',
          label: 'Reducible Uncertainty',
          value: epistemic > 0 ? epistemic : 'N/A',
          unit: epistemic > 0 ? '%' : '',
          status: epistemic < 20 ? 'excellent' : epistemic < 40 ? 'good' : epistemic < 60 ? 'warning' : 'critical',
          trend: 'stable',
          description: 'Epistemic uncertainty that can be reduced with more data',
          category: 'quality',
        });
      }
    }

    return [...dynamicKPIs, ...coreKPIs];
  };

  const kpis = calculateKPIs();
  const filteredKPIs = activeCategory ? kpis.filter(k => k.category === activeCategory) : kpis;
  const categories = [...new Set(kpis.map(k => k.category))];

  // Phase 6A: Auto-detect optimal chart type when KPIs change
  useEffect(() => {
    const detected = autoSelectChartType(filteredKPIs);
    setAutoDetected(detected);
  }, [filteredKPIs.length, activeCategory]);

  // Phase 6B: Generate action items from data
  const actionItems = useMemo(
    () => generateActionItems(queryResponse, causalResult, bayesianResult, guardianResult),
    [queryResponse, causalResult, bayesianResult, guardianResult]
  );

  // Phase 6B: Generate roadmap
  const roadmapSteps = useMemo(
    () => generateRoadmap(queryResponse, causalResult, bayesianResult, guardianResult),
    [queryResponse, causalResult, bayesianResult, guardianResult]
  );

  const toggleActionCheck = (id: string) => {
    setActionChecks(prev => ({ ...prev, [id]: !prev[id] }));
  };

  // Phase 6A: Prepare chart data for recharts
  const barChartData = filteredKPIs
    .filter(kpi => typeof kpi.value === 'number')
    .map(kpi => ({
      name: kpi.label,
      value: kpi.value as number,
      status: kpi.status,
    }));

  const pieChartData = filteredKPIs
    .filter(kpi => typeof kpi.value === 'number' && (kpi.value as number) > 0)
    .map(kpi => ({
      name: kpi.label,
      value: kpi.value as number,
    }));

  // Generate executive summary text
  const generateSummary = (): string => {
    if (!queryResponse) {
      return 'Submit a query to receive an executive summary of the analysis.';
    }

    const parts: string[] = [];

    // Visualize title if available
    if (vizConfig?.title_template) {
      parts.push(`## ${vizConfig.title_template}`);
    }

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

  // Phase 6A: Render the chart type selector icon bar
  const renderChartTypeSelector = () => (
    <div className="flex items-center gap-1" data-testid="chart-type-selector">
      <span className="text-xs text-gray-400 mr-1">View:</span>
      <button
        onClick={() => setChartType('cards')}
        className={`p-1.5 rounded transition-colors ${chartType === 'cards' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}
        title="KPI Cards"
        aria-label="KPI Cards view"
        data-testid="chart-type-cards"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <rect x="1" y="1" width="6" height="6" rx="1" />
          <rect x="9" y="1" width="6" height="6" rx="1" />
          <rect x="1" y="9" width="6" height="6" rx="1" />
          <rect x="9" y="9" width="6" height="6" rx="1" />
        </svg>
      </button>
      <button
        onClick={() => setChartType('bar')}
        className={`p-1.5 rounded transition-colors ${chartType === 'bar' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}
        title="Bar Chart"
        aria-label="Bar Chart view"
        data-testid="chart-type-bar"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <rect x="1" y="8" width="3" height="7" rx="0.5" />
          <rect x="5" y="4" width="3" height="11" rx="0.5" />
          <rect x="9" y="6" width="3" height="9" rx="0.5" />
          <rect x="13" y="2" width="3" height="13" rx="0.5" />
        </svg>
      </button>
      <button
        onClick={() => setChartType('pie')}
        className={`p-1.5 rounded transition-colors ${chartType === 'pie' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}
        title="Pie Chart"
        aria-label="Pie Chart view"
        data-testid="chart-type-pie"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 1a7 7 0 1 0 7 7h-7V1z" />
          <path d="M9 0v7h7a7 7 0 0 0-7-7z" opacity="0.5" />
        </svg>
      </button>
      {autoDetected !== 'cards' && chartType === 'cards' && (
        <button
          onClick={() => setChartType(autoDetected)}
          className="ml-1 text-xs text-primary hover:text-primary/80 underline"
          title={`Auto-detected: ${autoDetected} chart would work well`}
        >
          Try {autoDetected}
        </button>
      )}
    </div>
  );

  // Phase 6A: Render KPI cards (default)
  const renderKPICards = () => (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4" data-testid="kpi-cards-view">
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
  );

  // Phase 6A: Render bar chart
  const renderBarChart = () => {
    if (barChartData.length === 0) {
      return (
        <div className="p-8 text-center text-gray-500 bg-gray-50 rounded-xl">
          No numeric KPI data available for bar chart. Try KPI Cards view.
        </div>
      );
    }
    return (
      <div data-testid="bar-chart-view" className="w-full h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={barChartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="value" name="KPI Value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  // Phase 6A: Render pie chart
  const renderPieChart = () => {
    if (pieChartData.length === 0) {
      return (
        <div className="p-8 text-center text-gray-500 bg-gray-50 rounded-xl">
          No numeric KPI data available for pie chart. Try KPI Cards view.
        </div>
      );
    }
    return (
      <div data-testid="pie-chart-view" className="w-full h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={pieChartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }: { name?: string; percent?: number }) => `${name ?? ''}: ${((percent ?? 0) * 100).toFixed(0)}%`}
              outerRadius={100}
              dataKey="value"
            >
              {pieChartData.map((_entry, index) => (
                <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  };

  // Phase 6A: Render the selected visualization
  const renderVisualization = () => {
    switch (chartType) {
      case 'bar': return renderBarChart();
      case 'pie': return renderPieChart();
      case 'cards':
      default: return renderKPICards();
    }
  };

  return (
    <div className="space-y-6">
      {/* Phase 6A: Chart Type Selector + KPI Category Filters */}
      <div className="flex items-center justify-between flex-wrap gap-2">
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
        {renderChartTypeSelector()}
      </div>

      {/* Phase 6A: Adaptive Visualization */}
      {renderVisualization()}

      {/* Executive Summary */}
      <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl p-6 border border-slate-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <span>Executive Summary</span>
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

      {/* Actionable Insights (server-fetched) */}
      {insights.length > 0 && (
        <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-6 border border-amber-200">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-4">
            <span>Actionable Insights</span>
          </h3>
          <div className="space-y-3">
            {insights.slice(0, 4).map((insight, idx) => (
              <div
                key={insight.id || idx}
                className={`p-3 rounded-lg border ${
                  insight.priority === 'high'
                    ? 'bg-red-50 border-red-200'
                    : insight.priority === 'medium'
                    ? 'bg-yellow-50 border-yellow-200'
                    : 'bg-gray-50 border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold uppercase px-2 py-0.5 rounded ${
                      insight.type === 'warning'
                        ? 'bg-red-100 text-red-700'
                        : insight.type === 'recommendation'
                        ? 'bg-blue-100 text-blue-700'
                        : insight.type === 'validation'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-700'
                    }`}>
                      {insight.type}
                    </span>
                    <span className="font-medium text-gray-900">{insight.title}</span>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    insight.priority === 'high'
                      ? 'bg-red-100 text-red-700'
                      : insight.priority === 'medium'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {insight.priority}
                  </span>
                </div>
                <p className="text-sm text-gray-600 mt-2">{insight.description}</p>
                {insight.action && (
                  <p className="text-sm text-primary mt-2 font-medium">-&gt; {insight.action}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Phase 6B: Enhanced Action Items - Prioritized Checklist */}
      {actionItems.length > 0 && (
        <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl p-6 border border-indigo-200" data-testid="action-items-panel">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Action Items
          </h3>
          <div className="space-y-2">
            {actionItems.map(item => (
              <div
                key={item.id}
                className={`flex items-start gap-3 p-3 rounded-lg border transition-all ${
                  actionChecks[item.id] ? 'bg-gray-50 border-gray-200 opacity-60' : 'bg-white border-gray-200 hover:border-indigo-300'
                }`}
                data-testid={`action-item-${item.id}`}
              >
                <input
                  type="checkbox"
                  checked={!!actionChecks[item.id]}
                  onChange={() => toggleActionCheck(item.id)}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                  aria-label={item.label}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${effortBadgeStyles[item.effort]}`}>
                      {effortLabels[item.effort]}
                    </span>
                    <span className={`text-sm ${actionChecks[item.id] ? 'line-through text-gray-400' : 'text-gray-800'}`}>
                      {item.label}
                    </span>
                  </div>
                </div>
                {item.drillDownPanel && (
                  <button
                    onClick={() => onDrillDown?.(item.drillDownPanel!)}
                    className="text-xs text-primary hover:text-primary/80 whitespace-nowrap underline"
                    title={`Navigate to ${item.drillDownPanel}`}
                  >
                    View panel
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Phase 6B: Roadmap - Numbered Step Sequence */}
      {roadmapSteps.length > 0 && (
        <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl p-6 border border-emerald-200" data-testid="roadmap-panel">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Analysis Roadmap
          </h3>
          <div className="relative">
            {roadmapSteps.map((step, idx) => (
              <div key={step.number} className="flex items-start gap-4 mb-4 last:mb-0" data-testid={`roadmap-step-${step.number}`}>
                {/* Step number circle with connecting line */}
                <div className="flex flex-col items-center">
                  <div className="flex-shrink-0 w-8 h-8 bg-emerald-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                    {step.number}
                  </div>
                  {idx < roadmapSteps.length - 1 && (
                    <div className="w-0.5 h-8 bg-emerald-200 mt-1" />
                  )}
                </div>
                <div className="flex-1 pt-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-gray-900 text-sm">{step.title}</h4>
                    {step.panelLink && (
                      <button
                        onClick={() => onDrillDown?.(step.panelLink!)}
                        className="text-xs text-emerald-600 hover:text-emerald-800 underline"
                      >
                        Open
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-600 mt-0.5">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Decision Actions */}
      {queryResponse && (
        <div className="flex items-center gap-3 pt-4 border-t flex-wrap">
          <button className="flex-1 min-w-[120px] px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-colors">
            Export Report
          </button>
          <button className="flex-1 min-w-[120px] px-4 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors">
            Share Analysis
          </button>
          <button className="px-4 py-2 text-gray-500 hover:text-gray-700 transition-colors">
            <span className="text-xl">Settings</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default ExecutiveKPIPanel;
