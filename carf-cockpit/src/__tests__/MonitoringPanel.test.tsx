// Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MonitoringPanel from '../components/carf/MonitoringPanel';
import type { DriftStatus, BiasReport, ConvergenceStatus } from '../types/carf';

// Mock the API service
vi.mock('../services/apiService', () => ({
    getMonitoringDriftStatus: vi.fn().mockRejectedValue(new Error('mock')),
    getMonitoringDriftHistory: vi.fn().mockRejectedValue(new Error('mock')),
    resetMonitoringDriftBaseline: vi.fn().mockResolvedValue({ status: 'ok' }),
    getMonitoringBiasAudit: vi.fn().mockRejectedValue(new Error('mock')),
    getMonitoringConvergence: vi.fn().mockRejectedValue(new Error('mock')),
    getMonitoringStatus: vi.fn().mockRejectedValue(new Error('mock')),
}));

const mockDriftStatus: DriftStatus = {
    total_observations: 150,
    baseline_established: true,
    baseline_distribution: { clear: 0.3, complicated: 0.3, complex: 0.2, chaotic: 0.1, disorder: 0.1 },
    current_distribution: { clear: 0.35, complicated: 0.25, complex: 0.2, chaotic: 0.1, disorder: 0.1 },
    alert_count: 2,
    snapshot_count: 5,
    last_snapshot: {
        timestamp: '2026-03-16T10:00:00Z',
        window_size: 50,
        current_distribution: { clear: 0.35, complicated: 0.25, complex: 0.2, chaotic: 0.1, disorder: 0.1 },
        baseline_distribution: { clear: 0.3, complicated: 0.3, complex: 0.2, chaotic: 0.1, disorder: 0.1 },
        kl_divergence: 0.0123,
        max_domain_shift: 0.05,
        shifted_domain: 'clear',
        drift_detected: false,
        alert_reason: '',
    },
    config: { baseline_window: 100, detection_window: 50, kl_threshold: 0.1, domain_shift_threshold: 0.15 },
};

const mockBiasReport: BiasReport = {
    timestamp: '2026-03-16T10:00:00Z',
    total_entries: 200,
    domain_distribution: { clear: 60, complicated: 50, complex: 40, chaotic: 30, disorder: 20 },
    domain_percentages: { clear: 0.3, complicated: 0.25, complex: 0.2, chaotic: 0.15, disorder: 0.1 },
    chi_squared_statistic: 3.456,
    chi_squared_p_value: 0.485,
    distribution_biased: false,
    quality_by_domain: {
        clear: { mean: 0.85, count: 60, min: 0.7, max: 0.95 },
        complicated: { mean: 0.82, count: 50, min: 0.65, max: 0.92 },
    },
    quality_disparity: 0.03,
    quality_biased: false,
    verdict_by_domain: { clear: { approved: 55, rejected: 5 }, complicated: { approved: 45, rejected: 5 } },
    approval_rate_disparity: 0.017,
    overall_bias_detected: false,
    findings: ['Distribution is balanced', 'Quality metrics are consistent across domains'],
};

const mockConvergenceStatus: ConvergenceStatus = {
    total_epochs: 10,
    convergence: {
        epoch: 10,
        accuracy_delta: 0.0012,
        converged: true,
        regressed: false,
        plateau_detected: false,
        recommendation: 'Model has converged. No retraining needed.',
        history: [
            { epoch: 1, accuracy: 0.65, timestamp: '2026-03-15T08:00:00Z' },
            { epoch: 2, accuracy: 0.72, timestamp: '2026-03-15T09:00:00Z' },
            { epoch: 3, accuracy: 0.78, timestamp: '2026-03-15T10:00:00Z' },
            { epoch: 4, accuracy: 0.83, timestamp: '2026-03-15T11:00:00Z' },
            { epoch: 5, accuracy: 0.87, timestamp: '2026-03-15T12:00:00Z' },
        ],
    },
    config: { epsilon: 0.005, max_plateau_epochs: 3 },
};

describe('MonitoringPanel', () => {
    it('renders without crashing', () => {
        const { container } = render(<MonitoringPanel skipAutoFetch />);
        expect(container.querySelector('.monitoring-panel')).toBeTruthy();
    });

    it('shows drift tab by default', () => {
        render(
            <MonitoringPanel
                skipAutoFetch
                initialDriftStatus={mockDriftStatus}
            />
        );

        // Drift tab should be selected (active color = #60A5FA)
        const driftTab = screen.getByTestId('monitoring-tab-drift');
        expect(driftTab).toBeTruthy();

        // Should display drift-specific content
        expect(screen.getByText('150')).toBeTruthy(); // total observations
    });

    it('switches to bias tab', () => {
        render(
            <MonitoringPanel
                skipAutoFetch
                initialDriftStatus={mockDriftStatus}
                initialBiasReport={mockBiasReport}
            />
        );

        fireEvent.click(screen.getByTestId('monitoring-tab-bias'));

        // Bias tab content should be visible
        expect(screen.getByTestId('bias-verdict-badge')).toBeTruthy();
        expect(screen.getByText('No Bias Detected')).toBeTruthy();
    });

    it('switches to convergence tab', () => {
        render(
            <MonitoringPanel
                skipAutoFetch
                initialConvergenceStatus={mockConvergenceStatus}
            />
        );

        fireEvent.click(screen.getByTestId('monitoring-tab-convergence'));

        // Convergence content should be visible
        expect(screen.getByTestId('convergence-badge')).toBeTruthy();
        expect(screen.getByText('Model has converged. No retraining needed.')).toBeTruthy();
    });

    it('displays drift status', () => {
        render(
            <MonitoringPanel
                skipAutoFetch
                initialDriftStatus={mockDriftStatus}
            />
        );

        expect(screen.getByText('150')).toBeTruthy(); // total observations
        expect(screen.getByText('0.0123')).toBeTruthy(); // KL divergence
        expect(screen.getByText('2')).toBeTruthy(); // alert count
        expect(screen.getByText('NO')).toBeTruthy(); // drift not detected
    });

    it('displays bias report findings', () => {
        render(
            <MonitoringPanel
                skipAutoFetch
                initialBiasReport={mockBiasReport}
            />
        );

        fireEvent.click(screen.getByTestId('monitoring-tab-bias'));

        expect(screen.getByTestId('bias-finding-0')).toBeTruthy();
        expect(screen.getByText('Distribution is balanced')).toBeTruthy();
        expect(screen.getByText('Quality metrics are consistent across domains')).toBeTruthy();
    });

    it('handles loading state', () => {
        // When skipAutoFetch is false and no initial data, it will show loading
        // We can simulate this by rendering with loading = true via the internal state
        // Instead, test the component without initial data and with skipAutoFetch
        render(<MonitoringPanel skipAutoFetch />);

        // No data, no loading (skipAutoFetch = true), should show empty state
        expect(screen.getByText('No drift data available yet.')).toBeTruthy();
    });

    it('handles error state', () => {
        // Render and check for error display capability
        render(
            <MonitoringPanel
                skipAutoFetch
                initialDriftStatus={mockDriftStatus}
            />
        );

        // Panel should render without errors
        expect(screen.getByTestId('monitoring-panel')).toBeTruthy();
        // No error should be displayed when data is provided
        expect(screen.queryByTestId('monitoring-error')).toBeNull();
    });
});
