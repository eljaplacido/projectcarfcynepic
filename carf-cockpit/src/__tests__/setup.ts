import '@testing-library/jest-dom/vitest';
import { vi, beforeEach } from 'vitest';

// Mock fetch globally for API tests
(globalThis as { fetch?: typeof fetch }).fetch = vi.fn() as typeof fetch;

// Reset mocks before each test
beforeEach(() => {
    vi.clearAllMocks();
});
