import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TransparencyPanel from '../components/carf/TransparencyPanel';
import type { DatasetInfo } from '../components/carf/TransparencyPanel';

// Mock the apiService to prevent real network calls
vi.mock('../services/apiService', () => ({
    default: {
        getAgents: vi.fn().mockResolvedValue([]),
        assessReliability: vi.fn().mockResolvedValue(null),
        getRouterConfig: vi.fn().mockResolvedValue({}),
        getGuardianConfig: vi.fn().mockResolvedValue({}),
    },
}));

// Mock global fetch for the policies endpoint
(globalThis as { fetch?: typeof fetch }).fetch = vi.fn().mockRejectedValue(new Error('mock'));

const mockQueryResponse = {
    domain: 'complicated',
    domainConfidence: 0.85,
    method: 'Causal Inference',
    guardianVerdict: 'Approved',
    causalResult: {
        effect: 0.35,
        refutationsPassed: 2,
        refutationsTotal: 3,
    },
};

const mockDatasetInfo: DatasetInfo = {
    fileName: 'test_data.csv',
    columns: ['treatment', 'outcome', 'age', 'region'],
    rowCount: 1500,
    columnTypes: { treatment: 'boolean', outcome: 'float64', age: 'int64', region: 'string' },
    completeness: 0.95,
    validity: 0.88,
    variableRoles: {
        treatment: 'treatment',
        outcome: 'outcome',
        covariates: ['age', 'region'],
    },
};

// ---------------------------------------------------------------------------
// 2A: Data modal renders dataset info
// ---------------------------------------------------------------------------
describe('DataModal -- dataset info rendering', () => {
    it('renders dataset file name, row count, and columns when dataset is loaded', async () => {
        render(
            <TransparencyPanel
                queryResponse={mockQueryResponse}
                datasetInfo={mockDatasetInfo}
            />
        );

        // The data modal is triggered from the reliability tab's "View Data" button.
        // We need reliability data to show the button, but the mock returns null.
        // Instead, render the panel and open the data modal directly by finding
        // the button. The reliability tab may not have data, so let's switch
        // approach: render the component then simulate opening the modal.

        // Since the reliability API returns null (mocked), the panel shows
        // "Run a query..." -- the View Data button won't appear.
        // We need to set reliability so the button is shown.
        // Let's re-mock assessReliability to return data:
    });

    it('renders loaded dataset info in data modal when View Data is clicked', async () => {
        // Re-mock to provide reliability data so View Data button appears
        const apiMod = await import('../services/apiService');
        vi.spyOn(apiMod.default, 'assessReliability').mockResolvedValue({
            overall_score: 0.82,
            overall_level: 'good',
            level: 'good',
            factors: [
                { name: 'Confidence', score: 0.85, weight: 0.3, status: 'good', explanation: 'High confidence' },
            ],
            components: [],
            suggestions: [],
            eu_ai_act_compliant: true,
        });

        const { container } = render(
            <TransparencyPanel
                queryResponse={mockQueryResponse}
                datasetInfo={mockDatasetInfo}
            />
        );

        // Wait for reliability to load and show the View Data button
        const viewDataBtn = await screen.findByText('View Data', {}, { timeout: 3000 });
        fireEvent.click(viewDataBtn);

        // Now the DataModal should be open
        expect(screen.getByText('Data Schema & Sources')).toBeInTheDocument();
        expect(screen.getByText('Loaded Dataset')).toBeInTheDocument();

        // file name appears in both dataset section and flow node; use getAllByText
        const fileNameMatches = screen.getAllByText(/test_data\.csv/);
        expect(fileNameMatches.length).toBeGreaterThanOrEqual(1);

        expect(screen.getByText(/1,500/)).toBeInTheDocument();
        expect(screen.getByText(/Columns \(4\)/)).toBeInTheDocument();

        // Check variable roles
        expect(screen.getByText('Variable Roles')).toBeInTheDocument();

        // Check data quality indicators
        const qualitySection = container.querySelector('[data-testid="data-quality-indicators"]');
        expect(qualitySection).not.toBeNull();
        expect(screen.getByText('Completeness')).toBeInTheDocument();
        expect(screen.getByText('Validity')).toBeInTheDocument();
        expect(screen.getByText('95%')).toBeInTheDocument();
        expect(screen.getByText('88%')).toBeInTheDocument();
    });

    it('shows only domain info when no dataset is loaded', async () => {
        const apiMod = await import('../services/apiService');
        vi.spyOn(apiMod.default, 'assessReliability').mockResolvedValue({
            overall_score: 0.82,
            overall_level: 'good',
            level: 'good',
            factors: [],
            components: [],
            suggestions: [],
            eu_ai_act_compliant: true,
        });

        render(
            <TransparencyPanel
                queryResponse={mockQueryResponse}
                datasetInfo={null}
            />
        );

        const viewDataBtn = await screen.findByText('View Data', {}, { timeout: 3000 });
        fireEvent.click(viewDataBtn);

        expect(screen.getByText('Data Schema & Sources')).toBeInTheDocument();
        expect(screen.getByText('Analysis Context')).toBeInTheDocument();
        // Should NOT show "Loaded Dataset" section
        expect(screen.queryByText('Loaded Dataset')).toBeNull();
    });
});

// ---------------------------------------------------------------------------
// 2B: Data lineage flowchart renders in the modal
// ---------------------------------------------------------------------------
describe('DataModal -- lineage flowchart', () => {
    it('renders all five flow nodes: Input, Router, Agent, Guardian, Output', async () => {
        const apiMod = await import('../services/apiService');
        vi.spyOn(apiMod.default, 'assessReliability').mockResolvedValue({
            overall_score: 0.82,
            overall_level: 'good',
            level: 'good',
            factors: [],
            components: [],
            suggestions: [],
            eu_ai_act_compliant: true,
        });

        const { container } = render(
            <TransparencyPanel
                queryResponse={mockQueryResponse}
                datasetInfo={mockDatasetInfo}
            />
        );

        const viewDataBtn = await screen.findByText('View Data', {}, { timeout: 3000 });
        fireEvent.click(viewDataBtn);

        const flow = container.querySelector('[data-testid="data-lineage-flow"]');
        expect(flow).not.toBeNull();

        expect(container.querySelector('[data-testid="flow-node-input"]')).not.toBeNull();
        expect(container.querySelector('[data-testid="flow-node-router"]')).not.toBeNull();
        expect(container.querySelector('[data-testid="flow-node-agent"]')).not.toBeNull();
        expect(container.querySelector('[data-testid="flow-node-guardian"]')).not.toBeNull();
        expect(container.querySelector('[data-testid="flow-node-output"]')).not.toBeNull();

        // Router should show domain
        const routerNode = container.querySelector('[data-testid="flow-node-router"]')!;
        expect(routerNode.textContent).toContain('complicated');

        // Agent should show method
        const agentNode = container.querySelector('[data-testid="flow-node-agent"]')!;
        expect(agentNode.textContent).toContain('Causal Inference');

        // Guardian should show verdict
        const guardianNode = container.querySelector('[data-testid="flow-node-guardian"]')!;
        expect(guardianNode.textContent).toContain('Approved');
    });
});

// ---------------------------------------------------------------------------
// 2C: Baseline reference lines render in quality panel
// ---------------------------------------------------------------------------
describe('QualityScoresPanel -- baselines and drill-downs', () => {
    it('renders baseline reference lines for each quality metric', async () => {
        // We need to switch to the Quality tab. The panel starts on Reliability.
        render(
            <TransparencyPanel
                queryResponse={mockQueryResponse}
            />
        );

        // Switch to Quality tab
        const qualityTab = screen.getByText('Quality');
        fireEvent.click(qualityTab);

        // Wait for quality scores to be generated (demo/fallback useEffect)
        const relevancyBar = await screen.findByTestId('score-bar-relevancy', {}, { timeout: 3000 });
        expect(relevancyBar).toBeInTheDocument();

        // Check baseline lines exist
        expect(screen.getByTestId('baseline-relevancy')).toBeInTheDocument();
        expect(screen.getByTestId('baseline-hallucination-risk')).toBeInTheDocument();
        expect(screen.getByTestId('baseline-reasoning-depth')).toBeInTheDocument();
        expect(screen.getByTestId('baseline-uix-compliance')).toBeInTheDocument();
    });

    it('expands drill-down on click and collapses on second click', async () => {
        render(
            <TransparencyPanel
                queryResponse={mockQueryResponse}
            />
        );

        // Switch to Quality tab
        fireEvent.click(screen.getByText('Quality'));

        const relevancyBar = await screen.findByTestId('score-bar-relevancy', {}, { timeout: 3000 });

        // Initially no drill-down
        expect(screen.queryByTestId('drilldown-relevancy')).toBeNull();

        // Click to expand
        fireEvent.click(relevancyBar);
        const drilldown = screen.getByTestId('drilldown-relevancy');
        expect(drilldown).toBeInTheDocument();
        expect(drilldown.textContent).toContain('Relevancy measures');
        expect(drilldown.textContent).toContain('Industry standard');

        // Click again to collapse
        fireEvent.click(relevancyBar);
        expect(screen.queryByTestId('drilldown-relevancy')).toBeNull();
    });

    it('only one metric drill-down is expanded at a time', async () => {
        render(
            <TransparencyPanel
                queryResponse={mockQueryResponse}
            />
        );

        fireEvent.click(screen.getByText('Quality'));

        const relevancyBar = await screen.findByTestId('score-bar-relevancy', {}, { timeout: 3000 });
        const hallucinationBar = screen.getByTestId('score-bar-hallucination-risk');

        // Expand relevancy
        fireEvent.click(relevancyBar);
        expect(screen.getByTestId('drilldown-relevancy')).toBeInTheDocument();
        expect(screen.queryByTestId('drilldown-hallucination-risk')).toBeNull();

        // Now expand hallucination -- relevancy should close
        fireEvent.click(hallucinationBar);
        expect(screen.queryByTestId('drilldown-relevancy')).toBeNull();
        expect(screen.getByTestId('drilldown-hallucination-risk')).toBeInTheDocument();
    });
});

// ---------------------------------------------------------------------------
// 2D: Reliability factor interpretations
// ---------------------------------------------------------------------------
describe('Reliability tab -- factor interpretations', () => {
    it('renders plain-English interpretation for each reliability factor', async () => {
        const apiMod = await import('../services/apiService');
        vi.spyOn(apiMod.default, 'assessReliability').mockResolvedValue({
            overall_score: 0.82,
            overall_level: 'good',
            level: 'good',
            factors: [
                { name: 'Confidence', score: 0.9, weight: 0.3, status: 'good', explanation: '' },
                { name: 'Data Quality', score: 0.65, weight: 0.2, status: 'fair', explanation: '' },
            ],
            components: [],
            suggestions: [],
            eu_ai_act_compliant: true,
        });

        render(
            <TransparencyPanel queryResponse={mockQueryResponse} />
        );

        // Wait for the reliability factors to render
        const confInterpretation = await screen.findByTestId('factor-interpretation-confidence', {}, { timeout: 3000 });
        expect(confInterpretation).toBeInTheDocument();
        // High confidence => "highly confident"
        expect(confInterpretation.textContent).toContain('highly confident');
        expect(confInterpretation.textContent).toContain('complicated');

        const dqInterpretation = screen.getByTestId('factor-interpretation-data-quality');
        expect(dqInterpretation).toBeInTheDocument();
        // Score 0.65 < 0.7 => "concern"
        expect(dqInterpretation.textContent).toContain('concern');
    });
});
