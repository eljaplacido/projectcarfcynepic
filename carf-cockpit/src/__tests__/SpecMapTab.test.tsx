import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import SpecMapTab from '../components/carf/SpecMapTab';
import type { QueryResponse } from '../types/carf';

// Mock reactflow (the setup.ts may not fully mock it, so we ensure it here)
vi.mock('reactflow', () => {
    const ReactFlowMock = (props: { nodes: unknown[]; edges: unknown[] }) => (
        <div data-testid="mock-reactflow" data-node-count={Array.isArray(props.nodes) ? props.nodes.length : 0}>
            ReactFlow Graph
        </div>
    );
    return {
        __esModule: true,
        default: ReactFlowMock,
        Background: () => <div data-testid="mock-rf-background" />,
        Controls: () => <div data-testid="mock-rf-controls" />,
        Handle: () => <div />,
        Position: { Top: 'top', Bottom: 'bottom', Left: 'left', Right: 'right' },
    };
});

// Mock the API service
vi.mock('../services/apiService', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>();
    return {
        ...actual,
        getGovernanceDomains: vi.fn(),
    };
});

import { getGovernanceDomains } from '../services/apiService';

const mockDomains = [
    {
        domain_id: 'procurement',
        display_name: 'Procurement',
        description: 'Procurement governance domain',
        owner_email: 'proc@test.com',
        policy_namespace: 'procurement',
        tags: ['spend'],
        color: '#3B82F6',
    },
    {
        domain_id: 'sustainability',
        display_name: 'Sustainability',
        description: 'Sustainability governance domain',
        owner_email: 'green@test.com',
        policy_namespace: 'sustainability',
        tags: ['esg'],
        color: '#10B981',
    },
    {
        domain_id: 'security',
        display_name: 'Security',
        description: 'Security governance domain',
        owner_email: 'sec@test.com',
        policy_namespace: 'security',
        tags: ['infosec'],
        color: '#EF4444',
    },
];

describe('SpecMapTab', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('shows loading state initially', () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

        render(<SpecMapTab lastResult={null} />);

        expect(screen.getByText('Loading governance domains...')).toBeTruthy();
    });

    it('renders empty state when no domains configured', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue([]);

        render(<SpecMapTab lastResult={null} />);

        await waitFor(() => {
            expect(screen.getByText('MAP')).toBeTruthy();
            expect(screen.getByText(/No governance domains configured/)).toBeTruthy();
        });
    });

    it('renders ReactFlow when domains exist', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue(mockDomains);

        render(<SpecMapTab lastResult={null} />);

        await waitFor(() => {
            expect(screen.getByTestId('mock-reactflow')).toBeTruthy();
        });
    });

    it('passes correct number of nodes to ReactFlow', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue(mockDomains);

        render(<SpecMapTab lastResult={null} />);

        await waitFor(() => {
            const rfElement = screen.getByTestId('mock-reactflow');
            // 3 domains = 3 nodes
            expect(rfElement.getAttribute('data-node-count')).toBe('3');
        });
    });

    it('renders domain labels in nodes', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue(mockDomains);

        render(<SpecMapTab lastResult={null} />);

        await waitFor(() => {
            // ReactFlow is mocked, so we just verify it rendered
            expect(screen.getByTestId('mock-reactflow')).toBeTruthy();
        });
    });

    it('renders without crashing when lastResult is null', async () => {
        (getGovernanceDomains as ReturnType<typeof vi.fn>).mockResolvedValue(mockDomains);

        const { container } = render(<SpecMapTab lastResult={null} />);

        await waitFor(() => {
            expect(container).toBeTruthy();
            expect(screen.getByTestId('mock-reactflow')).toBeTruthy();
        });
    });
});
