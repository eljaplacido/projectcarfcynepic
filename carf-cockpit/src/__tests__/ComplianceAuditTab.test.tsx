import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ComplianceAuditTab from '../components/carf/ComplianceAuditTab';

// Mock the API service
vi.mock('../services/apiService', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>();
    return {
        ...actual,
        getComplianceScore: vi.fn(),
        getGovernanceAudit: vi.fn(),
    };
});

import { getComplianceScore, getGovernanceAudit } from '../services/apiService';

const mockComplianceData = {
    framework: 'eu_ai_act',
    overall_score: 0.83,
    articles: [
        {
            article_id: 'Art.9',
            title: 'Risk Management System',
            score: 0.85,
            status: 'compliant',
            evidence: ['Guardian layer enforces risk-based policy checks'],
            gaps: [],
        },
        {
            article_id: 'Art.10',
            title: 'Data and Data Governance',
            score: 0.75,
            status: 'partial',
            evidence: ['Dataset provenance tracked via Neo4j'],
            gaps: ['No automated data bias detection'],
        },
        {
            article_id: 'Art.13',
            title: 'Transparency and Information',
            score: 0.88,
            status: 'compliant',
            evidence: ['TransparencyPanel shows full decision rationale'],
            gaps: ['No standardized model card generation'],
        },
    ],
    gaps: ['No automated data bias detection', 'No standardized model card generation'],
    recommendations: [
        'Implement automated data bias detection for Art.10',
        'Add standardized model card generation for Art.13',
    ],
};

const mockAuditEntries = [
    {
        entry_id: 'ae1',
        event_type: 'triple_created',
        actor: 'governance_node',
        affected_domains: ['procurement', 'sustainability'],
        details: { triples_created: 3 },
        timestamp: '2026-02-20T10:00:00Z',
    },
    {
        entry_id: 'ae2',
        event_type: 'cost_computed',
        actor: 'governance_node',
        affected_domains: [],
        details: { total_cost: 0.0045 },
        timestamp: '2026-02-20T10:01:00Z',
    },
];

describe('ComplianceAuditTab', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders framework selector buttons for all 4 frameworks', async () => {
        (getComplianceScore as ReturnType<typeof vi.fn>).mockResolvedValue(mockComplianceData);
        (getGovernanceAudit as ReturnType<typeof vi.fn>).mockResolvedValue(mockAuditEntries);

        render(<ComplianceAuditTab />);

        // Framework buttons are always rendered, even during loading
        expect(screen.getByText('EU AI Act')).toBeTruthy();
        expect(screen.getByText('CSRD')).toBeTruthy();
        expect(screen.getByText('GDPR')).toBeTruthy();
        expect(screen.getByText('ISO 27001')).toBeTruthy();
    });

    it('defaults to EU AI Act framework', async () => {
        (getComplianceScore as ReturnType<typeof vi.fn>).mockResolvedValue(mockComplianceData);
        (getGovernanceAudit as ReturnType<typeof vi.fn>).mockResolvedValue(mockAuditEntries);

        render(<ComplianceAuditTab />);

        await waitFor(() => {
            // The EU AI Act button should have active styling (600 fontWeight)
            const euButton = screen.getByText('EU AI Act');
            expect(euButton).toBeTruthy();
            // getComplianceScore should be called with 'eu_ai_act' by default
            expect(getComplianceScore).toHaveBeenCalledWith('eu_ai_act');
        });
    });

    it('shows loading state while fetching data', () => {
        (getComplianceScore as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
        (getGovernanceAudit as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

        render(<ComplianceAuditTab />);

        expect(screen.getByText('Loading compliance assessment...')).toBeTruthy();
    });

    it('renders score gauge when data loads', async () => {
        (getComplianceScore as ReturnType<typeof vi.fn>).mockResolvedValue(mockComplianceData);
        (getGovernanceAudit as ReturnType<typeof vi.fn>).mockResolvedValue(mockAuditEntries);

        render(<ComplianceAuditTab />);

        await waitFor(() => {
            // 83% from overall_score 0.83
            expect(screen.getByText('83%')).toBeTruthy();
            expect(screen.getByText('Compliant')).toBeTruthy();
        });
    });

    it('renders article accordion with article titles', async () => {
        (getComplianceScore as ReturnType<typeof vi.fn>).mockResolvedValue(mockComplianceData);
        (getGovernanceAudit as ReturnType<typeof vi.fn>).mockResolvedValue(mockAuditEntries);

        render(<ComplianceAuditTab />);

        await waitFor(() => {
            expect(screen.getByText(/Articles/)).toBeTruthy();
            expect(screen.getByText(/Risk Management System/)).toBeTruthy();
            expect(screen.getByText(/Data and Data Governance/)).toBeTruthy();
            expect(screen.getByText(/Transparency and Information/)).toBeTruthy();
        });
    });

    it('loads new data when a different framework button is clicked', async () => {
        const csrdData = {
            ...mockComplianceData,
            framework: 'csrd',
            overall_score: 0.66,
            articles: [],
            gaps: [],
            recommendations: [],
        };

        (getComplianceScore as ReturnType<typeof vi.fn>)
            .mockResolvedValueOnce(mockComplianceData)  // initial EU AI Act load
            .mockResolvedValueOnce(csrdData);            // CSRD load
        (getGovernanceAudit as ReturnType<typeof vi.fn>).mockResolvedValue(mockAuditEntries);

        render(<ComplianceAuditTab />);

        // Wait for initial load
        await waitFor(() => {
            expect(screen.getByText('83%')).toBeTruthy();
        });

        // Click CSRD
        fireEvent.click(screen.getByText('CSRD'));

        await waitFor(() => {
            expect(getComplianceScore).toHaveBeenCalledWith('csrd');
            // 66% from CSRD overall_score 0.66
            expect(screen.getByText('66%')).toBeTruthy();
        });
    });
});
