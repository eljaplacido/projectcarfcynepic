import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SensitivityPlot from '../components/carf/SensitivityPlot';

// Mock recharts to avoid canvas/SVG rendering issues in jsdom
vi.mock('recharts', async (importOriginal) => {
    const actual = await importOriginal<typeof import('recharts')>();
    return {
        ...actual,
        ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
            <div data-testid="responsive-container" style={{ width: 500, height: 300 }}>
                {children}
            </div>
        ),
    };
});

describe('SensitivityPlot', () => {
    const defaultProps = {
        gamma: 2.0,
        treatment: 'Training Program',
        outcome: 'Emissions Reduction',
        refutationsPassed: 3,
        refutationsTotal: 4,
    };

    it('renders plain English axis labels', () => {
        const { container } = render(<SensitivityPlot {...defaultProps} />);
        // Check that the chart uses plain English labels
        expect(container.textContent).toContain('Sensitivity Analysis');
        // Interpretation text should use plain language
        expect(container.textContent).toContain('hidden factors');
        expect(container.textContent).toContain('2.0x');
    });

    it('renders interpretation text with robustness assessment', () => {
        render(<SensitivityPlot {...defaultProps} />);
        // gamma = 2.0 is "moderately robust" (> 1.5 but <= 2)
        expect(screen.getByText(/moderately robust/)).toBeTruthy();
        expect(screen.getByText(/hidden factors were up to/)).toBeTruthy();
    });

    it('renders "very robust" for gamma > 2', () => {
        render(<SensitivityPlot {...defaultProps} gamma={2.5} />);
        expect(screen.getByText(/very robust/)).toBeTruthy();
    });

    it('renders "fragile" for gamma <= 1.5', () => {
        render(<SensitivityPlot {...defaultProps} gamma={1.3} />);
        expect(screen.getByText(/fragile/)).toBeTruthy();
    });

    it('renders refutation summary when tests partially pass', () => {
        render(<SensitivityPlot {...defaultProps} refutationsPassed={3} refutationsTotal={4} />);
        expect(screen.getByText(/3\/4/)).toBeTruthy();
        expect(screen.getByText(/some tests flagged sensitivity/)).toBeTruthy();
    });

    it('renders refutation summary when all tests pass', () => {
        render(<SensitivityPlot {...defaultProps} refutationsPassed={4} refutationsTotal={4} />);
        expect(screen.getByText(/4\/4/)).toBeTruthy();
        expect(screen.getByText(/your finding is well-supported/)).toBeTruthy();
    });

    it('renders expand button for fullscreen modal', () => {
        render(<SensitivityPlot {...defaultProps} />);
        const expandBtn = screen.getByTestId('expand-sensitivity-btn');
        expect(expandBtn).toBeTruthy();
    });

    it('opens fullscreen modal when expand button is clicked', () => {
        render(<SensitivityPlot {...defaultProps} />);
        const expandBtn = screen.getByTestId('expand-sensitivity-btn');
        fireEvent.click(expandBtn);
        // Modal should now be visible
        expect(screen.getByTestId('sensitivity-modal')).toBeTruthy();
    });

    it('closes fullscreen modal when backdrop is clicked', () => {
        render(<SensitivityPlot {...defaultProps} />);
        fireEvent.click(screen.getByTestId('expand-sensitivity-btn'));
        expect(screen.getByTestId('sensitivity-modal')).toBeTruthy();

        // Click backdrop to close
        fireEvent.click(screen.getByTestId('sensitivity-modal-backdrop'));
        expect(screen.queryByTestId('sensitivity-modal')).toBeNull();
    });

    it('renders responsive container (recharts chart)', () => {
        render(<SensitivityPlot {...defaultProps} />);
        expect(screen.getAllByTestId('responsive-container').length).toBeGreaterThan(0);
    });

    it('does not render refutation section when no refutation data is provided', () => {
        render(<SensitivityPlot gamma={1.8} />);
        expect(screen.queryByText(/Validation:/)).toBeNull();
    });
});
