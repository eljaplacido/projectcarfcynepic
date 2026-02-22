import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import InterventionSimulator from '../components/carf/InterventionSimulator';

describe('InterventionSimulator', () => {
    const defaultProps = {
        treatment: 'Training Hours',
        outcome: 'CO2 Reduction',
        baseTreatmentValue: 10.0,
        baseOutcomeValue: 50.0,
        effectSize: 0.5,
        unit: 'tons',
    };

    const confounders = [
        { name: 'Budget', baseValue: 0, effectOnOutcome: 0.3, unit: 'k$' },
        { name: 'Team Size', baseValue: 0, effectOnOutcome: 0.15, unit: 'people' },
    ];

    it('renders the primary treatment slider', () => {
        render(<InterventionSimulator {...defaultProps} />);
        const slider = screen.getByTestId('treatment-slider');
        expect(slider).toBeTruthy();
        expect(screen.getByText(/Adjust Training Hours/)).toBeTruthy();
    });

    it('renders confounder sliders when confounders are provided', () => {
        render(<InterventionSimulator {...defaultProps} confounders={confounders} />);
        expect(screen.getByTestId('confounder-Budget')).toBeTruthy();
        expect(screen.getByTestId('confounder-Team Size')).toBeTruthy();
    });

    it('renders combined predicted outcome', () => {
        render(<InterventionSimulator {...defaultProps} />);
        const outcomeEl = screen.getByTestId('predicted-outcome');
        expect(outcomeEl).toBeTruthy();
        // Default predicted outcome equals baseOutcomeValue when slider is at baseline
        expect(outcomeEl.textContent).toContain('50.0');
        expect(outcomeEl.textContent).toContain('tons');
    });

    it('updates prediction when treatment slider changes', async () => {
        render(<InterventionSimulator {...defaultProps} />);
        const slider = screen.getByTestId('treatment-slider') as HTMLInputElement;

        // Move slider to max (15.0 = 10.0 * 1.5)
        fireEvent.change(slider, { target: { value: '15' } });

        await waitFor(() => {
            const outcomeEl = screen.getByTestId('predicted-outcome');
            // Effect: (15 - 10) * 0.5 = 2.5, so predicted = 50 + 2.5 = 52.5
            expect(outcomeEl.textContent).toContain('52.5');
        });
    });

    it('shows the Add Parameter button', () => {
        render(<InterventionSimulator {...defaultProps} />);
        expect(screen.getByTestId('add-parameter-btn')).toBeTruthy();
    });

    it('opens add parameter form when button is clicked', () => {
        render(<InterventionSimulator {...defaultProps} />);
        fireEvent.click(screen.getByTestId('add-parameter-btn'));
        expect(screen.getByTestId('add-parameter-form')).toBeTruthy();
        expect(screen.getByTestId('new-param-name')).toBeTruthy();
    });

    it('adds a new parameter and renders its slider', async () => {
        render(<InterventionSimulator {...defaultProps} />);
        fireEvent.click(screen.getByTestId('add-parameter-btn'));

        const nameInput = screen.getByTestId('new-param-name') as HTMLInputElement;
        fireEvent.change(nameInput, { target: { value: 'Fuel Cost' } });

        fireEvent.click(screen.getByTestId('confirm-add-param'));

        await waitFor(() => {
            expect(screen.getByTestId('confounder-Fuel Cost')).toBeTruthy();
        });
    });

    it('removes a parameter when remove button is clicked', async () => {
        render(<InterventionSimulator {...defaultProps} confounders={confounders} />);
        expect(screen.getByTestId('confounder-Budget')).toBeTruthy();

        fireEvent.click(screen.getByTestId('remove-Budget'));

        await waitFor(() => {
            expect(screen.queryByTestId('confounder-Budget')).toBeNull();
        });
    });

    it('highlights the strongest effect parameter', () => {
        render(<InterventionSimulator {...defaultProps} confounders={confounders} />);
        const hint = screen.getByTestId('strongest-effect-hint');
        expect(hint).toBeTruthy();
        // Budget has the largest effect (0.3 > 0.15)
        expect(hint.textContent).toContain('Budget');
        expect(hint.textContent).toContain('largest effect');
    });

    it('calls onRunSimulation with combined params', () => {
        const onRun = vi.fn();
        render(<InterventionSimulator {...defaultProps} confounders={confounders} onRunSimulation={onRun} />);

        fireEvent.click(screen.getByTestId('run-simulation-btn'));
        expect(onRun).toHaveBeenCalledTimes(1);

        const params = onRun.mock.calls[0][0];
        expect(params).toHaveProperty('treatmentValue');
        expect(params).toHaveProperty('confounderAdjustments');
        expect(params).toHaveProperty('predictedOutcome');
        expect(params).toHaveProperty('percentChange');
    });

    it('saves a scenario when Save Scenario is clicked', async () => {
        render(<InterventionSimulator {...defaultProps} />);
        fireEvent.click(screen.getByTestId('save-scenario-btn'));

        await waitFor(() => {
            expect(screen.getByText('Scenario 1')).toBeTruthy();
        });
    });

    it('resets all sliders to baseline on reset', async () => {
        render(<InterventionSimulator {...defaultProps} confounders={confounders} />);
        const slider = screen.getByTestId('treatment-slider') as HTMLInputElement;

        // Move slider away from baseline
        fireEvent.change(slider, { target: { value: '15' } });

        // Click reset
        fireEvent.click(screen.getByText('Reset'));

        await waitFor(() => {
            const outcomeEl = screen.getByTestId('predicted-outcome');
            expect(outcomeEl.textContent).toContain('50.0');
        });
    });
});
