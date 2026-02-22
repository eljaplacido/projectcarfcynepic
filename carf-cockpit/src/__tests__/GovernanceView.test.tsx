import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import GovernanceView from '../components/carf/GovernanceView';
import type { QueryResponse } from '../types/carf';

// Mock child tab components so we can test GovernanceView in isolation
vi.mock('../components/carf/SpecMapTab', () => ({
    __esModule: true,
    default: (props: { lastResult: unknown }) => (
        <div data-testid="mock-specmap-tab" data-last-result={JSON.stringify(props.lastResult)}>
            SpecMapTab Content
        </div>
    ),
}));

vi.mock('../components/carf/CostIntelligenceTab', () => ({
    __esModule: true,
    default: (props: { sessionId?: string }) => (
        <div data-testid="mock-cost-tab" data-session-id={props.sessionId || ''}>
            CostIntelligenceTab Content
        </div>
    ),
}));

vi.mock('../components/carf/PolicyFederationTab', () => ({
    __esModule: true,
    default: () => (
        <div data-testid="mock-policy-tab">PolicyFederationTab Content</div>
    ),
}));

vi.mock('../components/carf/ComplianceAuditTab', () => ({
    __esModule: true,
    default: () => (
        <div data-testid="mock-compliance-tab">ComplianceAuditTab Content</div>
    ),
}));

const createMockResponse = (overrides: Partial<QueryResponse> = {}): QueryResponse => ({
    sessionId: 'gov-session-001',
    domain: 'complicated',
    domainConfidence: 0.85,
    domainEntropy: 0.15,
    guardianVerdict: 'approved',
    response: 'Governance test response',
    requiresHuman: false,
    reasoningChain: [],
    causalResult: null,
    bayesianResult: null,
    guardianResult: null,
    error: null,
    ...overrides,
});

describe('GovernanceView', () => {
    it('renders all 4 tab buttons', () => {
        render(<GovernanceView lastResult={null} />);

        expect(screen.getByText('Spec Map')).toBeTruthy();
        expect(screen.getByText('Cost Intelligence')).toBeTruthy();
        expect(screen.getByText('Policy Federation')).toBeTruthy();
        expect(screen.getByText('Compliance Audit')).toBeTruthy();
    });

    it('shows Spec Map tab as default active content', () => {
        render(<GovernanceView lastResult={null} />);

        expect(screen.getByTestId('mock-specmap-tab')).toBeTruthy();
        expect(screen.queryByTestId('mock-cost-tab')).toBeNull();
        expect(screen.queryByTestId('mock-policy-tab')).toBeNull();
        expect(screen.queryByTestId('mock-compliance-tab')).toBeNull();
    });

    it('switches to Cost Intelligence tab when clicked', () => {
        render(<GovernanceView lastResult={null} />);

        fireEvent.click(screen.getByText('Cost Intelligence'));

        expect(screen.queryByTestId('mock-specmap-tab')).toBeNull();
        expect(screen.getByTestId('mock-cost-tab')).toBeTruthy();
        expect(screen.queryByTestId('mock-policy-tab')).toBeNull();
        expect(screen.queryByTestId('mock-compliance-tab')).toBeNull();
    });

    it('switches to Policy Federation tab when clicked', () => {
        render(<GovernanceView lastResult={null} />);

        fireEvent.click(screen.getByText('Policy Federation'));

        expect(screen.queryByTestId('mock-specmap-tab')).toBeNull();
        expect(screen.queryByTestId('mock-cost-tab')).toBeNull();
        expect(screen.getByTestId('mock-policy-tab')).toBeTruthy();
        expect(screen.queryByTestId('mock-compliance-tab')).toBeNull();
    });

    it('switches to Compliance Audit tab when clicked', () => {
        render(<GovernanceView lastResult={null} />);

        fireEvent.click(screen.getByText('Compliance Audit'));

        expect(screen.queryByTestId('mock-specmap-tab')).toBeNull();
        expect(screen.queryByTestId('mock-cost-tab')).toBeNull();
        expect(screen.queryByTestId('mock-policy-tab')).toBeNull();
        expect(screen.getByTestId('mock-compliance-tab')).toBeTruthy();
    });

    it('passes lastResult prop to SpecMapTab correctly', () => {
        const mockResult = createMockResponse();
        render(<GovernanceView lastResult={mockResult} />);

        const specMapTab = screen.getByTestId('mock-specmap-tab');
        const passedData = specMapTab.getAttribute('data-last-result');
        expect(passedData).toBeTruthy();
        const parsed = JSON.parse(passedData!);
        expect(parsed.sessionId).toBe('gov-session-001');
    });

    it('passes sessionId prop to CostIntelligenceTab correctly', () => {
        const mockResult = createMockResponse();
        render(<GovernanceView lastResult={mockResult} sessionId="custom-session-42" />);

        fireEvent.click(screen.getByText('Cost Intelligence'));

        const costTab = screen.getByTestId('mock-cost-tab');
        expect(costTab.getAttribute('data-session-id')).toBe('custom-session-42');
    });

    it('renders without crashing when lastResult is null', () => {
        const { container } = render(<GovernanceView lastResult={null} />);

        expect(container.querySelector('.governance-view')).toBeTruthy();
        expect(screen.getByTestId('mock-specmap-tab')).toBeTruthy();
    });
});
