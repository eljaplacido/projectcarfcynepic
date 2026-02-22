import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PolicyFederationTab from '../components/carf/PolicyFederationTab';

// Mock the API service
vi.mock('../services/apiService', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>();
    return {
        ...actual,
        getGovernanceDomains: vi.fn(),
        getFederatedPolicies: vi.fn(),
        getConflicts: vi.fn(),
        resolveConflict: vi.fn(),
    };
});

import {
    getGovernanceDomains,
    getFederatedPolicies,
    getConflicts,
    resolveConflict,
} from '../services/apiService';

const mockDomains = [
    {
        domain_id: 'procurement',
        display_name: 'Procurement',
        description: 'Procurement domain',
        owner_email: 'proc@example.com',
        policy_namespace: 'procurement',
        tags: ['spend'],
        color: '#3B82F6',
    },
    {
        domain_id: 'sustainability',
        display_name: 'Sustainability',
        description: 'Sustainability domain',
        owner_email: 'green@example.com',
        policy_namespace: 'sustainability',
        tags: ['esg'],
        color: '#10B981',
    },
];

const mockPolicies = [
    {
        policy_id: 'p1',
        name: 'Spend Cap Policy',
        domain_id: 'procurement',
        namespace: 'procurement.spend_cap',
        description: 'Limits max spend',
        rules: [{ rule_id: 'r1', name: 'max_spend', condition: {}, constraint: {}, message: '', severity: 'medium' }],
        priority: 80,
        is_active: true,
        version: '1.0',
        tags: [],
    },
    {
        policy_id: 'p2',
        name: 'Carbon Budget Policy',
        domain_id: 'sustainability',
        namespace: 'sustainability.carbon_budget',
        description: 'Carbon budget limit',
        rules: [{ rule_id: 'r2', name: 'carbon_limit', condition: {}, constraint: {}, message: '', severity: 'high' }],
        priority: 90,
        is_active: true,
        version: '1.0',
        tags: [],
    },
    {
        policy_id: 'p3',
        name: 'Vendor Audit Policy',
        domain_id: 'procurement',
        namespace: 'procurement.vendor_audit',
        description: 'Annual vendor audit',
        rules: [],
        priority: 50,
        is_active: false,
        version: '1.0',
        tags: [],
    },
];

const mockConflicts = [
    {
        conflict_id: 'c1',
        policy_a_id: 'p1',
        policy_a_name: 'Spend Cap Policy',
        policy_a_domain: 'procurement',
        policy_b_id: 'p2',
        policy_b_name: 'Carbon Budget Policy',
        policy_b_domain: 'sustainability',
        conflict_type: 'resource_contention',
        severity: 'high',
        description: 'Spend cap conflicts with carbon budget allocation',
        resolution: null,
        resolved_at: null,
    },
];

describe('PolicyFederationTab', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('shows loading state initially', () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
        (getFederatedPolicies as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
        (getConflicts as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

        render(<PolicyFederationTab />);

        expect(screen.getByText('Loading policy federation...')).toBeTruthy();
    });

    it('renders empty state when no domains loaded', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue([]);
        (getFederatedPolicies as ReturnType<typeof vi.fn>).mockResolvedValue([]);
        (getConflicts as ReturnType<typeof vi.fn>).mockResolvedValue([]);

        render(<PolicyFederationTab />);

        await waitFor(() => {
            expect(screen.getByText('RESOLVE')).toBeTruthy();
            expect(screen.getByText(/No federated policies loaded/)).toBeTruthy();
        });
    });

    it('renders domain sidebar with domain names', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue(mockDomains);
        (getFederatedPolicies as ReturnType<typeof vi.fn>).mockResolvedValue(mockPolicies);
        (getConflicts as ReturnType<typeof vi.fn>).mockResolvedValue([]);

        render(<PolicyFederationTab />);

        await waitFor(() => {
            expect(screen.getByText('Procurement')).toBeTruthy();
            expect(screen.getByText('Sustainability')).toBeTruthy();
        });
    });

    it('renders policy cards with policy names', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue(mockDomains);
        (getFederatedPolicies as ReturnType<typeof vi.fn>).mockResolvedValue(mockPolicies);
        (getConflicts as ReturnType<typeof vi.fn>).mockResolvedValue([]);

        render(<PolicyFederationTab />);

        await waitFor(() => {
            expect(screen.getByText('Spend Cap Policy')).toBeTruthy();
            expect(screen.getByText('Carbon Budget Policy')).toBeTruthy();
            expect(screen.getByText('Vendor Audit Policy')).toBeTruthy();
        });
    });

    it('renders conflict panel when conflicts exist', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue(mockDomains);
        (getFederatedPolicies as ReturnType<typeof vi.fn>).mockResolvedValue(mockPolicies);
        (getConflicts as ReturnType<typeof vi.fn>).mockResolvedValue(mockConflicts);

        render(<PolicyFederationTab />);

        await waitFor(() => {
            expect(screen.getByText(/Unresolved Conflicts/)).toBeTruthy();
            expect(screen.getByText(/Spend cap conflicts with carbon budget allocation/)).toBeTruthy();
        });
    });

    it('filters policies when a domain is clicked', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue(mockDomains);
        (getFederatedPolicies as ReturnType<typeof vi.fn>).mockResolvedValue(mockPolicies);
        (getConflicts as ReturnType<typeof vi.fn>).mockResolvedValue([]);

        render(<PolicyFederationTab />);

        // Wait for data to load
        await waitFor(() => {
            expect(screen.getByText('Spend Cap Policy')).toBeTruthy();
        });

        // Click on Sustainability domain
        fireEvent.click(screen.getByText('Sustainability'));

        // Should only show sustainability policies
        await waitFor(() => {
            expect(screen.getByText('Carbon Budget Policy')).toBeTruthy();
            // Procurement policies should be filtered out
            expect(screen.queryByText('Spend Cap Policy')).toBeNull();
            expect(screen.queryByText('Vendor Audit Policy')).toBeNull();
        });
    });

    it('shows all policies when All Domains is clicked after filtering', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue(mockDomains);
        (getFederatedPolicies as ReturnType<typeof vi.fn>).mockResolvedValue(mockPolicies);
        (getConflicts as ReturnType<typeof vi.fn>).mockResolvedValue([]);

        render(<PolicyFederationTab />);

        await waitFor(() => {
            expect(screen.getByText('Spend Cap Policy')).toBeTruthy();
        });

        // Filter by Sustainability
        fireEvent.click(screen.getByText('Sustainability'));
        await waitFor(() => {
            expect(screen.queryByText('Spend Cap Policy')).toBeNull();
        });

        // Click All Domains to reset
        fireEvent.click(screen.getByText('All Domains'));
        await waitFor(() => {
            expect(screen.getByText('Spend Cap Policy')).toBeTruthy();
            expect(screen.getByText('Carbon Budget Policy')).toBeTruthy();
            expect(screen.getByText('Vendor Audit Policy')).toBeTruthy();
        });
    });

    it('renders a Resolve button on each conflict', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue(mockDomains);
        (getFederatedPolicies as ReturnType<typeof vi.fn>).mockResolvedValue(mockPolicies);
        (getConflicts as ReturnType<typeof vi.fn>).mockResolvedValue(mockConflicts);

        render(<PolicyFederationTab />);

        await waitFor(() => {
            const resolveButtons = screen.getAllByText('Resolve');
            expect(resolveButtons.length).toBe(1);
        });
    });
});
