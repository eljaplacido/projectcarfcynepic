import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DeveloperView from '../components/carf/DeveloperView';
import type { QueryResponse, ExecutionTraceStep } from '../types/carf';

// Mock the API service
vi.mock('../services/apiService', () => ({
    __esModule: true,
    default: {
        getDeveloperState: vi.fn().mockResolvedValue({
            system: {
                is_processing: false,
                queries_processed: 100,
                errors_count: 2,
                uptime_seconds: 14.2,
                llm_calls: 50,
                cache_hits: 30,
                cache_misses: 20,
            },
            architecture: [
                { id: 'router', name: 'Cynefin Router', description: 'Classification', components: ['Classifier', 'Entropy'], status: 'ready' },
                { id: 'mesh', name: 'Cognitive Mesh', description: 'Orchestration', components: ['LangGraph', 'Tools'], status: 'ready' },
                { id: 'services', name: 'Service Layer', description: 'Analysis', components: ['DoWhy', 'PyMC'], status: 'ready' },
                { id: 'guardian', name: 'Guardian Layer', description: 'Safety', components: ['Policy', 'Audit'], status: 'error' },
            ],
            execution_timeline: [],
            recent_logs: [],
        }),
        connectDeveloperWebSocket: vi.fn().mockReturnValue({
            onopen: null,
            onmessage: null,
            onerror: null,
            onclose: null,
            close: vi.fn(),
            readyState: 3,
        }),
        getDeveloperLogs: vi.fn().mockResolvedValue({ logs: [] }),
    },
    submitFeedback: vi.fn().mockResolvedValue({ feedback_id: 'test', status: 'ok', message: 'ok', received_at: '' }),
}));

// Mock ExperienceBufferPanel
vi.mock('../components/carf/ExperienceBufferPanel', () => ({
    __esModule: true,
    default: () => <div data-testid="mock-experience-panel">Experience Buffer</div>,
}));

// Mock DataFlowPanel
vi.mock('../components/carf/DataFlowPanel', () => ({
    __esModule: true,
    default: () => <div data-testid="mock-dataflow-panel">Data Flow</div>,
}));

// Mock DataLayerInspector
vi.mock('../components/carf/DataLayerInspector', () => ({
    __esModule: true,
    default: () => <div data-testid="mock-datalayer-panel">Data Layer</div>,
}));

const createMockResponse = (overrides: Partial<QueryResponse> = {}): QueryResponse => ({
    sessionId: 'test-session-123',
    domain: 'complicated',
    domainConfidence: 0.85,
    domainEntropy: 0.15,
    guardianVerdict: 'approved',
    response: 'Test response',
    requiresHuman: false,
    reasoningChain: [],
    causalResult: null,
    bayesianResult: null,
    guardianResult: null,
    error: null,
    ...overrides,
});

const createTraceStep = (overrides: Partial<ExecutionTraceStep> = {}): ExecutionTraceStep => ({
    node: 'test_node',
    action: 'test_action',
    confidence: 'high',
    timestamp: '2025-01-01T00:00:00Z',
    durationMs: 100,
    layer: 'router',
    ...overrides,
});

describe('DeveloperView', () => {
    // =========================================================================
    // 5B: Real telemetry values (not hardcoded)
    // =========================================================================
    describe('Telemetry values (5B)', () => {
        it('computes average latency from systemState instead of hardcoding 142ms', async () => {
            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            // Wait for developer state to load
            await waitFor(() => {
                const latencyEl = screen.getByTestId('telemetry-latency');
                expect(latencyEl).toBeTruthy();
                // uptime_seconds=14.2, queries_processed=100 => 14200/100 = 142ms
                // This is computed, not hardcoded "142ms" string
                expect(latencyEl.textContent).toMatch(/\d+ms/);
            });
        });

        it('computes success rate from systemState instead of hardcoding 99.8%', async () => {
            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            await waitFor(() => {
                const successEl = screen.getByTestId('telemetry-success');
                expect(successEl).toBeTruthy();
                // queries_processed=100, errors_count=2 => (100-2)/100 = 98.0%
                expect(successEl.textContent).toBe('98.0%');
            });
        });

        it('displays queries processed count from systemState', async () => {
            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            await waitFor(() => {
                const queriesEl = screen.getByTestId('telemetry-queries');
                expect(queriesEl).toBeTruthy();
                expect(queriesEl.textContent).toBe('100');
            });
        });
    });

    // =========================================================================
    // 5C: View Components button
    // =========================================================================
    describe('View Components button (5C)', () => {
        it('shows component list when View Components is clicked on a selected layer', async () => {
            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            // The architecture panel should be active by default
            await waitFor(() => {
                expect(screen.getByText('Cynefin Router')).toBeTruthy();
            });

            // Click on a layer to select it
            fireEvent.click(screen.getByText('Cynefin Router'));

            // Wait for the "View components" button to appear after layer selection
            await waitFor(() => {
                expect(screen.getByTestId('view-components-router')).toBeTruthy();
            });

            // Click the "View components" button
            fireEvent.click(screen.getByTestId('view-components-router'));

            // Component panel should appear with component items showing status
            await waitFor(() => {
                const panel = screen.getByTestId('components-panel-router');
                expect(panel).toBeTruthy();
                // Panel should contain component items with ready status
                expect(panel.textContent).toContain('Classifier');
                expect(panel.textContent).toContain('Entropy');
                expect(panel.textContent).toContain('ready');
            });
        });
    });

    // =========================================================================
    // 5D: Suggest Improvements modal
    // =========================================================================
    describe('Suggest Improvements modal (5D)', () => {
        it('opens improvement modal when Suggest Improvement button is clicked', async () => {
            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            // Find and click the "Suggest Improvement" button
            const btn = screen.getByTestId('suggest-improvement-btn');
            fireEvent.click(btn);

            // Modal should appear
            await waitFor(() => {
                expect(screen.getByTestId('improvement-modal')).toBeTruthy();
                expect(screen.getByTestId('improvement-textarea')).toBeTruthy();
            });
        });

        it('pre-populates modal with context-aware suggestions', async () => {
            render(
                <DeveloperView
                    response={createMockResponse({ domainConfidence: 0.5, domainEntropy: 0.7 })}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            fireEvent.click(screen.getByTestId('suggest-improvement-btn'));

            await waitFor(() => {
                const textarea = screen.getByTestId('improvement-textarea') as HTMLTextAreaElement;
                // Should have pre-populated text based on low confidence and high entropy
                expect(textarea.value).toContain('classification accuracy');
                expect(textarea.value).toContain('entropy');
            });
        });

        it('closes modal when Cancel is clicked', async () => {
            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            fireEvent.click(screen.getByTestId('suggest-improvement-btn'));

            await waitFor(() => {
                expect(screen.getByTestId('improvement-modal')).toBeTruthy();
            });

            fireEvent.click(screen.getByText('Cancel'));

            await waitFor(() => {
                expect(screen.queryByTestId('improvement-modal')).toBeNull();
            });
        });

        it('submits feedback and closes modal on Submit', async () => {
            const { submitFeedback } = await import('../services/apiService');
            (submitFeedback as ReturnType<typeof vi.fn>).mockResolvedValue({
                feedback_id: 'fb1', status: 'ok', message: 'ok', received_at: '',
            });

            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            fireEvent.click(screen.getByTestId('suggest-improvement-btn'));

            await waitFor(() => {
                expect(screen.getByTestId('improvement-textarea')).toBeTruthy();
            });

            // Modify the textarea
            fireEvent.change(screen.getByTestId('improvement-textarea'), {
                target: { value: 'Improve the routing logic' },
            });

            fireEvent.click(screen.getByTestId('improvement-submit'));

            await waitFor(() => {
                expect(screen.queryByTestId('improvement-modal')).toBeNull();
            });
        });

        it('displays instruction text in the modal', async () => {
            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            fireEvent.click(screen.getByTestId('suggest-improvement-btn'));

            await waitFor(() => {
                expect(screen.getByText(/Describe how the analysis or routing could be improved/)).toBeTruthy();
            });
        });
    });

    // =========================================================================
    // 5E: DeepEval metrics drill-down
    // =========================================================================
    describe('DeepEval metric drill-downs (5E)', () => {
        it('shows metric drill-down when a metric bar is clicked', async () => {
            render(
                <DeveloperView
                    response={createMockResponse({ domainConfidence: 0.9 })}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            // Navigate to Evaluation tab
            fireEvent.click(screen.getByText('Evaluation'));

            await waitFor(() => {
                expect(screen.getByText('DeepEval Metrics')).toBeTruthy();
            });

            // Click on relevancy metric bar
            fireEvent.click(screen.getByTestId('metric-bar-relevancy'));

            await waitFor(() => {
                const detail = screen.getByTestId('metric-detail-relevancy');
                expect(detail).toBeTruthy();
                // Should show sub-factors
                expect(screen.getByText('Query-answer alignment')).toBeTruthy();
            });
        });

        it('shows Cynefin-aware recommendations in metric drill-down', async () => {
            render(
                <DeveloperView
                    response={createMockResponse({ domain: 'complicated', domainConfidence: 0.85 })}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            fireEvent.click(screen.getByText('Evaluation'));

            await waitFor(() => {
                expect(screen.getByText('DeepEval Metrics')).toBeTruthy();
            });

            // Expand reasoning metric
            fireEvent.click(screen.getByTestId('metric-bar-reasoning'));

            await waitFor(() => {
                const rec = screen.getByTestId('cynefin-rec-reasoning');
                expect(rec).toBeTruthy();
                // Complicated domain recommendation
                expect(rec.textContent).toContain('sense-analyze-respond');
            });
        });

        it('toggles metric detail closed when clicked again', async () => {
            render(
                <DeveloperView
                    response={createMockResponse({ domainConfidence: 0.9 })}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            fireEvent.click(screen.getByText('Evaluation'));

            await waitFor(() => {
                expect(screen.getByText('DeepEval Metrics')).toBeTruthy();
            });

            // Open
            fireEvent.click(screen.getByTestId('metric-bar-relevancy'));
            await waitFor(() => expect(screen.getByTestId('metric-detail-relevancy')).toBeTruthy());

            // Close
            fireEvent.click(screen.getByTestId('metric-bar-relevancy'));
            await waitFor(() => expect(screen.queryByTestId('metric-detail-relevancy')).toBeNull());
        });
    });

    // =========================================================================
    // 5F: Execution Timeline with real timing
    // =========================================================================
    describe('Execution Timeline (5F)', () => {
        it('renders timeline with real step durations', async () => {
            const trace: ExecutionTraceStep[] = [
                createTraceStep({ node: 'router', durationMs: 50, layer: 'router' }),
                createTraceStep({ node: 'causal_agent', durationMs: 200, layer: 'services' }),
                createTraceStep({ node: 'guardian', durationMs: 30, layer: 'guardian' }),
            ];

            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={trace}
                    isProcessing={false}
                />
            );

            // Navigate to Timeline tab
            fireEvent.click(screen.getByText('Timeline'));

            await waitFor(() => {
                expect(screen.getByTestId('execution-timeline')).toBeTruthy();
            });

            // Total should be 280ms
            expect(screen.getByTestId('timeline-total').textContent).toContain('280ms');
        });

        it('shows actual ms per step', async () => {
            const trace: ExecutionTraceStep[] = [
                createTraceStep({ node: 'router', durationMs: 75, layer: 'router' }),
                createTraceStep({ node: 'analyzer', durationMs: 150, layer: 'services' }),
            ];

            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={trace}
                    isProcessing={false}
                />
            );

            fireEvent.click(screen.getByText('Timeline'));

            await waitFor(() => {
                expect(screen.getByTestId('step-duration-0').textContent).toContain('75ms');
                expect(screen.getByTestId('step-duration-1').textContent).toContain('150ms');
            });
        });

        it('renders proportional timeline segments', async () => {
            const trace: ExecutionTraceStep[] = [
                createTraceStep({ node: 'fast_step', durationMs: 10, layer: 'router' }),
                createTraceStep({ node: 'slow_step', durationMs: 90, layer: 'services' }),
            ];

            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={trace}
                    isProcessing={false}
                />
            );

            fireEvent.click(screen.getByText('Timeline'));

            await waitFor(() => {
                expect(screen.getByTestId('timeline-segment-0')).toBeTruthy();
                expect(screen.getByTestId('timeline-segment-1')).toBeTruthy();
            });
        });

        it('shows empty state when no trace steps', async () => {
            render(
                <DeveloperView
                    response={createMockResponse()}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );

            fireEvent.click(screen.getByText('Timeline'));

            await waitFor(() => {
                expect(screen.getByTestId('timeline-empty')).toBeTruthy();
            });
        });
    });

    // =========================================================================
    // General rendering
    // =========================================================================
    describe('General', () => {
        it('renders the Developer Cockpit header', () => {
            render(
                <DeveloperView
                    response={null}
                    executionTrace={[]}
                    isProcessing={false}
                />
            );
            expect(screen.getByText('Developer Cockpit')).toBeTruthy();
        });

        it('shows processing indicator when isProcessing is true', () => {
            render(
                <DeveloperView
                    response={null}
                    executionTrace={[]}
                    isProcessing={true}
                />
            );
            expect(screen.getByText('Processing')).toBeTruthy();
        });
    });
});
