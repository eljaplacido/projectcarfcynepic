/**
 * Tests for the CARF API React Hooks
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useConfigStatus, useScenarios, useQuery, useChat, useExplanation, useDeveloperState } from '../hooks/useCarfApi';
import api from '../services/apiService';

// Mock the API service
vi.mock('../services/apiService', () => ({
    default: {
        getConfigStatus: vi.fn(),
        listScenarios: vi.fn(),
        submitQuery: vi.fn(),
        sendChatMessage: vi.fn(),
        explainComponent: vi.fn(),
        getDeveloperState: vi.fn(),
    },
}));

describe('useCarfApi Hooks', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('useConfigStatus', () => {
        it('should fetch config status on mount', async () => {
            const mockConfig = {
                demo_mode: true,
                llm_available: false,
                human_layer_available: true,
                message: 'Demo mode active',
            };

            vi.mocked(api.getConfigStatus).mockResolvedValue(mockConfig);

            const { result } = renderHook(() => useConfigStatus());

            // Initially loading
            expect(result.current.loading).toBe(true);

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            expect(result.current.config).toEqual(mockConfig);
            expect(result.current.isDemoMode).toBe(true);
        });

        it('should handle errors', async () => {
            vi.mocked(api.getConfigStatus).mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useConfigStatus());

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            expect(result.current.error).toBeDefined();
            expect(result.current.config).toBeNull();
        });
    });

    describe('useScenarios', () => {
        it('should fetch scenarios on mount', async () => {
            const mockScenarios = {
                scenarios: [
                    { id: 'scope3', name: 'Scope 3 Attribution', description: 'Sustainability analysis', payloadPath: '/data/scope3.json' },
                    { id: 'churn', name: 'Customer Churn', description: 'Business analysis', payloadPath: '/data/churn.json' },
                ],
            };

            vi.mocked(api.listScenarios).mockResolvedValue(mockScenarios);

            const { result } = renderHook(() => useScenarios());

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            expect(result.current.scenarios).toHaveLength(2);
            expect(result.current.scenarios[0].id).toBe('scope3');
        });

        it('should provide fetchScenarios function', async () => {
            vi.mocked(api.listScenarios).mockResolvedValue({ scenarios: [] });

            const { result } = renderHook(() => useScenarios());

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            // Update mock for refresh
            vi.mocked(api.listScenarios).mockResolvedValue({
                scenarios: [{ id: 'new', name: 'New Scenario', description: 'New', payloadPath: '/data/new.json' }],
            });

            act(() => {
                result.current.fetchScenarios();
            });

            await waitFor(() => {
                expect(result.current.scenarios).toHaveLength(1);
            });
        });
    });

    describe('useQuery', () => {
        it('should submit query and return response', async () => {
            const mockResponse = {
                sessionId: 'test-session',
                domain: 'complicated',
                domainConfidence: 0.85,
                response: 'Analysis complete',
            };

            vi.mocked(api.submitQuery).mockResolvedValue(mockResponse as any);

            const { result } = renderHook(() => useQuery());

            expect(result.current.loading).toBe(false);
            expect(result.current.response).toBeNull();

            let submitResult;
            await act(async () => {
                submitResult = await result.current.submitQuery({
                    query: 'What is the effect?',
                });
            });

            expect(submitResult).toEqual(mockResponse);
            expect(result.current.response).toEqual(mockResponse);
        });

        it('should track loading state during query', async () => {
            vi.mocked(api.submitQuery).mockImplementation(
                () => new Promise(resolve => setTimeout(() => resolve({} as any), 100))
            );

            const { result } = renderHook(() => useQuery());

            act(() => {
                result.current.submitQuery({ query: 'Test' });
            });

            expect(result.current.loading).toBe(true);

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });
        });

        it('should handle query errors', async () => {
            vi.mocked(api.submitQuery).mockRejectedValue(new Error('Query failed'));

            const { result } = renderHook(() => useQuery());

            await act(async () => {
                try {
                    await result.current.submitQuery({ query: 'Test' });
                } catch {
                    // Expected to throw
                }
            });

            expect(result.current.error).toBeDefined();
        });

        it('should provide reset function', async () => {
            vi.mocked(api.submitQuery).mockResolvedValue({ domain: 'complex' } as any);

            const { result } = renderHook(() => useQuery());

            await act(async () => {
                await result.current.submitQuery({ query: 'Test' });
            });

            expect(result.current.response).not.toBeNull();

            act(() => {
                result.current.reset();
            });

            expect(result.current.response).toBeNull();
            expect(result.current.error).toBeNull();
        });
    });

    describe('useChat', () => {
        it('should send chat message and return response', async () => {
            const mockResponse = {
                message: 'Here is the interpretation of your results.',
                suggestions: ['Try this', 'Or that'],
            };

            vi.mocked(api.sendChatMessage).mockResolvedValue(mockResponse);

            const { result } = renderHook(() => useChat());

            let chatResult;
            await act(async () => {
                chatResult = await result.current.sendMessage('What do these results mean?');
            });

            expect(chatResult).toEqual(mockResponse);
            expect(result.current.messages).toContainEqual(
                expect.objectContaining({ role: 'user', content: 'What do these results mean?' })
            );
        });

        it('should maintain conversation history', async () => {
            vi.mocked(api.sendChatMessage)
                .mockResolvedValueOnce({ message: 'Response 1' })
                .mockResolvedValueOnce({ message: 'Response 2' });

            const { result } = renderHook(() => useChat());

            await act(async () => {
                await result.current.sendMessage('Question 1');
            });

            await act(async () => {
                await result.current.sendMessage('Question 2');
            });

            expect(result.current.messages).toHaveLength(4); // 2 user + 2 assistant
        });

        it('should use query context from hook parameter', async () => {
            vi.mocked(api.sendChatMessage).mockResolvedValue({ message: 'OK' });

            const { result } = renderHook(() => useChat({ domain: 'complex', effect: 0.42 }));

            await act(async () => {
                await result.current.sendMessage('Test');
            });

            expect(api.sendChatMessage).toHaveBeenCalledWith(
                expect.objectContaining({
                    query_context: expect.objectContaining({ domain: 'complex' }),
                })
            );
        });

        it('should provide clearMessages function', async () => {
            vi.mocked(api.sendChatMessage).mockResolvedValue({ message: 'Response' });

            const { result } = renderHook(() => useChat());

            await act(async () => {
                await result.current.sendMessage('Test');
            });

            expect(result.current.messages.length).toBeGreaterThan(0);

            act(() => {
                result.current.clearMessages();
            });

            expect(result.current.messages).toHaveLength(0);
        });
    });

    describe('useExplanation', () => {
        it('should fetch explanation for component', async () => {
            const mockExplanation = {
                component: 'cynefin_domain',
                title: 'Complex Domain',
                summary: 'The Complex domain represents systems with emergent behavior.',
                key_points: ['Emergent behavior', 'Probe-sense-respond'],
                reliability_score: 0.85,
            };

            vi.mocked(api.explainComponent).mockResolvedValue(mockExplanation as any);

            const { result } = renderHook(() => useExplanation());

            await act(async () => {
                await result.current.explain('cynefin_domain', undefined, { domain: 'complex' });
            });

            expect(result.current.explanation).toEqual(mockExplanation);
        });

        it('should track loading state', async () => {
            vi.mocked(api.explainComponent).mockImplementation(
                () => new Promise(resolve => setTimeout(() => resolve({} as any), 100))
            );

            const { result } = renderHook(() => useExplanation());

            act(() => {
                result.current.explain('causal_effect');
            });

            expect(result.current.loading).toBe(true);

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });
        });

        it('should provide reset function', async () => {
            vi.mocked(api.explainComponent).mockResolvedValue({ title: 'Test' } as any);

            const { result } = renderHook(() => useExplanation());

            await act(async () => {
                await result.current.explain('bayesian_epistemic');
            });

            expect(result.current.explanation).not.toBeNull();

            act(() => {
                result.current.reset();
            });

            expect(result.current.explanation).toBeNull();
        });
    });

    describe('useDeveloperState', () => {
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
                architecture: [],
                execution_timeline: [],
                recent_logs: [],
            };

            vi.mocked(api.getDeveloperState).mockResolvedValue(mockState);

            const { result } = renderHook(() => useDeveloperState(false));

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            expect(result.current.state).toEqual(mockState);
        });

        it('should provide fetchState function', async () => {
            vi.mocked(api.getDeveloperState).mockResolvedValue({
                system: { queries_processed: 5 },
                recent_logs: [],
            } as any);

            const { result } = renderHook(() => useDeveloperState());

            await waitFor(() => {
                expect(result.current.state?.system.queries_processed).toBe(5);
            });

            vi.mocked(api.getDeveloperState).mockResolvedValue({
                system: { queries_processed: 10 },
                recent_logs: [],
            } as any);

            await act(async () => {
                await result.current.fetchState();
            });

            expect(result.current.state?.system.queries_processed).toBe(10);
        });
    });
});
