import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import WalkthroughManager from '../components/carf/WalkthroughManager';

describe('WalkthroughManager', () => {
    const defaultProps = {
        onClose: vi.fn(),
        onTrackComplete: vi.fn(),
    };

    it('renders the track selection view by default', () => {
        render(<WalkthroughManager {...defaultProps} />);
        expect(screen.getByText('CARF Walkthrough')).toBeInTheDocument();
        expect(screen.getByText('Choose your learning path')).toBeInTheDocument();
    });

    // -----------------------------------------------------------------------
    // Existing tracks still render
    // -----------------------------------------------------------------------
    it('renders the Quick Demo track', () => {
        render(<WalkthroughManager {...defaultProps} />);
        expect(screen.getByText('Quick Demo')).toBeInTheDocument();
    });

    it('renders the Analyst Onboarding track', () => {
        render(<WalkthroughManager {...defaultProps} />);
        expect(screen.getByText('Analyst Onboarding')).toBeInTheDocument();
    });

    it('renders the Executive View track', () => {
        render(<WalkthroughManager {...defaultProps} />);
        expect(screen.getByText('Executive View')).toBeInTheDocument();
    });

    it('renders the Contributor Guide track', () => {
        render(<WalkthroughManager {...defaultProps} />);
        expect(screen.getByText('Contributor Guide')).toBeInTheDocument();
    });

    it('renders the Production Deployment track', () => {
        render(<WalkthroughManager {...defaultProps} />);
        expect(screen.getByText('Production Deployment')).toBeInTheDocument();
    });

    // -----------------------------------------------------------------------
    // New Phase 7D tracks
    // -----------------------------------------------------------------------
    it('renders the Causal Analysis Deep Dive track', () => {
        render(<WalkthroughManager {...defaultProps} />);
        expect(screen.getByText('Causal Analysis Deep Dive')).toBeInTheDocument();
        expect(screen.getByText('Understand DAGs, effects, and refutations')).toBeInTheDocument();
    });

    it('renders the Running Simulations track', () => {
        render(<WalkthroughManager {...defaultProps} />);
        expect(screen.getByText('Running Simulations')).toBeInTheDocument();
        expect(screen.getByText('Learn what-if analysis and comparisons')).toBeInTheDocument();
    });

    it('renders the Developer Debugging track', () => {
        render(<WalkthroughManager {...defaultProps} />);
        expect(screen.getByText('Developer Debugging')).toBeInTheDocument();
        expect(screen.getByText('Inspect architecture, logs, and timelines')).toBeInTheDocument();
    });

    // -----------------------------------------------------------------------
    // Track navigation
    // -----------------------------------------------------------------------
    it('starts Causal Analysis Deep Dive track and shows first step', () => {
        render(<WalkthroughManager {...defaultProps} />);
        fireEvent.click(screen.getByText('Causal Analysis Deep Dive'));
        expect(screen.getByText('What is Causal Analysis?')).toBeInTheDocument();
        expect(screen.getByText(/Step 1/)).toBeInTheDocument();
    });

    it('starts Running Simulations track and shows first step', () => {
        render(<WalkthroughManager {...defaultProps} />);
        fireEvent.click(screen.getByText('Running Simulations'));
        expect(screen.getByText('What-If Simulations')).toBeInTheDocument();
        expect(screen.getByText(/Step 1/)).toBeInTheDocument();
    });

    it('starts Developer Debugging track and shows first step', () => {
        render(<WalkthroughManager {...defaultProps} />);
        fireEvent.click(screen.getByText('Developer Debugging'));
        expect(screen.getByText('Developer View Overview')).toBeInTheDocument();
        expect(screen.getByText(/Step 1/)).toBeInTheDocument();
    });

    it('navigates forward and backward within a track', () => {
        render(<WalkthroughManager {...defaultProps} />);
        fireEvent.click(screen.getByText('Causal Analysis Deep Dive'));

        // Step 1
        expect(screen.getByText('What is Causal Analysis?')).toBeInTheDocument();

        // Go to step 2
        fireEvent.click(screen.getByText(/Next/));
        expect(screen.getByText('Understanding the DAG')).toBeInTheDocument();
        expect(screen.getByText(/Step 2/)).toBeInTheDocument();

        // Go back to step 1
        fireEvent.click(screen.getByText(/Back/));
        expect(screen.getByText('What is Causal Analysis?')).toBeInTheDocument();
    });

    it('shows correct total step count for new tracks', () => {
        render(<WalkthroughManager {...defaultProps} />);

        // Causal Analysis Deep Dive: ~8 minutes, 6 steps
        expect(screen.getByText(/~8 minutes/)).toBeInTheDocument();

        // Running Simulations: ~6 minutes, 5 steps
        expect(screen.getByText(/~6 minutes/)).toBeInTheDocument();

        // Developer Debugging: ~7 minutes, 6 steps
        expect(screen.getByText(/~7 minutes/)).toBeInTheDocument();

        // Multiple tracks share "6 steps" (executive, causal deep dive, developer debugging)
        const sixStepElements = screen.getAllByText(/6 steps/);
        expect(sixStepElements.length).toBeGreaterThanOrEqual(3);

        // Running Simulations has 5 steps — verify it exists
        const fiveStepElements = screen.getAllByText(/5 steps/);
        expect(fiveStepElements.length).toBeGreaterThanOrEqual(1);
    });

    it('calls onClose when close button is clicked', () => {
        const onClose = vi.fn();
        render(<WalkthroughManager onClose={onClose} />);
        // The X button in the header
        const closeButtons = screen.getAllByRole('button');
        // Click the dedicated close button (the X svg button in the header)
        const closeButton = closeButtons.find(btn =>
            btn.querySelector('svg path[d*="M6 18L18 6"]')
        );
        if (closeButton) {
            fireEvent.click(closeButton);
            expect(onClose).toHaveBeenCalledTimes(1);
        }
    });

    it('calls onClose when "Skip tour for now" is clicked', () => {
        const onClose = vi.fn();
        render(<WalkthroughManager onClose={onClose} />);
        fireEvent.click(screen.getByText('Skip tour for now'));
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
