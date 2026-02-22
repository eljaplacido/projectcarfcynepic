import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PolicyEditorModal from '../components/carf/PolicyEditorModal';
import type { FederatedPolicyInfo, GovernanceDomain } from '../types/carf';

// Mock apiService
vi.mock('../services/apiService', () => ({
    createFederatedPolicy: vi.fn(),
    updateFederatedPolicy: vi.fn(),
    getGovernanceDomains: vi.fn(),
}));

import {
    createFederatedPolicy,
    updateFederatedPolicy,
    getGovernanceDomains,
} from '../services/apiService';

const mockedGetGovernanceDomains = vi.mocked(getGovernanceDomains);
const mockedCreateFederatedPolicy = vi.mocked(createFederatedPolicy);

const mockDomains: GovernanceDomain[] = [
    {
        domain_id: 'sustainability',
        display_name: 'Sustainability',
        description: 'Environmental sustainability governance',
        owner_email: 'admin@example.com',
        policy_namespace: 'sustainability',
        tags: ['esg'],
        color: '#10B981',
    },
    {
        domain_id: 'security',
        display_name: 'Security',
        description: 'Cybersecurity governance',
        owner_email: 'sec@example.com',
        policy_namespace: 'security',
        tags: ['infosec'],
        color: '#EF4444',
    },
];

const mockEditPolicy: FederatedPolicyInfo = {
    policy_id: 'pol-1',
    name: 'Carbon Budget Policy',
    domain_id: 'sustainability',
    namespace: 'sustainability.carbon_budget',
    description: 'Caps carbon spending per action',
    rules: [
        {
            rule_id: 'r-1',
            name: 'Max CO2',
            condition: { emission_type: 'scope_1' },
            constraint: { max_co2_tons: 100 },
            message: 'CO2 exceeds limit',
            severity: 'high',
        },
    ],
    priority: 80,
    is_active: true,
    version: 'v1.0',
    tags: ['carbon'],
};

const defaultProps = {
    isOpen: false,
    onClose: vi.fn(),
    onSaved: vi.fn(),
};

describe('PolicyEditorModal', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockedGetGovernanceDomains.mockResolvedValue(mockDomains);
    });

    it('renders nothing when closed', () => {
        const { container } = render(
            <PolicyEditorModal {...defaultProps} isOpen={false} />
        );

        // Modal should not render any visible content
        expect(container.innerHTML).toBe('');
    });

    it('renders create form when open', async () => {
        render(
            <PolicyEditorModal {...defaultProps} isOpen={true} />
        );

        // Verify "Create Policy" heading is shown
        expect(screen.getByText('Create Policy')).toBeInTheDocument();

        // Verify form fields are present
        expect(screen.getByText('Name')).toBeInTheDocument();
        expect(screen.getByText('Domain')).toBeInTheDocument();
        expect(screen.getByText('Namespace')).toBeInTheDocument();
        expect(screen.getByText('Description')).toBeInTheDocument();

        // Verify action buttons
        expect(screen.getByText('Cancel')).toBeInTheDocument();
        expect(screen.getByText('Save')).toBeInTheDocument();
    });

    it('renders edit form with policy data', async () => {
        render(
            <PolicyEditorModal
                {...defaultProps}
                isOpen={true}
                editPolicy={mockEditPolicy}
            />
        );

        // Verify "Edit Policy" heading is shown
        expect(screen.getByText('Edit Policy')).toBeInTheDocument();

        // Verify the name input is pre-filled with the policy name
        const nameInput = screen.getByDisplayValue('Carbon Budget Policy');
        expect(nameInput).toBeInTheDocument();

        // Verify the namespace is pre-filled
        expect(screen.getByDisplayValue('sustainability.carbon_budget')).toBeInTheDocument();
    });

    it('calls onClose when Cancel clicked', async () => {
        const onClose = vi.fn();

        render(
            <PolicyEditorModal
                {...defaultProps}
                isOpen={true}
                onClose={onClose}
            />
        );

        fireEvent.click(screen.getByText('Cancel'));
        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('shows error when save with empty fields', async () => {
        render(
            <PolicyEditorModal {...defaultProps} isOpen={true} />
        );

        // Click Save without filling any fields
        fireEvent.click(screen.getByText('Save'));

        // Verify error message about required fields
        await waitFor(() => {
            expect(screen.getByText('Name, domain, and namespace are required.')).toBeInTheDocument();
        });

        // Verify createFederatedPolicy was NOT called
        expect(mockedCreateFederatedPolicy).not.toHaveBeenCalled();
    });
});
