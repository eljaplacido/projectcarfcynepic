import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CausalAnalysisCard from '../components/carf/CausalAnalysisCard';
import type { CausalAnalysisResult } from '../types/carf';

// Mock ExplainableWrapper to just render children
vi.mock('../components/carf/ExplainableWrapper', () => ({
    default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockResult: CausalAnalysisResult = {
    effect: 0.35,
    unit: 'tCO2e',
    pValue: 0.03,
    confidenceInterval: [0.1, 0.6],
    description: 'Carbon reduction effect',
    refutationsPassed: 2,
    refutationsTotal: 3,
    refutationDetails: [
        { name: 'Placebo Treatment', passed: true, pValue: 0.42 },
        { name: 'Random Common Cause', passed: true, pValue: 0.38 },
        { name: 'Data Subset', passed: false, pValue: 0.04 },
    ],
    confoundersControlled: [
        { name: 'Region', controlled: true },
        { name: 'Season', controlled: false },
    ],
    evidenceBase: 'observational',
    metaAnalysis: false,
    studies: 1,
    treatment: 'Carbon Tax',
    outcome: 'CO2 Emissions',
};

describe('CausalAnalysisCard', () => {
    it('renders empty state when no result', () => {
        render(<CausalAnalysisCard result={null} />);
        expect(screen.getByText(/Analysis results will appear here/)).toBeInTheDocument();
    });

    it('renders effect estimate with correct values', () => {
        render(<CausalAnalysisCard result={mockResult} />);
        expect(screen.getByText('+0.35 tCO2e')).toBeInTheDocument();
        expect(screen.getByText('p = 0.0300')).toBeInTheDocument();
        expect(screen.getByText('Carbon reduction effect')).toBeInTheDocument();
    });

    it('does not show follow-up button when onFollowUp is not provided', () => {
        render(<CausalAnalysisCard result={mockResult} />);
        expect(screen.queryByTestId('ask-followup-button')).not.toBeInTheDocument();
    });

    it('shows follow-up button when onFollowUp is provided', () => {
        const onFollowUp = vi.fn();
        render(<CausalAnalysisCard result={mockResult} onFollowUp={onFollowUp} />);
        expect(screen.getByTestId('ask-followup-button')).toBeInTheDocument();
        expect(screen.getByText('Ask follow-up')).toBeInTheDocument();
    });

    it('calls onFollowUp with contextual question when button is clicked', () => {
        const onFollowUp = vi.fn();
        render(<CausalAnalysisCard result={mockResult} onFollowUp={onFollowUp} />);

        fireEvent.click(screen.getByTestId('ask-followup-button'));

        expect(onFollowUp).toHaveBeenCalledTimes(1);
        // The result has p < 0.05 and effect > 0, so it should ask about subgroup heterogeneity
        const question = onFollowUp.mock.calls[0][0] as string;
        expect(question).toContain('Carbon Tax');
        expect(question).toContain('CO2 Emissions');
        expect(question).toContain('subgroups');
    });

    it('generates question about robustness when refutation tests fail', () => {
        const onFollowUp = vi.fn();
        const failedResult: CausalAnalysisResult = {
            ...mockResult,
            pValue: 0.08, // non-significant
            refutationsPassed: 1,
            refutationsTotal: 3,
        };

        render(<CausalAnalysisCard result={failedResult} onFollowUp={onFollowUp} />);
        fireEvent.click(screen.getByTestId('ask-followup-button'));

        const question = onFollowUp.mock.calls[0][0] as string;
        expect(question).toContain('refutation tests failed');
        expect(question).toContain('assumptions');
    });

    it('generates question about confounders when p-value is high', () => {
        const onFollowUp = vi.fn();
        const nonSigResult: CausalAnalysisResult = {
            ...mockResult,
            pValue: 0.12,
            refutationsPassed: 3,
            refutationsTotal: 3,
        };

        render(<CausalAnalysisCard result={nonSigResult} onFollowUp={onFollowUp} />);
        fireEvent.click(screen.getByTestId('ask-followup-button'));

        const question = onFollowUp.mock.calls[0][0] as string;
        expect(question).toContain('not statistically significant');
        expect(question).toContain('confounders');
    });

    it('renders refutation tests correctly', () => {
        render(<CausalAnalysisCard result={mockResult} />);
        expect(screen.getByText('2/3 Passed')).toBeInTheDocument();
        expect(screen.getByText('Placebo Treatment')).toBeInTheDocument();
        expect(screen.getByText('Random Common Cause')).toBeInTheDocument();
        expect(screen.getByText('Data Subset')).toBeInTheDocument();
    });

    it('renders confounders correctly', () => {
        render(<CausalAnalysisCard result={mockResult} />);
        expect(screen.getByText('Region')).toBeInTheDocument();
        expect(screen.getByText('Season')).toBeInTheDocument();
    });
});
