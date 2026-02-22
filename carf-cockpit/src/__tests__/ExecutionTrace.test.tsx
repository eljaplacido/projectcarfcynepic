import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ExecutionTrace from '../components/carf/ExecutionTrace';
import type { ReasoningStep } from '../types/carf';

const createStep = (overrides: Partial<ReasoningStep> = {}): ReasoningStep => ({
    node: 'test_node',
    action: 'Test action',
    confidence: 'high',
    timestamp: new Date().toISOString(),
    durationMs: 42,
    status: 'completed',
    ...overrides,
});

describe('ExecutionTrace', () => {
    it('renders empty state message when no steps', () => {
        render(<ExecutionTrace steps={[]} sessionId="test-session" />);
        expect(screen.getByText(/Execution trace will appear here/)).toBeTruthy();
    });

    it('renders "< 1ms" when durationMs is 0', () => {
        const steps = [createStep({ durationMs: 0 })];
        render(<ExecutionTrace steps={steps} sessionId="test-session" />);
        expect(screen.getByText('< 1ms')).toBeTruthy();
    });

    it('renders actual duration when durationMs > 0', () => {
        const steps = [createStep({ durationMs: 142 })];
        render(<ExecutionTrace steps={steps} sessionId="test-session" />);
        expect(screen.getByText('142ms')).toBeTruthy();
    });

    it('shows tooltip on confidence badge for high confidence', () => {
        const steps = [createStep({ confidence: 'high' })];
        render(<ExecutionTrace steps={steps} sessionId="test-session" />);
        const badge = screen.getByText('high');
        expect(badge.getAttribute('title')).toContain('Strong evidence');
    });

    it('shows tooltip on confidence badge for medium confidence', () => {
        const steps = [createStep({ confidence: 'medium' })];
        render(<ExecutionTrace steps={steps} sessionId="test-session" />);
        const badge = screen.getByText('medium');
        expect(badge.getAttribute('title')).toContain('Moderate evidence');
    });

    it('shows tooltip on confidence badge for low confidence', () => {
        const steps = [createStep({ confidence: 'low' })];
        render(<ExecutionTrace steps={steps} sessionId="test-session" />);
        const badge = screen.getByText('low');
        expect(badge.getAttribute('title')).toContain('Limited evidence');
    });

    it('renders multiple steps in timeline', () => {
        const steps = [
            createStep({ node: 'router', action: 'Route query' }),
            createStep({ node: 'causal_analyst', action: 'Analyze causality' }),
        ];
        render(<ExecutionTrace steps={steps} sessionId="test-session" />);
        expect(screen.getByText('router')).toBeTruthy();
        expect(screen.getByText('causal_analyst')).toBeTruthy();
    });

    it('shows session ID', () => {
        const steps = [createStep()];
        render(<ExecutionTrace steps={steps} sessionId="abc123def456" />);
        expect(screen.getByText(/abc123def456/)).toBeTruthy();
    });
});
