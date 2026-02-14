import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DomainVisualization from '../components/carf/DomainVisualization';
import type { CynefinDomain, CausalAnalysisResult, BayesianBeliefState } from '../types/carf';

const mockCausalResult: CausalAnalysisResult = {
    effect: 0.35, unit: 'tCO2e', pValue: 0.03,
    confidenceInterval: [0.1, 0.6], description: 'Test',
    refutationsPassed: 2, refutationsTotal: 3,
    refutationDetails: [], confoundersControlled: [],
    evidenceBase: 'data', metaAnalysis: false, studies: 1,
    treatment: 'Treatment A', outcome: 'Outcome B',
};

const mockBayesianResult: BayesianBeliefState = {
    variable: 'test', priorMean: 0.5, priorStd: 0.1,
    posteriorMean: 0.7, posteriorStd: 0.05,
    confidenceLevel: 'high', interpretation: 'Test interp',
    epistemicUncertainty: 0.3, aleatoricUncertainty: 0.2,
    totalUncertainty: 0.5, recommendedProbe: 'Try X',
};

describe('DomainVisualization', () => {
    it('renders null when domain is null', () => {
        const { container } = render(
            <DomainVisualization domain={null} confidence={0} />
        );
        expect(container.firstChild).toBeNull();
    });

    it('renders null when processing', () => {
        const { container } = render(
            <DomainVisualization domain="clear" confidence={0.9} isProcessing={true} />
        );
        expect(container.firstChild).toBeNull();
    });

    it.each<CynefinDomain>(['clear', 'complicated', 'complex', 'chaotic', 'disorder'])(
        'renders a view for domain: %s',
        (domain) => {
            const { container } = render(
                <DomainVisualization
                    domain={domain}
                    confidence={0.8}
                    causalResult={mockCausalResult}
                    bayesianResult={mockBayesianResult}
                />
            );
            expect(container.firstChild).not.toBeNull();
        }
    );

    it('shows causal effect in complicated view', () => {
        render(
            <DomainVisualization
                domain="complicated" confidence={0.9}
                causalResult={mockCausalResult}
            />
        );
        expect(screen.getByText(/Causal Effect/)).toBeInTheDocument();
        expect(screen.getByText(/0\.350/)).toBeInTheDocument();
    });

    it('shows uncertainty bar in complex view', () => {
        render(
            <DomainVisualization
                domain="complex" confidence={0.7}
                bayesianResult={mockBayesianResult}
            />
        );
        expect(screen.getByText(/Total Uncertainty/)).toBeInTheDocument();
        expect(screen.getByText(/50\.0%/)).toBeInTheDocument();
    });

    it('calls onAction when action button clicked in clear view', () => {
        const onAction = vi.fn();
        render(
            <DomainVisualization domain="clear" confidence={0.95} onAction={onAction} />
        );
        fireEvent.click(screen.getByText(/Apply Recommendation/));
        expect(onAction).toHaveBeenCalledWith('apply');
    });

    it('calls onEscalate in disorder view', () => {
        const onEscalate = vi.fn();
        render(
            <DomainVisualization domain="disorder" confidence={0.3} onEscalate={onEscalate} />
        );
        fireEvent.click(screen.getByText(/Escalate to Human/));
        expect(onEscalate).toHaveBeenCalled();
    });
});
