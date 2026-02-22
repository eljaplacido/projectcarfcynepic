import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import GovernanceBoardTab from '../components/carf/GovernanceBoardTab';
import type {
    GovernanceBoard,
    BoardTemplate,
    GovernanceDomain,
    FederatedPolicyInfo,
    ComplianceScore,
} from '../types/carf';

// Mock apiService
vi.mock('../services/apiService', () => ({
    getGovernanceBoards: vi.fn(),
    getBoardTemplates: vi.fn(),
    getGovernanceDomains: vi.fn(),
    getFederatedPolicies: vi.fn(),
    getBoardCompliance: vi.fn(),
    createGovernanceBoard: vi.fn(),
    createBoardFromTemplate: vi.fn(),
    deleteGovernanceBoard: vi.fn(),
    exportGovernanceSpec: vi.fn(),
    seedGovernanceDemoData: vi.fn(),
}));

import {
    getGovernanceBoards,
    getBoardTemplates,
    getGovernanceDomains,
    getFederatedPolicies,
    getBoardCompliance,
    createGovernanceBoard,
    createBoardFromTemplate,
    deleteGovernanceBoard,
    exportGovernanceSpec,
    seedGovernanceDemoData,
} from '../services/apiService';

const mockedGetGovernanceBoards = vi.mocked(getGovernanceBoards);
const mockedGetBoardTemplates = vi.mocked(getBoardTemplates);
const mockedGetGovernanceDomains = vi.mocked(getGovernanceDomains);
const mockedGetFederatedPolicies = vi.mocked(getFederatedPolicies);
const mockedGetBoardCompliance = vi.mocked(getBoardCompliance);

const mockTemplate: BoardTemplate = {
    template_id: 'scope_emissions',
    name: 'Scope Emissions Template',
    description: 'Pre-configured board for GHG emission governance',
    domain_ids: ['sustainability'],
    frameworks: ['eu_ai_act'],
    tags: ['emissions', 'ghg'],
};

const mockDomain: GovernanceDomain = {
    domain_id: 'sustainability',
    display_name: 'Sustainability',
    description: 'Environmental sustainability governance',
    owner_email: 'admin@example.com',
    policy_namespace: 'sustainability',
    tags: ['esg'],
    color: '#10B981',
};

const mockPolicy: FederatedPolicyInfo = {
    policy_id: 'pol-1',
    name: 'Carbon Budget Policy',
    domain_id: 'sustainability',
    namespace: 'sustainability.carbon_budget',
    description: 'Caps carbon spending per action',
    rules: [
        {
            rule_id: 'r-1',
            name: 'Max CO2 per action',
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

const mockBoard: GovernanceBoard = {
    board_id: 'board-1',
    name: 'ESG Oversight Board',
    description: 'Board for environmental oversight',
    template_id: 'scope_emissions',
    domain_ids: ['sustainability'],
    policy_namespaces: ['sustainability.carbon_budget'],
    compliance_configs: [
        {
            framework: 'eu_ai_act',
            enabled: true,
            target_score: 0.85,
            custom_articles: [],
            custom_weights: {},
        },
    ],
    members: [
        {
            user_id: 'u-1',
            name: 'Alice Manager',
            email: 'alice@example.com',
            role: 'owner',
        },
    ],
    tags: ['esg', 'environment'],
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
};

const mockCompliance: ComplianceScore = {
    framework: 'eu_ai_act',
    overall_score: 0.82,
    articles: [
        {
            article_id: 'art-9',
            title: 'Risk Management',
            score: 0.9,
            status: 'compliant',
            evidence: ['Policy exists'],
            gaps: [],
        },
    ],
    gaps: [],
    recommendations: [],
};

describe('GovernanceBoardTab', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders loading state initially', () => {
        // Make the API calls hang (never resolve) so loading state persists
        mockedGetGovernanceBoards.mockReturnValue(new Promise(() => {}));
        mockedGetBoardTemplates.mockReturnValue(new Promise(() => {}));
        mockedGetGovernanceDomains.mockReturnValue(new Promise(() => {}));
        mockedGetFederatedPolicies.mockReturnValue(new Promise(() => {}));

        render(<GovernanceBoardTab />);

        expect(screen.getByText('Loading governance boards...')).toBeInTheDocument();
    });

    it('renders empty state when no boards', async () => {
        mockedGetGovernanceBoards.mockResolvedValue([]);
        mockedGetBoardTemplates.mockResolvedValue([]);
        mockedGetGovernanceDomains.mockResolvedValue([]);
        mockedGetFederatedPolicies.mockResolvedValue([]);

        render(<GovernanceBoardTab />);

        await waitFor(() => {
            expect(screen.getByText(/No boards yet/)).toBeInTheDocument();
        });
    });

    it('renders board list', async () => {
        mockedGetGovernanceBoards.mockResolvedValue([mockBoard]);
        mockedGetBoardTemplates.mockResolvedValue([mockTemplate]);
        mockedGetGovernanceDomains.mockResolvedValue([mockDomain]);
        mockedGetFederatedPolicies.mockResolvedValue([mockPolicy]);

        render(<GovernanceBoardTab />);

        await waitFor(() => {
            expect(screen.getByText('ESG Oversight Board')).toBeInTheDocument();
        });

        // Verify board count badge
        expect(screen.getByText('1 board')).toBeInTheDocument();
    });

    it('shows template dropdown', async () => {
        mockedGetGovernanceBoards.mockResolvedValue([]);
        mockedGetBoardTemplates.mockResolvedValue([mockTemplate]);
        mockedGetGovernanceDomains.mockResolvedValue([]);
        mockedGetFederatedPolicies.mockResolvedValue([]);

        render(<GovernanceBoardTab />);

        await waitFor(() => {
            expect(screen.getByText('From Template')).toBeInTheDocument();
        });

        // Click the "From Template" button
        fireEvent.click(screen.getByText('From Template'));

        // Verify template names appear in the dropdown
        await waitFor(() => {
            expect(screen.getByText('Scope Emissions Template')).toBeInTheDocument();
        });
        expect(screen.getByText('Pre-configured board for GHG emission governance')).toBeInTheDocument();
    });

    it('renders board detail when selected', async () => {
        mockedGetGovernanceBoards.mockResolvedValue([mockBoard]);
        mockedGetBoardTemplates.mockResolvedValue([mockTemplate]);
        mockedGetGovernanceDomains.mockResolvedValue([mockDomain]);
        mockedGetFederatedPolicies.mockResolvedValue([mockPolicy]);
        mockedGetBoardCompliance.mockResolvedValue([mockCompliance]);

        render(<GovernanceBoardTab />);

        // Wait for boards to load, then click on the board
        await waitFor(() => {
            expect(screen.getByText('ESG Oversight Board')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('ESG Oversight Board'));

        // Verify domain section appears
        await waitFor(() => {
            expect(screen.getByText(/Domains/)).toBeInTheDocument();
        });
        expect(screen.getByText('Sustainability')).toBeInTheDocument();

        // Verify policies section appears
        expect(screen.getByText(/Policies/)).toBeInTheDocument();
        expect(screen.getByText('Carbon Budget Policy')).toBeInTheDocument();

        // Verify members section appears
        expect(screen.getByText('Alice Manager')).toBeInTheDocument();
        expect(screen.getByText('owner')).toBeInTheDocument();

        // Verify tags appear
        expect(screen.getByText('esg')).toBeInTheDocument();
        expect(screen.getByText('environment')).toBeInTheDocument();
    });
});
