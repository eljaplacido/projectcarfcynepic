/**
 * Tests for the CARF API Service
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import api, {
    checkHealth,
    getConfigStatus,
    listScenarios,
    submitQuery,
    analyzeFile,
    sendChatMessage,
    explainComponent,
    getDeveloperState,
    ApiError,
} from '../services/apiService';

// Mock fetch globally
const mockFetch = vi.fn();
(globalThis as { fetch?: typeof fetch }).fetch = mockFetch as typeof fetch;

describe('API Service', () => {
    beforeEach(() => {
        mockFetch.mockReset();
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    describe('checkHealth', () => {
        it('should return health status on success', async () => {
            const mockResponse = {
                status: 'healthy',
                phase: 'Phase 7',
                version: '1.0.0',
                components: { causal: 'ready', bayesian: 'ready' },
            };

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse),
            });

            const result = await checkHealth();

            expect(result).toEqual(mockResponse);
            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/health'),
                expect.any(Object)
            );
        });

        it('should throw ApiError on failure', async () => {
            // Use 400 error to avoid retry delays (4xx errors don't retry)
            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 400,
                statusText: 'Bad Request',
                json: () => Promise.resolve({ detail: 'Bad request' }),
            });

            await expect(checkHealth()).rejects.toThrow(ApiError);
        });
    });

    describe('getConfigStatus', () => {
        it('should return config status', async () => {
            const mockConfig = {
                demo_mode: true,
                llm_available: false,
                human_layer_available: true,
                message: 'Running in demo mode',
            };

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockConfig),
            });

            const result = await getConfigStatus();

            expect(result).toEqual(mockConfig);
            expect(result.demo_mode).toBe(true);
        });
    });

    describe('listScenarios', () => {
        it('should return list of scenarios', async () => {
            const mockScenarios = {
                scenarios: [
                    { id: 'scope3', name: 'Scope 3 Attribution' },
                    { id: 'churn', name: 'Customer Churn' },
                ],
            };

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockScenarios),
            });

            const result = await listScenarios();

            expect(result.scenarios).toHaveLength(2);
            expect(result.scenarios[0].id).toBe('scope3');
        });
    });

    describe('submitQuery', () => {
        it('should submit query and return response', async () => {
            const mockResponse = {
                sessionId: 'test-session',
                domain: 'complicated',
                domainConfidence: 0.85,
                causalResult: {
                    effect: 0.42,
                    pValue: 0.03,
                },
            };

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse),
            });

            const result = await submitQuery({
                query: 'What is the effect of X on Y?',
            });

            expect(result.domain).toBe('complicated');
            expect(result.domainConfidence).toBe(0.85);
        });

        it('should include context in request', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ sessionId: 'test' }),
            });

            await submitQuery({
                query: 'Test query',
                context: { scenario_id: 'test-scenario' },
            });

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/query'),
                expect.objectContaining({
                    method: 'POST',
                    body: expect.stringContaining('test-scenario'),
                })
            );
        });
    });

    describe('analyzeFile', () => {
        it('should upload and analyze file', async () => {
            const mockResult = {
                file_type: 'csv',
                file_name: 'test.csv',
                file_size: 1024,
                row_count: 100,
                column_count: 5,
                columns: ['id', 'name', 'value', 'treatment', 'outcome'],
                analysis_ready: true,
            };

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResult),
            });

            const file = new File(['test content'], 'test.csv', { type: 'text/csv' });
            const result = await analyzeFile(file);

            expect(result.file_type).toBe('csv');
            expect(result.row_count).toBe(100);
            expect(result.analysis_ready).toBe(true);
        });

        it('should throw error on upload failure', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 413,
                statusText: 'Payload Too Large',
                json: () => Promise.resolve({ detail: 'File too large' }),
            });

            const file = new File(['large content'], 'large.csv', { type: 'text/csv' });

            await expect(analyzeFile(file)).rejects.toThrow(ApiError);
        });
    });

    describe('sendChatMessage', () => {
        it('should send chat message and return response', async () => {
            const mockResponse = {
                message: 'Based on your analysis, the effect size is significant.',
                suggestions: ['Try adjusting confounders', 'Run refutation tests'],
            };

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse),
            });

            const result = await sendChatMessage({
                messages: [{ role: 'user', content: 'What do these results mean?' }],
            });

            expect(result.message).toContain('effect size');
            expect(result.suggestions).toHaveLength(2);
        });

        it('should include query context', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ message: 'Response' }),
            });

            await sendChatMessage({
                messages: [{ role: 'user', content: 'Test' }],
                query_context: { domain: 'complex', confidence: 0.9 },
            });

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/chat'),
                expect.objectContaining({
                    body: expect.stringContaining('complex'),
                })
            );
        });
    });

    describe('explainComponent', () => {
        it('should fetch component explanation', async () => {
            const mockExplanation = {
                component: 'cynefin_domain',
                title: 'Complex Domain',
                summary: 'The Complex domain represents...',
                key_points: ['Emergent behavior', 'Probe-sense-respond'],
                reliability_score: 0.85,
            };

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockExplanation),
            });

            const result = await explainComponent('cynefin_domain', undefined, { domain: 'complex' });

            expect(result.component).toBe('cynefin_domain');
            expect(result.title).toBe('Complex Domain');
            expect(result.key_points).toContain('Emergent behavior');
        });

        it('should include element_id when provided', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ component: 'causal_refutation', title: 'Test' }),
            });

            await explainComponent('causal_refutation', 'placebo_test', {});

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/explain'),
                expect.objectContaining({
                    body: expect.stringContaining('placebo_test'),
                })
            );
        });
    });

    describe('getDeveloperState', () => {
        it('should fetch developer state', async () => {
            const mockState = {
                system: {
                    is_processing: false,
                    queries_processed: 10,
                    uptime_seconds: 3600,
                    llm_calls: 25,
                    cache_hits: 15,
                    cache_misses: 10,
                    errors_count: 0,
                },
                architecture: [
                    { id: 'router', name: 'Router Layer', status: 'active' },
                ],
                execution_timeline: [],
                recent_logs: [],
            };

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockState),
            });

            const result = await getDeveloperState();

            expect(result.system.queries_processed).toBe(10);
            expect(result.architecture).toHaveLength(1);
        });
    });

    describe('API Error Handling', () => {
        it('should retry on server errors', async () => {
            vi.useFakeTimers();

            // First two calls fail, third succeeds
            mockFetch
                .mockResolvedValueOnce({
                    ok: false,
                    status: 503,
                    statusText: 'Service Unavailable',
                    json: () => Promise.resolve({}),
                })
                .mockResolvedValueOnce({
                    ok: false,
                    status: 503,
                    statusText: 'Service Unavailable',
                    json: () => Promise.resolve({}),
                })
                .mockResolvedValueOnce({
                    ok: true,
                    json: () => Promise.resolve({ status: 'healthy' }),
                });

            const resultPromise = checkHealth();

            // Fast-forward through retry delays
            await vi.advanceTimersByTimeAsync(1000); // First retry delay
            await vi.advanceTimersByTimeAsync(2000); // Second retry delay

            const result = await resultPromise;

            expect(result.status).toBe('healthy');
            expect(mockFetch).toHaveBeenCalledTimes(3);

            vi.useRealTimers();
        });

        it('should not retry on client errors', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 400,
                statusText: 'Bad Request',
                json: () => Promise.resolve({ detail: 'Invalid query' }),
            });

            await expect(submitQuery({ query: '' })).rejects.toThrow(ApiError);
            expect(mockFetch).toHaveBeenCalledTimes(1);
        });

        it('should include error details in ApiError', async () => {
            const errorDetail = { detail: 'Query validation failed', code: 'INVALID_QUERY' };

            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 422,
                statusText: 'Unprocessable Entity',
                json: () => Promise.resolve(errorDetail),
            });

            try {
                await submitQuery({ query: '' });
                expect.fail('Should have thrown');
            } catch (error) {
                expect(error).toBeInstanceOf(ApiError);
                expect((error as ApiError).status).toBe(422);
                expect((error as ApiError).details).toEqual(errorDetail);
            }
        });
    });

    describe('Default export', () => {
        it('should export all API functions', () => {
            expect(api.checkHealth).toBeDefined();
            expect(api.getConfigStatus).toBeDefined();
            expect(api.listScenarios).toBeDefined();
            expect(api.submitQuery).toBeDefined();
            expect(api.analyzeFile).toBeDefined();
            expect(api.sendChatMessage).toBeDefined();
            expect(api.explainComponent).toBeDefined();
            expect(api.getDeveloperState).toBeDefined();
        });
    });
});
