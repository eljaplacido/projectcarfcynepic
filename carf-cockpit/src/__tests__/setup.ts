import '@testing-library/jest-dom/vitest';
import { vi, beforeEach } from 'vitest';

// Mock fetch globally for API tests
(globalThis as { fetch?: typeof fetch }).fetch = vi.fn() as typeof fetch;

// Mock ResizeObserver for recharts ResponsiveContainer
if (typeof window !== 'undefined' && !window.ResizeObserver) {
    window.ResizeObserver = class ResizeObserverMock {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as unknown as typeof ResizeObserver;
}

// Reset mocks before each test
beforeEach(() => {
    vi.clearAllMocks();
});
