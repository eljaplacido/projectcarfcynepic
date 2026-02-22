import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExecutiveKPIPanel } from '../components/carf/ExecutiveKPIPanel';
import type { QueryResponse, CausalAnalysisResult, BayesianBeliefState, GuardianDecision } from '../types/carf';

// ---- Mock data ----

const mockQueryResponse: QueryResponse = {
  sessionId: 'sess-abc123def456',
  domain: 'complicated',
  domainConfidence: 0.85,
  domainEntropy: 0.15,
  guardianVerdict: 'approved',
  response: 'Test analysis complete.',
  requiresHuman: false,
  reasoningChain: [],
  causalResult: null,
  bayesianResult: null,
  guardianResult: null,
  error: null,
  keyInsights: ['Insight A', 'Insight B'],
  nextSteps: ['Step 1', 'Step 2'],
};

const mockCausalResult: CausalAnalysisResult = {
  effect: 0.42,
  unit: 'units',
  pValue: 0.01,
  confidenceInterval: [0.3, 0.54],
  description: 'Treatment increases outcome',
  refutationsPassed: 3,
  refutationsTotal: 4,
  refutationDetails: [
    { name: 'Placebo', passed: true, pValue: 0.3 },
    { name: 'Random Common Cause', passed: true, pValue: 0.4 },
    { name: 'Data Subset', passed: true, pValue: 0.2 },
    { name: 'Bootstrap', passed: false, pValue: 0.02 },
  ],
  confoundersControlled: [{ name: 'age', controlled: true }],
  evidenceBase: 'observational',
  metaAnalysis: false,
  studies: 1,
  treatment: 'new_policy',
  outcome: 'productivity',
};

const mockBayesianResult: BayesianBeliefState = {
  variable: 'productivity',
  priorMean: 0.5,
  priorStd: 0.1,
  posteriorMean: 0.65,
  posteriorStd: 0.08,
  confidenceLevel: 'high',
  interpretation: 'Strong evidence of improvement',
  epistemicUncertainty: 0.35,
  aleatoricUncertainty: 0.15,
  totalUncertainty: 0.5,
};

const mockGuardianResult: GuardianDecision = {
  overallStatus: 'pass',
  proposedAction: {
    type: 'invest',
    target: 'Renewable Energy',
    amount: 25000,
    unit: 'USD',
    expectedEffect: 'Reduce CO2 by 15%',
  },
  policies: [
    {
      id: 'budget_limit',
      name: 'Budget Limit',
      description: 'Max per-action spend',
      status: 'passed',
      version: 'v1.0',
    },
    {
      id: 'bias_check',
      name: 'Bias Check',
      description: 'Ensure no bias',
      status: 'failed',
      version: 'v1.0',
    },
  ],
  requiresHumanApproval: true,
  riskLevel: 'medium',
  policiesPassed: 1,
  policiesTotal: 2,
};

// ---- Setup ----

beforeEach(() => {
  // Mock fetch to return empty / basic responses for config endpoints
  (globalThis.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
    if (typeof url === 'string' && url.includes('/config/visualization')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ kpi_templates: [] }),
      });
    }
    if (typeof url === 'string' && url.includes('/guardian/status')) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            compliance_percentage: 80,
            policies_active: 3,
            risk_level: 'medium',
          }),
      });
    }
    if (typeof url === 'string' && url.includes('/insights/generate')) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            insights: [
              {
                id: 'ins-1',
                type: 'recommendation',
                title: 'Collect more data',
                description: 'Additional data would improve confidence.',
                priority: 'high',
                action: 'Run follow-up study',
              },
            ],
          }),
      });
    }
    return Promise.resolve({ ok: false, json: () => Promise.resolve({}) });
  });
});

// ---- Tests ----

describe('ExecutiveKPIPanel', () => {
  // ========================
  // Phase 6A: Chart type switching
  // ========================

  describe('Chart type switching (Phase 6A)', () => {
    it('renders chart type selector with three options', () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={null}
          bayesianResult={null}
          guardianResult={null}
        />
      );

      expect(screen.getByTestId('chart-type-selector')).toBeInTheDocument();
      expect(screen.getByTestId('chart-type-cards')).toBeInTheDocument();
      expect(screen.getByTestId('chart-type-bar')).toBeInTheDocument();
      expect(screen.getByTestId('chart-type-pie')).toBeInTheDocument();
    });

    it('defaults to KPI Cards view', () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={null}
          bayesianResult={null}
          guardianResult={null}
        />
      );

      expect(screen.getByTestId('kpi-cards-view')).toBeInTheDocument();
    });

    it('switches to bar chart view when bar icon is clicked', async () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={mockCausalResult}
          bayesianResult={mockBayesianResult}
          guardianResult={null}
        />
      );

      // Click bar chart button
      fireEvent.click(screen.getByTestId('chart-type-bar'));

      await waitFor(() => {
        expect(screen.getByTestId('bar-chart-view')).toBeInTheDocument();
      });

      // KPI cards view should no longer be rendered
      expect(screen.queryByTestId('kpi-cards-view')).not.toBeInTheDocument();
    });

    it('switches to pie chart view when pie icon is clicked', async () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={mockCausalResult}
          bayesianResult={mockBayesianResult}
          guardianResult={null}
        />
      );

      fireEvent.click(screen.getByTestId('chart-type-pie'));

      await waitFor(() => {
        expect(screen.getByTestId('pie-chart-view')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('kpi-cards-view')).not.toBeInTheDocument();
    });

    it('can switch back to cards after selecting another chart type', async () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={mockCausalResult}
          bayesianResult={null}
          guardianResult={null}
        />
      );

      // Switch to bar
      fireEvent.click(screen.getByTestId('chart-type-bar'));
      await waitFor(() => {
        expect(screen.getByTestId('bar-chart-view')).toBeInTheDocument();
      });

      // Switch back to cards
      fireEvent.click(screen.getByTestId('chart-type-cards'));
      await waitFor(() => {
        expect(screen.getByTestId('kpi-cards-view')).toBeInTheDocument();
      });
    });
  });

  // ========================
  // Phase 6B: Enhanced insights and action items
  // ========================

  describe('Enhanced insights render (Phase 6B)', () => {
    it('renders server-fetched actionable insights', async () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={mockCausalResult}
          bayesianResult={mockBayesianResult}
          guardianResult={mockGuardianResult}
        />
      );

      // Wait for insights to load from the mock fetch
      await waitFor(() => {
        expect(screen.getByText('Collect more data')).toBeInTheDocument();
      });

      expect(screen.getByText('Additional data would improve confidence.')).toBeInTheDocument();
      expect(screen.getByText(/Run follow-up study/)).toBeInTheDocument();
    });

    it('renders executive summary text based on queryResponse', () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={null}
          bayesianResult={null}
          guardianResult={null}
        />
      );

      // The summary contains the domain and confidence text; may appear in multiple elements
      expect(screen.getAllByText(/COMPLICATED/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/85% confidence/).length).toBeGreaterThan(0);
    });
  });

  describe('Action items display (Phase 6B)', () => {
    it('renders action items panel with prioritized checklist when data warrants actions', async () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={mockCausalResult}
          bayesianResult={mockBayesianResult}
          guardianResult={mockGuardianResult}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('action-items-panel')).toBeInTheDocument();
      });

      // Should have Quick Win badge(s) for failed policies
      expect(screen.getAllByText('Quick Win').length).toBeGreaterThan(0);
      // Should have Medium Effort badge(s) for human approval / refutation gaps
      expect(screen.getAllByText('Medium Effort').length).toBeGreaterThan(0);
      // Should have Strategic badge(s) for strong causal effect
      expect(screen.getAllByText('Strategic').length).toBeGreaterThan(0);
    });

    it('allows toggling action item checkboxes', async () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={mockCausalResult}
          bayesianResult={mockBayesianResult}
          guardianResult={mockGuardianResult}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('action-items-panel')).toBeInTheDocument();
      });

      // Find checkboxes
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBeGreaterThan(0);

      // Initially unchecked
      expect(checkboxes[0]).not.toBeChecked();

      // Click to check
      fireEvent.click(checkboxes[0]);
      expect(checkboxes[0]).toBeChecked();

      // Click to uncheck
      fireEvent.click(checkboxes[0]);
      expect(checkboxes[0]).not.toBeChecked();
    });

    it('renders "View panel" drill-down links for action items', async () => {
      const onDrillDown = vi.fn();
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={mockCausalResult}
          bayesianResult={mockBayesianResult}
          guardianResult={mockGuardianResult}
          onDrillDown={onDrillDown}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('action-items-panel')).toBeInTheDocument();
      });

      const viewPanelButtons = screen.getAllByText('View panel');
      expect(viewPanelButtons.length).toBeGreaterThan(0);

      fireEvent.click(viewPanelButtons[0]);
      expect(onDrillDown).toHaveBeenCalled();
    });

    it('renders roadmap with numbered steps when queryResponse is provided', async () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={mockCausalResult}
          bayesianResult={mockBayesianResult}
          guardianResult={mockGuardianResult}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('roadmap-panel')).toBeInTheDocument();
      });

      expect(screen.getByText('Analysis Roadmap')).toBeInTheDocument();
      expect(screen.getByTestId('roadmap-step-1')).toBeInTheDocument();
      expect(screen.getByText('Review Domain Classification')).toBeInTheDocument();
      expect(screen.getByText('Validate Causal Findings')).toBeInTheDocument();
    });

    it('does not render action items panel when no actions are warranted', () => {
      // With no causal/bayesian/guardian data, only low-confidence action would fire
      const highConfResponse = { ...mockQueryResponse, domainConfidence: 0.95 };
      render(
        <ExecutiveKPIPanel
          queryResponse={highConfResponse}
          causalResult={null}
          bayesianResult={null}
          guardianResult={null}
        />
      );

      expect(screen.queryByTestId('action-items-panel')).not.toBeInTheDocument();
    });
  });

  // ========================
  // Baseline functionality preserved
  // ========================

  describe('KPI cards and summary', () => {
    it('renders empty state when no queryResponse is provided', () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={null}
          causalResult={null}
          bayesianResult={null}
          guardianResult={null}
        />
      );

      expect(screen.getByText(/Submit a query to receive an executive summary/)).toBeInTheDocument();
    });

    it('renders KPI cards with correct data from queryResponse', async () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={null}
          bayesianResult={null}
          guardianResult={null}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Domain Confidence')).toBeInTheDocument();
      });

      expect(screen.getByText('Overall Score')).toBeInTheDocument();
      expect(screen.getByText('Risk Assessment')).toBeInTheDocument();
      expect(screen.getByText('Policy Compliance')).toBeInTheDocument();
    });

    it('renders category filter buttons', () => {
      render(
        <ExecutiveKPIPanel
          queryResponse={mockQueryResponse}
          causalResult={mockCausalResult}
          bayesianResult={null}
          guardianResult={null}
        />
      );

      expect(screen.getByText('All KPIs')).toBeInTheDocument();
      // 'confidence' appears in both the filter button and KPI card category labels
      expect(screen.getAllByText('confidence').length).toBeGreaterThan(0);
    });
  });
});
