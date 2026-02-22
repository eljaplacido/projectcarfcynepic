import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import CostIntelligenceTab from '../components/carf/CostIntelligenceTab';

// Mock the API service
vi.mock('../services/apiService', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>();
    return {
        ...actual,
        getCostAggregate: vi.fn(),
        getCostROI: vi.fn(),
    };
});

import { getCostAggregate, getCostROI } from '../services/apiService';

const mockCostAggregate = {
    total_cost: 1.2345,
    average_cost_per_query: 0.0123,
    total_tokens: 54321,
    cost_by_category: {
        llm: 0.8,
        compute: 0.25,
        risk: 0.15,
        opportunity: 0.0345,
    },
};

const mockROI = {
    roi_percentage: 342,
    cost_per_insight: 0.012,
    manual_equivalent_cost: 5.45,
};

describe('CostIntelligenceTab', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('shows loading state initially', () => {
        // Mock APIs that never resolve to keep loading state
        (getCostAggregate as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
        (getCostROI as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

        render(<CostIntelligenceTab />);

        expect(screen.getByText('Loading cost intelligence...')).toBeTruthy();
    });

    it('renders KPI cards when data loads', async () => {
        (getCostAggregate as ReturnType<typeof vi.fn>).mockResolvedValue(mockCostAggregate);
        (getCostROI as ReturnType<typeof vi.fn>).mockResolvedValue(mockROI);

        render(<CostIntelligenceTab />);

        await waitFor(() => {
            expect(screen.getByText('Total Cost')).toBeTruthy();
            expect(screen.getByText('ROI')).toBeTruthy();
            expect(screen.getByText('Tokens Used')).toBeTruthy();
        });
    });

    it('renders empty state when no data returned', async () => {
        (getCostAggregate as ReturnType<typeof vi.fn>).mockResolvedValue({});
        (getCostROI as ReturnType<typeof vi.fn>).mockResolvedValue({});

        render(<CostIntelligenceTab />);

        await waitFor(() => {
            // With empty data, cost values show $0.0000 and chart shows empty message
            const zeroCosts = screen.getAllByText('$0.0000');
            expect(zeroCosts.length).toBeGreaterThanOrEqual(1);
            expect(screen.getByText('No cost data yet. Run a query with governance enabled.')).toBeTruthy();
        });
    });

    it('displays total cost correctly formatted', async () => {
        (getCostAggregate as ReturnType<typeof vi.fn>).mockResolvedValue(mockCostAggregate);
        (getCostROI as ReturnType<typeof vi.fn>).mockResolvedValue(mockROI);

        render(<CostIntelligenceTab />);

        await waitFor(() => {
            expect(screen.getByText('$1.2345')).toBeTruthy();
        });
    });

    it('displays ROI percentage correctly', async () => {
        (getCostAggregate as ReturnType<typeof vi.fn>).mockResolvedValue(mockCostAggregate);
        (getCostROI as ReturnType<typeof vi.fn>).mockResolvedValue(mockROI);

        render(<CostIntelligenceTab />);

        await waitFor(() => {
            expect(screen.getByText('342%')).toBeTruthy();
        });
    });

    it('renders chart containers with category headers', async () => {
        (getCostAggregate as ReturnType<typeof vi.fn>).mockResolvedValue(mockCostAggregate);
        (getCostROI as ReturnType<typeof vi.fn>).mockResolvedValue(mockROI);

        render(<CostIntelligenceTab />);

        await waitFor(() => {
            expect(screen.getByText('Cost Breakdown by Category')).toBeTruthy();
            expect(screen.getByText('Cost Distribution')).toBeTruthy();
        });
    });
});
