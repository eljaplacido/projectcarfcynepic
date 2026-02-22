import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PolicyIngestionPanel from '../components/carf/PolicyIngestionPanel';

// Mock apiService
vi.mock('../services/apiService', () => ({
    extractPoliciesFromText: vi.fn(),
    createFederatedPolicy: vi.fn(),
    getGovernanceDomains: vi.fn(),
}));

import {
    extractPoliciesFromText,
    getGovernanceDomains,
} from '../services/apiService';

const mockedExtractPoliciesFromText = vi.mocked(extractPoliciesFromText);
const mockedGetGovernanceDomains = vi.mocked(getGovernanceDomains);

describe('PolicyIngestionPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockedGetGovernanceDomains.mockResolvedValue([]);
    });

    it('renders text area and extract button', () => {
        render(<PolicyIngestionPanel />);

        // Verify the textarea is present via placeholder text
        expect(
            screen.getByPlaceholderText(/Paste policy text, regulatory guidelines/i)
        ).toBeInTheDocument();

        // Verify "Extract Rules" button is present
        expect(screen.getByText('Extract Rules')).toBeInTheDocument();

        // Verify heading
        expect(screen.getByText('Policy Text Extraction')).toBeInTheDocument();
    });

    it('extract button disabled when no text', () => {
        render(<PolicyIngestionPanel />);

        const extractButton = screen.getByText('Extract Rules');

        // Button should be disabled when textarea is empty
        expect(extractButton).toBeDisabled();
    });

    it('calls extractPoliciesFromText on extract', async () => {
        mockedExtractPoliciesFromText.mockResolvedValue({
            source_name: 'pasted_text',
            target_domain: null,
            rules_extracted: 1,
            rules: [
                {
                    name: 'Data Retention Limit',
                    condition: { data_type: 'personal' },
                    constraint: { max_retention_days: 365 },
                    message: 'Personal data must not be retained beyond 365 days',
                    severity: 'high',
                },
            ],
            error: null,
        });

        render(<PolicyIngestionPanel />);

        // Type text into the textarea
        const textarea = screen.getByPlaceholderText(/Paste policy text, regulatory guidelines/i);
        fireEvent.change(textarea, {
            target: { value: 'Personal data must not be retained for more than 365 days.' },
        });

        // Button should now be enabled
        const extractButton = screen.getByText('Extract Rules');
        expect(extractButton).not.toBeDisabled();

        // Click Extract Rules
        fireEvent.click(extractButton);

        // Verify the API was called with the pasted text
        await waitFor(() => {
            expect(mockedExtractPoliciesFromText).toHaveBeenCalledTimes(1);
        });
        expect(mockedExtractPoliciesFromText).toHaveBeenCalledWith(
            'Personal data must not be retained for more than 365 days.',
            'pasted_text',
            undefined
        );
    });

    it('shows extracted rules', async () => {
        mockedExtractPoliciesFromText.mockResolvedValue({
            source_name: 'pasted_text',
            target_domain: null,
            rules_extracted: 2,
            rules: [
                {
                    name: 'Data Retention Limit',
                    condition: { data_type: 'personal' },
                    constraint: { max_retention_days: 365 },
                    message: 'Personal data must not be retained beyond 365 days',
                    severity: 'high',
                },
                {
                    name: 'Encryption Requirement',
                    condition: { data_classification: 'sensitive' },
                    constraint: { encryption: 'AES-256' },
                    message: 'Sensitive data must be encrypted with AES-256',
                    severity: 'critical',
                },
            ],
            error: null,
        });

        render(<PolicyIngestionPanel />);

        // Type text and trigger extraction
        const textarea = screen.getByPlaceholderText(/Paste policy text, regulatory guidelines/i);
        fireEvent.change(textarea, {
            target: { value: 'Some policy text about data retention and encryption requirements.' },
        });
        fireEvent.click(screen.getByText('Extract Rules'));

        // Wait for and verify that extracted rule names appear
        await waitFor(() => {
            expect(screen.getByText('Data Retention Limit')).toBeInTheDocument();
        });
        expect(screen.getByText('Encryption Requirement')).toBeInTheDocument();

        // Verify rule messages appear
        expect(screen.getByText('Personal data must not be retained beyond 365 days')).toBeInTheDocument();
        expect(screen.getByText('Sensitive data must be encrypted with AES-256')).toBeInTheDocument();

        // Verify severity badges
        expect(screen.getByText('high')).toBeInTheDocument();
        expect(screen.getByText('critical')).toBeInTheDocument();

        // Verify the "Extracted Rules" section heading with count
        expect(screen.getByText('Extracted Rules (2)')).toBeInTheDocument();

        // Verify the "Add Selected" button shows the correct count
        expect(screen.getByText('Add 2 Selected')).toBeInTheDocument();
    });
});
