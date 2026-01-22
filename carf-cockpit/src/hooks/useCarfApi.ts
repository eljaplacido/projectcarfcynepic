/**
 * CARF API React Hooks
 *
 * Custom hooks for interacting with the CARF backend API.
 * Provides state management, loading indicators, and error handling.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import api, {
    type QueryRequest,
    type ChatRequest,
    type ChatResponse,
    type FileAnalysisResult,
    type ExplanationResponse,
    type ExplanationComponent,
    type DeveloperState,
    type LogEntry,
    type ConfigStatus,
    type ScenarioDetailResponse,
    type DatasetMetadata,
    ApiError,
} from '../services/apiService';
import type { QueryResponse, ScenarioMetadata } from '../types/carf';

// ============================================================================
// Generic API Hook
// ============================================================================

interface UseApiState<T> {
    data: T | null;
    loading: boolean;
    error: Error | null;
}

interface UseApiReturn<T, Args extends unknown[]> extends UseApiState<T> {
    execute: (...args: Args) => Promise<T | null>;
    reset: () => void;
}

function useApi<T, Args extends unknown[]>(
    apiFn: (...args: Args) => Promise<T>
): UseApiReturn<T, Args> {
    const [state, setState] = useState<UseApiState<T>>({
        data: null,
        loading: false,
        error: null,
    });

    const execute = useCallback(
        async (...args: Args): Promise<T | null> => {
            setState(prev => ({ ...prev, loading: true, error: null }));
            try {
                const data = await apiFn(...args);
                setState({ data, loading: false, error: null });
                return data;
            } catch (error) {
                const err = error instanceof Error ? error : new Error(String(error));
                setState({ data: null, loading: false, error: err });
                return null;
            }
        },
        [apiFn]
    );

    const reset = useCallback(() => {
        setState({ data: null, loading: false, error: null });
    }, []);

    return { ...state, execute, reset };
}

// ============================================================================
// Configuration Hook
// ============================================================================

export function useConfigStatus() {
    const [config, setConfig] = useState<ConfigStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        const fetchConfig = async () => {
            try {
                const status = await api.getConfigStatus();
                setConfig(status);
            } catch (e) {
                setError(e instanceof Error ? e : new Error(String(e)));
            } finally {
                setLoading(false);
            }
        };

        fetchConfig();
    }, []);

    return { config, loading, error, isDemoMode: config?.demo_mode ?? true };
}

// ============================================================================
// Scenarios Hook
// ============================================================================

export function useScenarios() {
    const [scenarios, setScenarios] = useState<ScenarioMetadata[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    const fetchScenarios = useCallback(async () => {
        setLoading(true);
        try {
            const response = await api.listScenarios();
            setScenarios(response.scenarios);
            setError(null);
        } catch (e) {
            setError(e instanceof Error ? e : new Error(String(e)));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchScenarios();
    }, [fetchScenarios]);

    const getScenario = useCallback(async (scenarioId: string): Promise<ScenarioDetailResponse | null> => {
        try {
            return await api.getScenario(scenarioId);
        } catch (e) {
            setError(e instanceof Error ? e : new Error(String(e)));
            return null;
        }
    }, []);

    return { scenarios, loading, error, fetchScenarios, getScenario };
}

// ============================================================================
// Query Hook
// ============================================================================

export interface UseQueryOptions {
    onSuccess?: (response: QueryResponse) => void;
    onError?: (error: Error) => void;
}

export function useQuery(options?: UseQueryOptions) {
    const [response, setResponse] = useState<QueryResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [progress, setProgress] = useState(0);

    const submitQuery = useCallback(
        async (request: QueryRequest): Promise<QueryResponse | null> => {
            setLoading(true);
            setError(null);
            setProgress(10);

            try {
                // Simulate progress updates
                const progressInterval = setInterval(() => {
                    setProgress(prev => Math.min(prev + 10, 90));
                }, 500);

                const result = await api.submitQuery(request);

                clearInterval(progressInterval);
                setProgress(100);
                setResponse(result);
                options?.onSuccess?.(result);

                // Reset progress after animation
                setTimeout(() => setProgress(0), 500);

                return result;
            } catch (e) {
                const err = e instanceof Error ? e : new Error(String(e));
                setError(err);
                options?.onError?.(err);
                setProgress(0);
                return null;
            } finally {
                setLoading(false);
            }
        },
        [options]
    );

    const reset = useCallback(() => {
        setResponse(null);
        setError(null);
        setProgress(0);
    }, []);

    return { response, loading, error, progress, submitQuery, reset };
}

// ============================================================================
// Chat Hook
// ============================================================================

export interface ChatMessageWithId {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    suggestions?: string[];
    linkedPanels?: string[];
    confidence?: string;
}

export function useChat(queryContext?: Record<string, unknown> | null) {
    const [messages, setMessages] = useState<ChatMessageWithId[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const sendMessage = useCallback(
        async (content: string): Promise<ChatResponse | null> => {
            // Add user message
            const userMessage: ChatMessageWithId = {
                id: `msg_${Date.now()}_user`,
                role: 'user',
                content,
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, userMessage]);

            setLoading(true);
            setError(null);

            try {
                const request: ChatRequest = {
                    messages: messages.concat(userMessage).map(m => ({
                        role: m.role,
                        content: m.content,
                    })),
                    query_context: queryContext,
                };

                const response = await api.sendChatMessage(request);

                // Add assistant response
                const assistantMessage: ChatMessageWithId = {
                    id: `msg_${Date.now()}_assistant`,
                    role: 'assistant',
                    content: response.message,
                    timestamp: new Date(),
                    suggestions: response.suggestions ?? undefined,
                    linkedPanels: response.linked_panels ?? undefined,
                    confidence: response.confidence ?? undefined,
                };
                setMessages(prev => [...prev, assistantMessage]);

                return response;
            } catch (e) {
                const err = e instanceof Error ? e : new Error(String(e));
                setError(err);

                // Add error message
                const errorMessage: ChatMessageWithId = {
                    id: `msg_${Date.now()}_error`,
                    role: 'system',
                    content: `Error: ${err.message}`,
                    timestamp: new Date(),
                };
                setMessages(prev => [...prev, errorMessage]);

                return null;
            } finally {
                setLoading(false);
            }
        },
        [messages, queryContext]
    );

    const addSystemMessage = useCallback((content: string) => {
        const systemMessage: ChatMessageWithId = {
            id: `msg_${Date.now()}_system`,
            role: 'system',
            content,
            timestamp: new Date(),
        };
        setMessages(prev => [...prev, systemMessage]);
    }, []);

    const clearMessages = useCallback(() => {
        setMessages([]);
        setError(null);
    }, []);

    return { messages, loading, error, sendMessage, addSystemMessage, clearMessages };
}

// ============================================================================
// File Analysis Hook
// ============================================================================

export function useFileAnalysis() {
    const [result, setResult] = useState<FileAnalysisResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [uploadProgress, setUploadProgress] = useState(0);

    const analyzeFile = useCallback(async (file: File): Promise<FileAnalysisResult | null> => {
        setLoading(true);
        setError(null);
        setUploadProgress(0);

        try {
            // Simulate upload progress
            const progressInterval = setInterval(() => {
                setUploadProgress(prev => Math.min(prev + 20, 90));
            }, 200);

            const analysisResult = await api.analyzeFile(file);

            clearInterval(progressInterval);
            setUploadProgress(100);
            setResult(analysisResult);

            setTimeout(() => setUploadProgress(0), 500);

            return analysisResult;
        } catch (e) {
            const err = e instanceof Error ? e : new Error(String(e));
            setError(err);
            setUploadProgress(0);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    const analyzeText = useCallback(async (text: string, query = ''): Promise<FileAnalysisResult | null> => {
        setLoading(true);
        setError(null);

        try {
            const analysisResult = await api.analyzeText(text, query);
            setResult(analysisResult);
            return analysisResult;
        } catch (e) {
            const err = e instanceof Error ? e : new Error(String(e));
            setError(err);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    const reset = useCallback(() => {
        setResult(null);
        setError(null);
        setUploadProgress(0);
    }, []);

    return { result, loading, error, uploadProgress, analyzeFile, analyzeText, reset };
}

// ============================================================================
// Explanation Hook
// ============================================================================

export function useExplanation() {
    const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const explain = useCallback(async (
        component: ExplanationComponent,
        elementId?: string,
        context?: Record<string, unknown>,
        detailLevel: 'brief' | 'standard' | 'detailed' = 'standard'
    ): Promise<ExplanationResponse | null> => {
        setLoading(true);
        setError(null);

        try {
            const result = await api.explainComponent(component, elementId, context, detailLevel);
            setExplanation(result);
            return result;
        } catch (e) {
            const err = e instanceof Error ? e : new Error(String(e));
            setError(err);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    const explainCynefin = useCallback(async (
        element: 'domain' | 'confidence' | 'entropy' | 'solver',
        value?: string
    ): Promise<ExplanationResponse | null> => {
        setLoading(true);
        setError(null);

        try {
            const result = await api.explainCynefinElement(element, value);
            setExplanation(result);
            return result;
        } catch (e) {
            const err = e instanceof Error ? e : new Error(String(e));
            setError(err);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    const explainCausal = useCallback(async (
        element: 'effect' | 'pvalue' | 'ci' | 'refutation' | 'confounder',
        value?: string
    ): Promise<ExplanationResponse | null> => {
        setLoading(true);
        setError(null);

        try {
            const result = await api.explainCausalElement(element, value);
            setExplanation(result);
            return result;
        } catch (e) {
            const err = e instanceof Error ? e : new Error(String(e));
            setError(err);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    const explainBayesian = useCallback(async (
        element: 'posterior' | 'epistemic' | 'aleatoric' | 'probe',
        value?: string
    ): Promise<ExplanationResponse | null> => {
        setLoading(true);
        setError(null);

        try {
            const result = await api.explainBayesianElement(element, value);
            setExplanation(result);
            return result;
        } catch (e) {
            const err = e instanceof Error ? e : new Error(String(e));
            setError(err);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    const explainGuardian = useCallback(async (
        element: 'policy' | 'verdict',
        policyName?: string
    ): Promise<ExplanationResponse | null> => {
        setLoading(true);
        setError(null);

        try {
            const result = await api.explainGuardianElement(element, policyName);
            setExplanation(result);
            return result;
        } catch (e) {
            const err = e instanceof Error ? e : new Error(String(e));
            setError(err);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    const reset = useCallback(() => {
        setExplanation(null);
        setError(null);
    }, []);

    return {
        explanation,
        loading,
        error,
        explain,
        explainCynefin,
        explainCausal,
        explainBayesian,
        explainGuardian,
        reset,
    };
}

// ============================================================================
// Developer State Hook
// ============================================================================

export function useDeveloperState(autoRefresh = false, refreshInterval = 5000) {
    const [state, setState] = useState<DeveloperState | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const [logs, setLogs] = useState<LogEntry[]>([]);

    // Fetch initial state
    const fetchState = useCallback(async () => {
        try {
            const devState = await api.getDeveloperState();
            setState(devState);
            setLogs(devState.recent_logs);
            setError(null);
        } catch (e) {
            setError(e instanceof Error ? e : new Error(String(e)));
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        fetchState();
    }, [fetchState]);

    // Auto-refresh polling
    useEffect(() => {
        if (!autoRefresh) return;

        const interval = setInterval(fetchState, refreshInterval);
        return () => clearInterval(interval);
    }, [autoRefresh, refreshInterval, fetchState]);

    // WebSocket connection for real-time logs
    const connectWebSocket = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
        }

        wsRef.current = api.connectDeveloperWebSocket(
            (log) => {
                setLogs(prev => [...prev.slice(-499), log]); // Keep last 500 logs
            },
            (error) => {
                console.error('WebSocket error:', error);
            },
            () => {
                console.log('WebSocket disconnected');
            }
        );
    }, []);

    const disconnectWebSocket = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            disconnectWebSocket();
        };
    }, [disconnectWebSocket]);

    return {
        state,
        logs,
        loading,
        error,
        fetchState,
        connectWebSocket,
        disconnectWebSocket,
        isWebSocketConnected: wsRef.current?.readyState === WebSocket.OPEN,
    };
}

// ============================================================================
// Datasets Hook
// ============================================================================

export function useDatasets() {
    const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    const fetchDatasets = useCallback(async () => {
        setLoading(true);
        try {
            const response = await api.listDatasets();
            setDatasets(response.datasets);
            setError(null);
        } catch (e) {
            setError(e instanceof Error ? e : new Error(String(e)));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchDatasets();
    }, [fetchDatasets]);

    const createDataset = useCallback(async (data: {
        name: string;
        description?: string;
        data: Record<string, unknown>[] | Record<string, unknown[]>;
    }): Promise<DatasetMetadata | null> => {
        try {
            const newDataset = await api.createDataset(data);
            setDatasets(prev => [...prev, newDataset]);
            return newDataset;
        } catch (e) {
            setError(e instanceof Error ? e : new Error(String(e)));
            return null;
        }
    }, []);

    const previewDataset = useCallback(async (datasetId: string, limit = 10) => {
        try {
            return await api.previewDataset(datasetId, limit);
        } catch (e) {
            setError(e instanceof Error ? e : new Error(String(e)));
            return null;
        }
    }, []);

    return { datasets, loading, error, fetchDatasets, createDataset, previewDataset };
}

// ============================================================================
// Export all hooks
// ============================================================================

export {
    useApi,
    ApiError,
};
