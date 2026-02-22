import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import GuardianPanel from '../components/carf/GuardianPanel';
import type { GuardianDecision } from '../types/carf';

// Mock ExplainableWrapper to just render children
vi.mock('../components/carf/ExplainableWrapper', () => ({
    default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock PolicyEditorModal to avoid heavy dependencies
vi.mock('../components/carf/PolicyEditorModal', () => ({
    default: ({ isOpen }: { isOpen: boolean }) =>
        isOpen ? <div data-testid="policy-editor-modal">Policy Editor</div> : null,
}));

const mockDecision: GuardianDecision = {
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
            details: 'Under $50k limit',
        },
        {
            id: 'confidence_gate',
            name: 'Confidence Gate',
            description: 'Min confidence threshold',
            status: 'passed',
            version: 'v1.0',
            details: 'Confidence 0.85 > 0.70',
        },
    ],
    requiresHumanApproval: false,
};

describe('GuardianPanel', () => {
    beforeEach(() => {
        // Mock fetch to return config and policy descriptions
        (globalThis.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
            if (url.includes('/guardian/config')) {
                return Promise.resolve({
                    ok: true,
                    json: () =>
                        Promise.resolve({
                            activePolicies: 4,
                            thresholds: [
                                { name: 'Max spend per action', value: '$50,000' },
                                { name: 'Min confidence', value: '0.70' },
                            ],
                        }),
                });
            }
            if (url.includes('/guardian/policies')) {
                return Promise.resolve({
                    ok: true,
                    json: () =>
                        Promise.resolve([
                            {
                                id: 'budget_limit',
                                name: 'Budget Limit',
                                description: 'Caps maximum spend per automated action.',
                                relevance: 'Prevents large financial commitments without human sign-off.',
                                configControl: 'Threshold: max_spend_per_action',
                                euAiActArticle: 'Art. 14 - Human oversight',
                                euAiActMatchLevel: 'partial',
                            },
                        ]),
                });
            }
            return Promise.resolve({ ok: false, json: () => Promise.resolve({}) });
        });
    });

    // 3A: Empty state renders config info
    it('renders empty state with config information when no decision provided', async () => {
        render(<GuardianPanel decision={null} />);

        // Explanatory text
        expect(screen.getByText(/Safety & Compliance Layer/)).toBeInTheDocument();
        expect(screen.getByText(/validates every proposed action/)).toBeInTheDocument();

        // Wait for config fetch
        await waitFor(() => {
            expect(screen.getByTestId('guardian-config-summary')).toBeInTheDocument();
        });

        expect(screen.getByText('4 policies active')).toBeInTheDocument();
        expect(screen.getByText('Max spend per action')).toBeInTheDocument();
        expect(screen.getByText('$50,000')).toBeInTheDocument();
    });

    // 3B: Policy descriptions render in empty state
    it('renders policy descriptions with EU AI Act indicators in empty state', async () => {
        render(<GuardianPanel decision={null} />);

        await waitFor(() => {
            expect(screen.getByTestId('guardian-policy-descriptions')).toBeInTheDocument();
        });

        expect(screen.getByText('Budget Limit')).toBeInTheDocument();
        expect(screen.getByText('Caps maximum spend per automated action.')).toBeInTheDocument();
        expect(screen.getByText(/Art\. 14/)).toBeInTheDocument();
        expect(screen.getByText('Partial match')).toBeInTheDocument();
    });

    // 3B: Policy descriptions render per-policy in decision view
    it('renders per-policy descriptions and EU AI Act badges when decision is present', async () => {
        render(<GuardianPanel decision={mockDecision} />);

        // Wait for policy descriptions to load
        await waitFor(() => {
            expect(screen.getByText(/Prevents large financial commitments/)).toBeInTheDocument();
        });

        expect(screen.getByText(/Threshold: max_spend_per_action/)).toBeInTheDocument();
    });

    // 3C: Audit trail button is present and clickable
    it('renders clickable audit trail button that calls onViewAuditTrail', async () => {
        const onViewAuditTrail = vi.fn();
        render(<GuardianPanel decision={mockDecision} onViewAuditTrail={onViewAuditTrail} />);

        const auditButton = screen.getByTestId('audit-trail-button');
        expect(auditButton).toBeInTheDocument();
        expect(screen.getByText('Audit trail preserved')).toBeInTheDocument();

        fireEvent.click(auditButton);
        expect(onViewAuditTrail).toHaveBeenCalledTimes(1);
    });

    // 3A: Empty What/Why/Risk sections when decision exists but fields are empty
    it('explains why What/Why/Risk sections are empty when decision has no action data', async () => {
        const emptyDecision: GuardianDecision = {
            overallStatus: 'pending',
            proposedAction: {
                type: '',
                target: '',
                amount: 0,
                unit: '',
                expectedEffect: '',
            },
            policies: [],
            requiresHumanApproval: false,
        };

        render(<GuardianPanel decision={emptyDecision} />);

        expect(screen.getByTestId('what-empty')).toBeInTheDocument();
        expect(screen.getByText(/No proposed action specified/)).toBeInTheDocument();

        expect(screen.getByTestId('why-empty')).toBeInTheDocument();
        expect(screen.getByText(/Expected effect not yet computed/)).toBeInTheDocument();

        expect(screen.getByTestId('risk-empty')).toBeInTheDocument();
        expect(screen.getByText(/No policy checks have been evaluated/)).toBeInTheDocument();
    });

    it('renders verdict badge correctly for each status', () => {
        const { rerender } = render(<GuardianPanel decision={mockDecision} />);
        expect(screen.getByText('APPROVED')).toBeInTheDocument();

        rerender(
            <GuardianPanel decision={{ ...mockDecision, overallStatus: 'fail' }} />
        );
        expect(screen.getByText('REJECTED')).toBeInTheDocument();

        rerender(
            <GuardianPanel decision={{ ...mockDecision, overallStatus: 'pending' }} />
        );
        expect(screen.getByText('REQUIRES APPROVAL')).toBeInTheDocument();
    });
});
