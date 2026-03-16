// Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
/**
 * CARF API Service
 *
 * Full typed API client for all CARF backend endpoints.
 * Provides error handling, retry logic, and streaming support.
 */

import type {
    QueryResponse,
    ScenarioMetadata,
} from '../types/carf';

import { firebaseAuth, isFirebaseEnabled } from './firebaseConfig';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Get auth headers for API requests.
 * Returns a Firebase JWT Bearer token when auth is enabled.
 */
async function getAuthHeaders(): Promise<Record<string, string>> {
    if (!isFirebaseEnabled || !firebaseAuth?.currentUser) {
        return {};
    }
    const token = await firebaseAuth.currentUser.getIdToken();
    return { Authorization: `Bearer ${token}` };
}

// Types for API requests and responses
export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
}

export interface ChatRequest {
    messages: ChatMessage[];
    query_context?: Record<string, unknown> | null;
    system_prompt?: string | null;
    max_tokens?: number;
}

export interface ChatResponse {
    message: string;
    suggestions?: string[] | null;
    linked_panels?: string[] | null;
    confidence?: string | null;
}

export interface FileAnalysisResult {
    file_type: string;
    file_name: string;
    file_size: number;
    row_count?: number | null;
    column_count?: number | null;
    columns?: string[] | null;
    column_types?: Record<string, string> | null;
    text_content?: string | null;
    data_preview?: Record<string, unknown>[] | null;
    suggested_treatment?: string | null;
    suggested_outcome?: string | null;
    suggested_covariates?: string[] | null;
    analysis_ready: boolean;
    error?: string | null;
}

export interface ExplanationResponse {
    component: string;
    element_id?: string | null;
    title: string;
    summary: string;
    key_points: string[];
    implications: string;
    reliability: string;
    reliability_score: number;
    related_concepts: string[];
    learn_more_links: string[];
}

export interface LogEntry {
    timestamp: string;
    level: string;
    layer: string;
    message: string;
    metadata?: Record<string, unknown> | null;
}

export interface SystemState {
    session_id?: string | null;
    is_processing: boolean;
    current_layer?: string | null;
    last_query?: string | null;
    last_domain?: string | null;
    uptime_seconds: number;
    queries_processed: number;
    errors_count: number;
    llm_calls: number;
    cache_hits: number;
    cache_misses: number;
}

export interface ArchitectureLayer {
    id: string;
    name: string;
    description: string;
    components: string[];
    status: string;
    last_activity?: string | null;
}

export interface ExecutionStep {
    step_id: string;
    layer: string;
    name: string;
    start_time: number;
    end_time?: number | null;
    duration_ms?: number | null;
    status: string;
    input_summary?: string | null;
    output_summary?: string | null;
}

export interface DeveloperState {
    system: SystemState;
    architecture: ArchitectureLayer[];
    execution_timeline: ExecutionStep[];
    recent_logs: LogEntry[];
}

export interface ConfigStatus {
    demo_mode: boolean;
    llm_available: boolean;
    llm_provider?: string | null;
    human_layer_available: boolean;
    message: string;
}

export interface QueryRequest {
    query: string;
    context?: Record<string, unknown> | null;
    causal_estimation?: Record<string, unknown> | null;
    bayesian_inference?: Record<string, unknown> | null;
    dataset_selection?: {
        dataset_id: string;
        treatment: string;
        outcome: string;
        covariates?: string[];
        effect_modifiers?: string[];
    } | null;
}

export interface ScenarioDetailResponse {
    scenario: ScenarioMetadata;
    payload: Record<string, unknown>;
}

// API Error class
export class ApiError extends Error {
    constructor(
        public status: number,
        message: string,
        public details?: unknown
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

// Retry configuration
const RETRY_CONFIG = {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
};

// Helper function for retries with exponential backoff
async function withRetry<T>(
    fn: () => Promise<T>,
    retries = RETRY_CONFIG.maxRetries
): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error as Error;

            // Don't retry on client errors (4xx)
            if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
                throw error;
            }

            if (attempt < retries) {
                const delay = Math.min(
                    RETRY_CONFIG.baseDelay * Math.pow(2, attempt),
                    RETRY_CONFIG.maxDelay
                );
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    throw lastError;
}

// Generic fetch wrapper
async function apiFetch<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const authHeaders = await getAuthHeaders();

    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...authHeaders,
            ...options.headers,
        },
    });

    if (!response.ok) {
        let details: unknown;
        try {
            details = await response.json();
        } catch {
            details = await response.text();
        }
        throw new ApiError(response.status, `API Error: ${response.statusText}`, details);
    }

    return response.json();
}

// ============================================================================
// Health & Configuration
// ============================================================================

export async function checkHealth(): Promise<{
    status: string;
    phase: string;
    version: string;
    components: Record<string, string>;
}> {
    return withRetry(() => apiFetch('/health'));
}

export async function getConfigStatus(): Promise<ConfigStatus> {
    return withRetry(() => apiFetch('/config/status'));
}

export async function validateConfig(provider: string, apiKey?: string, baseUrl?: string): Promise<{ valid: boolean; message: string }> {
    return withRetry(() => apiFetch('/config/validate', {
        method: 'POST',
        body: JSON.stringify({ provider, api_key: apiKey, base_url: baseUrl }),
    }));
}

export async function updateConfig(provider: string, apiKey?: string, baseUrl?: string): Promise<{ status: string }> {
    return withRetry(() => apiFetch('/config/update', {
        method: 'POST',
        body: JSON.stringify({ provider, api_key: apiKey, base_url: baseUrl }),
    }));
}

// ============================================================================
// Scenarios API
// ============================================================================

export async function listScenarios(): Promise<{ scenarios: ScenarioMetadata[] }> {
    return withRetry(() => apiFetch('/scenarios'));
}

export async function getScenario(scenarioId: string): Promise<ScenarioDetailResponse> {
    return withRetry(() => apiFetch(`/scenarios/${encodeURIComponent(scenarioId)}`));
}

// ============================================================================
// Query API
// ============================================================================

export async function submitQuery(request: QueryRequest): Promise<QueryResponse> {
    return withRetry(() =>
        apiFetch('/query', {
            method: 'POST',
            body: JSON.stringify(request),
        })
    );
}

// Progress update from SSE stream
export interface ProgressUpdate {
    step: string;           // 'init', 'router', 'domain_agent', 'guardian', 'complete', 'error'
    status: string;         // 'started', 'completed', 'error'
    message: string;        // Human-readable progress message
    progress_percent: number; // 0-100
    timestamp: string;      // ISO timestamp
    details?: Record<string, unknown> | null; // Step-specific metadata
}

/**
 * Submit a query with real-time progress streaming via SSE.
 * This allows showing users chain-of-thought as analysis progresses.
 *
 * @param request - The query request
 * @param onProgress - Callback for each progress update
 * @param onComplete - Callback when analysis completes with final result
 * @param onError - Callback for errors
 * @returns AbortController to cancel the stream if needed
 */
export function submitQueryStream(
    request: QueryRequest,
    onProgress: (update: ProgressUpdate) => void,
    onComplete: (result: QueryResponse) => void,
    onError: (error: Error) => void
): AbortController {
    const controller = new AbortController();

    (async () => {
        try {
            const authHeaders = await getAuthHeaders();
            const response = await fetch(`${API_BASE_URL}/query/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...authHeaders,
                },
                body: JSON.stringify(request),
                signal: controller.signal,
            });

            if (!response.ok) {
                throw new ApiError(response.status, `Stream Error: ${response.statusText}`);
            }

            const reader = response.body?.getReader();
            if (!reader) {
                throw new Error('No response body for SSE stream');
            }

            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            // Check if this is the final result
                            if (data.step === 'complete' && data.details?.result) {
                                onComplete(data.details.result as QueryResponse);
                            } else if (data.step === 'error') {
                                onError(new Error(data.message || 'Analysis failed'));
                            } else {
                                onProgress(data as ProgressUpdate);
                            }
                        } catch {
                            console.warn('Failed to parse SSE data:', line);
                        }
                    }
                }
            }
        } catch (error) {
            if ((error as Error).name !== 'AbortError') {
                onError(error as Error);
            }
        }
    })();

    return controller;
}

// ============================================================================
// Datasets API
// ============================================================================

export interface DatasetMetadata {
    dataset_id: string;
    name: string;
    description?: string | null;
    created_at: string;
    row_count: number;
    column_names: string[];
}

export async function listDatasets(): Promise<{ datasets: DatasetMetadata[] }> {
    return withRetry(() => apiFetch('/datasets'));
}

export async function createDataset(data: {
    name: string;
    description?: string;
    data: Record<string, unknown>[] | Record<string, unknown[]>;
}): Promise<DatasetMetadata> {
    return withRetry(() =>
        apiFetch('/datasets', {
            method: 'POST',
            body: JSON.stringify(data),
        })
    );
}

export async function previewDataset(
    datasetId: string,
    limit = 10
): Promise<{ dataset_id: string; rows: Record<string, unknown>[] }> {
    return withRetry(() =>
        apiFetch(`/datasets/${encodeURIComponent(datasetId)}/preview?limit=${limit}`)
    );
}

// ============================================================================
// Analyze API (File Upload)
// ============================================================================

export async function analyzeFile(file: File): Promise<FileAnalysisResult> {
    const formData = new FormData();
    formData.append('file', file);
    const authHeaders = await getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        headers: { ...authHeaders },
        body: formData,
    });

    if (!response.ok) {
        let details: unknown;
        try {
            details = await response.json();
        } catch {
            details = await response.text();
        }
        throw new ApiError(response.status, `Upload Error: ${response.statusText}`, details);
    }

    return response.json();
}

export async function analyzeText(
    textContent: string,
    query = ''
): Promise<FileAnalysisResult> {
    const formData = new FormData();
    formData.append('text_content', textContent);
    formData.append('query', query);
    const authHeaders = await getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        headers: { ...authHeaders },
        body: formData,
    });

    if (!response.ok) {
        let details: unknown;
        try {
            details = await response.json();
        } catch {
            details = await response.text();
        }
        throw new ApiError(response.status, `Analysis Error: ${response.statusText}`, details);
    }

    return response.json();
}

// ============================================================================
// Chat API
// ============================================================================

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    return withRetry(() =>
        apiFetch('/chat', {
            method: 'POST',
            body: JSON.stringify(request),
        })
    );
}

// ============================================================================
// Explain API
// ============================================================================

export type ExplanationComponent =
    // Cynefin Router
    | 'cynefin_domain'
    | 'cynefin_confidence'
    | 'cynefin_entropy'
    | 'cynefin_solver'
    // Causal Analysis
    | 'causal_effect'
    | 'causal_pvalue'
    | 'causal_ci'
    | 'causal_refutation'
    | 'causal_confounder'
    // Bayesian Panel
    | 'bayesian_posterior'
    | 'bayesian_epistemic'
    | 'bayesian_aleatoric'
    | 'bayesian_probe'
    | 'bayesian_info_gain'
    | 'bayesian_confidence'
    // Guardian Panel
    | 'guardian_policy'
    | 'guardian_policies'
    | 'guardian_verdict'
    | 'guardian_action'
    | 'guardian_risk'
    // DAG
    | 'dag_node'
    | 'dag_edge'
    | 'dag_path';

export async function explainComponent(
    component: ExplanationComponent,
    elementId?: string,
    context?: Record<string, unknown>,
    detailLevel: 'brief' | 'standard' | 'detailed' = 'standard'
): Promise<ExplanationResponse> {
    return withRetry(() =>
        apiFetch('/explain', {
            method: 'POST',
            body: JSON.stringify({
                component,
                element_id: elementId,
                context,
                detail_level: detailLevel,
            }),
        })
    );
}

export async function explainCynefinElement(
    element: 'domain' | 'confidence' | 'entropy' | 'solver',
    value?: string
): Promise<ExplanationResponse> {
    const params = value ? `?value=${encodeURIComponent(value)}` : '';
    return withRetry(() => apiFetch(`/explain/cynefin/${element}${params}`));
}

export async function explainCausalElement(
    element: 'effect' | 'pvalue' | 'ci' | 'refutation' | 'confounder',
    value?: string
): Promise<ExplanationResponse> {
    const params = value ? `?value=${encodeURIComponent(value)}` : '';
    return withRetry(() => apiFetch(`/explain/causal/${element}${params}`));
}

export async function explainBayesianElement(
    element: 'posterior' | 'epistemic' | 'aleatoric' | 'probe',
    value?: string
): Promise<ExplanationResponse> {
    const params = value ? `?value=${encodeURIComponent(value)}` : '';
    return withRetry(() => apiFetch(`/explain/bayesian/${element}${params}`));
}

export async function explainGuardianElement(
    element: 'policy' | 'verdict',
    policyName?: string
): Promise<ExplanationResponse> {
    const params = policyName ? `?policy_name=${encodeURIComponent(policyName)}` : '';
    return withRetry(() => apiFetch(`/explain/guardian/${element}${params}`));
}

// ============================================================================
// Developer API
// ============================================================================

export async function getDeveloperState(): Promise<DeveloperState> {
    return withRetry(() => apiFetch('/developer/state'));
}

export async function getDeveloperLogs(options?: {
    layer?: string;
    level?: string;
    limit?: number;
}): Promise<{ logs: LogEntry[] }> {
    const params = new URLSearchParams();
    if (options?.layer) params.append('layer', options.layer);
    if (options?.level) params.append('level', options.level);
    if (options?.limit) params.append('limit', options.limit.toString());

    const queryString = params.toString();
    return withRetry(() => apiFetch(`/developer/logs${queryString ? `?${queryString}` : ''}`));
}

// WebSocket for real-time log streaming
export function connectDeveloperWebSocket(
    onMessage: (log: LogEntry) => void,
    onError?: (error: Event) => void,
    onClose?: () => void
): WebSocket {
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws') + '/developer/ws';
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        try {
            const log = JSON.parse(event.data) as LogEntry;
            onMessage(log);
        } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
    };

    ws.onclose = () => {
        onClose?.();
    };

    // Set up ping interval to keep connection alive
    const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
        }
    }, 30000);

    // Clean up on close
    const originalClose = ws.close.bind(ws);
    ws.close = () => {
        clearInterval(pingInterval);
        originalClose();
    };

    return ws;
}

// ============================================================================
// Domains API
// ============================================================================

export async function listDomains(): Promise<{
    domains: Array<{
        name: string;
        description: string;
        route: string;
    }>;
}> {
    return withRetry(() => apiFetch('/domains'));
}

// ============================================================================
// Transparency API
// ============================================================================

export interface AgentInfo {
    agent_id: string;
    name: string;
    description: string;
    category: string;
    capabilities: string[];
    dependencies: string[];
    reliability_score: number;
    version: string;
}

export interface DataQualityAssessment {
    dataset_id: string;
    overall_score: number;
    completeness: number;
    consistency: number;
    uniqueness: number;
    validity: number;
    issues: string[];
    recommendations: string[];
}

// DeepEval quality scores for LLM output evaluation
export interface DeepEvalScores {
    relevancy_score: number;
    hallucination_risk: number;
    reasoning_depth: number;
    uix_compliance: number;
    task_completion: boolean;
    evaluated_at?: string;
}

export interface ReliabilityAssessment {
    overall_score: number;
    overall_level?: string;
    level: 'excellent' | 'good' | 'fair' | 'poor' | 'unreliable';
    factors?: {
        name: string;
        score: number;
        weight: number;
        status: string;
        explanation: string;
    }[];
    components: {
        name: string;
        score: number;
        weight: number;
        details: string;
    }[];
    suggestions: string[];
    improvement_suggestions?: string[];
    eu_ai_act_compliant: boolean;
    // DeepEval LLM quality scores (optional, populated when evaluation enabled)
    deepeval_scores?: DeepEvalScores | null;
}

export interface EUAIActReport {
    overall_compliant: boolean;
    risk_level: 'minimal' | 'limited' | 'high' | 'unacceptable';
    articles: {
        article_id: string;
        title: string;
        compliant: boolean;
        details: string;
        recommendations: string[];
    }[];
    transparency_score: number;
    traceability_score: number;
    human_oversight_score: number;
}

export interface RouterConfig {
    confidence_threshold: number;
    clear_threshold: number;
    complicated_threshold: number;
    complex_threshold: number;
    use_data_hints: boolean;
    use_pattern_matching: boolean;
}

export interface GuardianConfig {
    confidence_thresholds: Record<string, number>;
    financial_limits: Record<string, number>;
    risk_weights: Record<string, number>;
    user_financial_limit: number | null;
    policies_enabled: boolean;
}

export async function getAgents(): Promise<AgentInfo[]> {
    return withRetry(() => apiFetch('/transparency/agents'));
}

export async function assessDataQuality(datasetId: string): Promise<DataQualityAssessment> {
    return withRetry(() =>
        apiFetch('/transparency/data-quality', {
            method: 'POST',
            body: JSON.stringify({ dataset_id: datasetId }),
        })
    );
}

export async function assessReliability(request: {
    confidence: number;
    sample_size: number;
    method: string;
    refutation_pass_rate?: number;
    data_quality_score?: number;
}): Promise<ReliabilityAssessment> {
    return withRetry(() =>
        apiFetch('/transparency/reliability', {
            method: 'POST',
            body: JSON.stringify(request),
        })
    );
}

export async function getEUAIActCompliance(request: {
    workflow_id?: string;
    analysis_type: string;
    data_sources: string[];
    methods_used: string[];
}): Promise<EUAIActReport> {
    return withRetry(() =>
        apiFetch('/transparency/compliance', {
            method: 'POST',
            body: JSON.stringify(request),
        })
    );
}

export async function getRouterConfig(): Promise<RouterConfig> {
    return withRetry(() => apiFetch('/router/config'));
}

export async function updateRouterConfig(config: Partial<RouterConfig>): Promise<RouterConfig> {
    return withRetry(() =>
        apiFetch('/router/config', {
            method: 'PUT',
            body: JSON.stringify(config),
        })
    );
}

export async function getGuardianConfig(): Promise<GuardianConfig> {
    return withRetry(() => apiFetch('/guardian/config'));
}

export async function updateGuardianConfig(config: Partial<GuardianConfig>): Promise<GuardianConfig> {
    return withRetry(() =>
        apiFetch('/guardian/config', {
            method: 'PUT',
            body: JSON.stringify(config),
        })
    );
}

// ============================================================================
// Simulation API
// ============================================================================

export interface SimulationGenerator {
    name: string;
    description: string;
}

export interface ScenarioRealism {
    overall_score: number;
    level: 'excellent' | 'good' | 'fair' | 'poor' | 'synthetic';
    sample_adequacy: number;
    causal_validity: number;
    covariate_balance: number;
    effect_plausibility: number;
    issues: string[];
    recommendations: string[];
}

export async function listSimulationGenerators(): Promise<SimulationGenerator[]> {
    return withRetry(() => apiFetch('/simulations/generators'));
}

export async function generateSimulationData(request: {
    scenario_type: string;
    n_samples: number;
    seed?: number;
}): Promise<{
    scenario_type: string;
    n_samples: number;
    columns: string[];
    sample_data: Record<string, unknown>[];
}> {
    return withRetry(() =>
        apiFetch('/simulations/generate', {
            method: 'POST',
            body: JSON.stringify(request),
        })
    );
}

export async function assessScenarioRealism(request: {
    dataset_id: string;
    treatment_col: string;
    outcome_col: string;
    covariates?: string[];
}): Promise<ScenarioRealism> {
    return withRetry(() =>
        apiFetch('/simulations/assess-realism', {
            method: 'POST',
            body: JSON.stringify(request),
        })
    );
}

// ============================================================================
// Export default API object
// ============================================================================

const api = {
    // Health & Config
    checkHealth,
    getConfigStatus,
    validateConfig,
    updateConfig,

    // Scenarios
    listScenarios,
    getScenario,

    // Query
    submitQuery,
    submitQueryStream,

    // Datasets
    listDatasets,
    createDataset,
    previewDataset,

    // Analyze
    analyzeFile,
    analyzeText,

    // Chat
    sendChatMessage,

    // Explain
    explainComponent,
    explainCynefinElement,
    explainCausalElement,
    explainBayesianElement,
    explainGuardianElement,

    // Developer
    getDeveloperState,
    getDeveloperLogs,
    connectDeveloperWebSocket,

    // Domains
    listDomains,

    // Transparency
    getAgents,
    assessDataQuality,
    assessReliability,
    getEUAIActCompliance,
    getRouterConfig,
    updateRouterConfig,
    getGuardianConfig,
    updateGuardianConfig,

    // Simulation
    listSimulationGenerators,
    generateSimulationData,
    assessScenarioRealism,
};

// ============================================================================
// Visualization Config
// ============================================================================

export interface CynefinVizConfig {
    domain: string;
    primary_chart: string;
    secondary_charts: string[];
    color_scheme: string[];
    interaction_mode: string;
    detail_level: string;
    recommended_panels: string[];
}

export interface ContextualVizConfig {
    context: string;
    chart_type: string;
    color_scheme: string[];
    kpi_templates: Array<{ name: string; unit: string; trend: string; description?: string }>;
    recommended_panels: string[];
    title_template: string;
    insight_prompt: string;
}

export interface VizConfigResponse {
    context: ContextualVizConfig;
    domain: CynefinVizConfig;
}

export async function getVisualizationConfig(
    context: string = 'general',
    domain: string = 'disorder'
): Promise<VizConfigResponse> {
    const response = await fetch(
        `${API_BASE_URL}/api/visualization-config?context=${encodeURIComponent(context)}&domain=${encodeURIComponent(domain)}`
    );
    if (!response.ok) throw new ApiError(response.status, 'Failed to fetch visualization config');
    return response.json();
}

// ============================================================================
// Feedback API — Closed-Loop Learning
// ============================================================================

export interface FeedbackItem {
    type: 'issue' | 'improvement' | 'domain_override' | 'quality_rating';
    description: string;
    context: Record<string, unknown>;
    rating?: number;
    correct_domain?: string;
}

export interface FeedbackResponse {
    feedback_id: string;
    status: string;
    message: string;
    received_at: string;
}

export async function submitFeedback(item: FeedbackItem): Promise<FeedbackResponse> {
    const authHeaders = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(item),
    });
    if (!response.ok) throw new ApiError(response.status, 'Failed to submit feedback');
    return response.json();
}

export async function getFeedbackSummary(): Promise<Record<string, unknown>> {
    const authHeaders = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/feedback/summary`, {
        headers: { ...authHeaders },
    });
    if (!response.ok) throw new ApiError(response.status, 'Failed to fetch feedback summary');
    return response.json();
}

// ============================================================================
// Analysis History (cloud-backed, per-user)
// ============================================================================

export interface HistoryEntry {
    id: string;
    user_id: string;
    query: string;
    domain: string;
    confidence: number;
    result_json: string;
    created_at: string;
}

export async function saveHistory(entry: {
    query: string;
    domain: string;
    confidence: number;
    result_json: string;
}): Promise<HistoryEntry> {
    return apiFetch<HistoryEntry>('/history', {
        method: 'POST',
        body: JSON.stringify(entry),
    });
}

export async function listHistory(): Promise<{ items: HistoryEntry[] }> {
    return apiFetch<{ items: HistoryEntry[] }>('/history');
}

export async function deleteHistoryEntry(entryId: string): Promise<{ status: string }> {
    return apiFetch<{ status: string }>(`/history/${entryId}`, { method: 'DELETE' });
}

// ============================================================================
// Domain Action API
// ============================================================================

export async function submitDomainAction(
    action: string,
    context: Record<string, unknown>
): Promise<QueryResponse> {
    return withRetry(() =>
        apiFetch('/query', {
            method: 'POST',
            body: JSON.stringify({
                query: context.prompt || `Execute domain action: ${action}`,
                context: { ...context, action_type: action },
            }),
        })
    );
}

// ============================================================================
// CSL Policy API
// ============================================================================

export interface CSLStatus {
    enabled: boolean;
    engine: string;
    policy_count: number;
    rule_count: number;
    policies: string[];
}

export interface CSLPolicyDetail {
    name: string;
    version: string;
    description: string;
    rules: CSLRuleDetail[];
}

export interface CSLRuleDetail {
    name: string;
    policy_name: string;
    condition: Record<string, unknown>;
    constraint: Record<string, unknown>;
    message: string;
}

export interface CSLEvaluationResult {
    allow: boolean;
    rules_checked: number;
    rules_passed: number;
    rules_failed: number;
    violations: Array<{
        rule_name: string;
        policy_name: string;
        message: string;
    }>;
}

export async function getCSLStatus(): Promise<CSLStatus> {
    return withRetry(() => apiFetch('/csl/status'));
}

export async function getCSLPolicies(): Promise<CSLPolicyDetail[]> {
    return withRetry(() => apiFetch('/csl/policies'));
}

export async function reloadCSLPolicies(): Promise<{ status: string; message: string }> {
    return withRetry(() => apiFetch('/csl/reload', { method: 'POST' }));
}

export async function evaluateCSLPolicy(
    policyName: string,
    context: Record<string, unknown>
): Promise<CSLEvaluationResult> {
    return withRetry(() =>
        apiFetch('/csl/evaluate', {
            method: 'POST',
            body: JSON.stringify({ policy_name: policyName, context }),
        })
    );
}

export async function addCSLRule(
    policyName: string,
    naturalLanguageRule: string
): Promise<{ status: string; rule: CSLRuleDetail }> {
    return withRetry(() =>
        apiFetch(`/csl/policies/${encodeURIComponent(policyName)}/rules`, {
            method: 'POST',
            body: JSON.stringify({ natural_language: naturalLanguageRule }),
        })
    );
}

// ============================================================================
// Simulation Benchmarks API
// ============================================================================

export interface SimulationBenchmark {
    id: string;
    name: string;
    type: 'industry' | 'historical' | 'custom';
    value: number;
    description: string;
}

export async function getSimulationBenchmarks(
    scenario: string
): Promise<SimulationBenchmark[]> {
    return withRetry(() =>
        apiFetch(`/simulations/benchmarks/${encodeURIComponent(scenario)}`)
    );
}

// ============================================================================
// Executive Summary API
// ============================================================================

export interface ExecutiveSummary {
    key_finding: string;
    confidence_level: string;
    recommended_action: string;
    risk_assessment: string;
    plain_explanation: string;
    domain: string;
    generated_at: string;
}

export async function getExecutiveSummary(
    analysisContext: Record<string, unknown>
): Promise<ExecutiveSummary> {
    return withRetry(() =>
        apiFetch('/summary/executive', {
            method: 'POST',
            body: JSON.stringify(analysisContext),
        })
    );
}

// ============================================================================
// Governance API (Phase 16 — Orchestration Governance)
// ============================================================================

import type {
    GovernanceDomain,
    ContextTriple,
    FederatedPolicyInfo,
    PolicyConflict,
    CostBreakdown,
    ComplianceScore,
    GovernanceAuditEntry,
    GovernanceHealth,
    GovernanceBoard,
    BoardTemplate,
    PolicyExtractionResult,
    GovernanceSemanticGraph,
} from '../types/carf';

export async function getGovernanceDomains(): Promise<GovernanceDomain[]> {
    return withRetry(() => apiFetch('/governance/domains'));
}

export async function getTriples(sessionId?: string): Promise<ContextTriple[]> {
    const params = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
    return withRetry(() => apiFetch(`/governance/triples${params}`));
}

export async function getImpactGraph(domainId: string): Promise<Record<string, unknown>> {
    return withRetry(() => apiFetch(`/governance/triples/impact/${encodeURIComponent(domainId)}`));
}

export async function getFederatedPolicies(domainId?: string): Promise<FederatedPolicyInfo[]> {
    const params = domainId ? `?domain_id=${encodeURIComponent(domainId)}` : '';
    return withRetry(() => apiFetch(`/governance/policies${params}`));
}

export async function getConflicts(unresolvedOnly = true): Promise<PolicyConflict[]> {
    return withRetry(() => apiFetch(`/governance/conflicts?unresolved_only=${unresolvedOnly}`));
}

export async function resolveConflict(
    conflictId: string,
    resolution: string,
    resolvedBy = 'user'
): Promise<PolicyConflict> {
    return withRetry(() =>
        apiFetch(`/governance/conflicts/${encodeURIComponent(conflictId)}/resolve`, {
            method: 'POST',
            body: JSON.stringify({ resolution, resolved_by: resolvedBy }),
        })
    );
}

export async function getCostBreakdown(sessionId: string): Promise<CostBreakdown> {
    return withRetry(() => apiFetch(`/governance/cost/breakdown/${encodeURIComponent(sessionId)}`));
}

export async function getCostAggregate(): Promise<Record<string, unknown>> {
    return withRetry(() => apiFetch('/governance/cost/aggregate'));
}

export async function getCostROI(): Promise<Record<string, unknown>> {
    return withRetry(() => apiFetch('/governance/cost/roi'));
}

export async function getComplianceScore(framework: string): Promise<ComplianceScore> {
    return withRetry(() => apiFetch(`/governance/compliance/${encodeURIComponent(framework)}`));
}

export async function getGovernanceAudit(
    limit = 100,
    domainId?: string,
    eventType?: string
): Promise<GovernanceAuditEntry[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (domainId) params.append('domain_id', domainId);
    if (eventType) params.append('event_type', eventType);
    return withRetry(() => apiFetch(`/governance/audit?${params.toString()}`));
}

export async function getGovernanceHealth(): Promise<GovernanceHealth> {
    return withRetry(() => apiFetch('/governance/health'));
}

export async function getGovernanceSemanticGraph(
    options?: {
        boardId?: string;
        sessionId?: string;
        unresolvedOnly?: boolean;
        tripleLimit?: number;
    }
): Promise<GovernanceSemanticGraph> {
    const params = new URLSearchParams();
    if (options?.boardId) params.append('board_id', options.boardId);
    if (options?.sessionId) params.append('session_id', options.sessionId);
    if (typeof options?.unresolvedOnly === 'boolean') {
        params.append('unresolved_only', String(options.unresolvedOnly));
    }
    if (options?.tripleLimit != null) {
        params.append('triple_limit', String(options.tripleLimit));
    }
    const qs = params.toString();
    return withRetry(() => apiFetch(`/governance/semantic-graph${qs ? `?${qs}` : ''}`));
}

// ============================================================================
// Governance Board API (Phase 17 — Board Configurator)
// ============================================================================

export async function getGovernanceBoards(): Promise<GovernanceBoard[]> {
    return withRetry(() => apiFetch('/governance/boards'));
}

export async function createGovernanceBoard(board: {
    name: string;
    description?: string;
    domain_ids?: string[];
    policy_namespaces?: string[];
    compliance_configs?: Array<{ framework: string; enabled?: boolean; target_score?: number }>;
    members?: Array<{ name: string; email?: string; role?: string }>;
    tags?: string[];
    is_active?: boolean;
}): Promise<GovernanceBoard> {
    return withRetry(() =>
        apiFetch('/governance/boards', {
            method: 'POST',
            body: JSON.stringify(board),
        })
    );
}

export async function getBoardTemplates(): Promise<BoardTemplate[]> {
    return withRetry(() => apiFetch('/governance/boards/templates'));
}

export async function createBoardFromTemplate(
    templateId: string,
    name?: string
): Promise<GovernanceBoard> {
    return withRetry(() =>
        apiFetch('/governance/boards/from-template', {
            method: 'POST',
            body: JSON.stringify({ template_id: templateId, name }),
        })
    );
}

export async function getGovernanceBoard(boardId: string): Promise<GovernanceBoard> {
    return withRetry(() => apiFetch(`/governance/boards/${encodeURIComponent(boardId)}`));
}

export async function updateGovernanceBoard(
    boardId: string,
    updates: {
        name?: string;
        description?: string;
        domain_ids?: string[];
        policy_namespaces?: string[];
        tags?: string[];
        is_active?: boolean;
    }
): Promise<GovernanceBoard> {
    return withRetry(() =>
        apiFetch(`/governance/boards/${encodeURIComponent(boardId)}`, {
            method: 'PUT',
            body: JSON.stringify(updates),
        })
    );
}

export async function deleteGovernanceBoard(boardId: string): Promise<void> {
    await withRetry(() =>
        apiFetch(`/governance/boards/${encodeURIComponent(boardId)}`, {
            method: 'DELETE',
        }).catch(() => undefined) // 204 No Content
    );
}

export async function getBoardCompliance(boardId: string): Promise<ComplianceScore[]> {
    return withRetry(() =>
        apiFetch(`/governance/boards/${encodeURIComponent(boardId)}/compliance`)
    );
}

export async function exportGovernanceSpec(
    boardId: string,
    format: 'json_ld' | 'yaml' | 'csl'
): Promise<Record<string, unknown>> {
    return withRetry(() =>
        apiFetch('/governance/export', {
            method: 'POST',
            body: JSON.stringify({ board_id: boardId, format }),
        })
    );
}

export async function extractPoliciesFromText(
    text: string,
    sourceName?: string,
    targetDomain?: string
): Promise<PolicyExtractionResult> {
    return withRetry(() =>
        apiFetch('/governance/policies/extract', {
            method: 'POST',
            body: JSON.stringify({
                text,
                source_name: sourceName || 'pasted_text',
                target_domain: targetDomain,
            }),
        })
    );
}

export async function createGovernanceDomain(domain: {
    domain_id: string;
    display_name: string;
    description?: string;
    owner_email?: string;
    policy_namespace?: string;
    tags?: string[];
    color?: string;
}): Promise<GovernanceDomain> {
    return withRetry(() =>
        apiFetch('/governance/domains', {
            method: 'POST',
            body: JSON.stringify(domain),
        })
    );
}

export async function createFederatedPolicy(policy: {
    name: string;
    domain_id: string;
    namespace: string;
    description?: string;
    rules?: Array<Record<string, unknown>>;
    priority?: number;
    is_active?: boolean;
    tags?: string[];
}): Promise<FederatedPolicyInfo> {
    return withRetry(() =>
        apiFetch('/governance/policies', {
            method: 'POST',
            body: JSON.stringify(policy),
        })
    );
}

export async function updateFederatedPolicy(
    namespace: string,
    updates: {
        description?: string;
        priority?: number;
        is_active?: boolean;
        tags?: string[];
    }
): Promise<FederatedPolicyInfo> {
    return withRetry(() =>
        apiFetch(`/governance/policies/${namespace}`, {
            method: 'PUT',
            body: JSON.stringify(updates),
        })
    );
}

export async function deleteFederatedPolicy(namespace: string): Promise<void> {
    await withRetry(() =>
        apiFetch(`/governance/policies/${namespace}`, {
            method: 'DELETE',
        }).catch(() => undefined) // 204 No Content
    );
}

export async function seedGovernanceDemoData(
    templateId: string
): Promise<{ status: string; board_id: string; board_name: string }> {
    return withRetry(() =>
        apiFetch(`/governance/seed/${encodeURIComponent(templateId)}`, {
            method: 'POST',
        })
    );
}

// ============================================================================
// RAG API (Phase C — Retrieval-Augmented Generation)
// ============================================================================

export interface RAGStatus {
    backend: string;
    chunks: number;
    domains_indexed: string[];
    lightrag_available: boolean;
}

export interface RAGQueryResult {
    query: string;
    chunks: Array<{
        content: string;
        source: string;
        domain_id: string | null;
        similarity: number;
    }>;
    context_text: string;
    total_chunks: number;
}

export async function getRAGStatus(): Promise<RAGStatus> {
    return withRetry(() => apiFetch('/governance/rag/status'));
}

export async function ragIngestPolicies(): Promise<{ status: string; chunks: number }> {
    return withRetry(() =>
        apiFetch('/governance/rag/ingest-policies', { method: 'POST' })
    );
}

export async function ragQuery(
    query: string,
    options?: { domain_id?: string; top_k?: number }
): Promise<RAGQueryResult> {
    return withRetry(() =>
        apiFetch('/governance/rag/query', {
            method: 'POST',
            body: JSON.stringify({
                query,
                domain_id: options?.domain_id,
                top_k: options?.top_k ?? 5,
            }),
        })
    );
}

export async function ragIngestText(
    text: string,
    sourceName?: string,
    targetDomain?: string
): Promise<{ status: string; source: string; chunks: number }> {
    return withRetry(() =>
        apiFetch('/governance/rag/ingest-text', {
            method: 'POST',
            body: JSON.stringify({
                text,
                source_name: sourceName || 'manual_input',
                target_domain: targetDomain,
            }),
        })
    );
}

// ============================================================================
// Document Upload API (Phase C — Multiformat Document Processing)
// ============================================================================

export interface DocumentUploadResult {
    status: string;
    filename: string;
    file_type?: string;
    text_length?: number;
    chunks_ingested?: number;
    error?: string;
}

export interface DocumentProcessorStatus {
    supported_types: string[];
    rag_anything_available: boolean;
}

export async function uploadGovernanceDocument(
    file: File,
    domainId?: string,
    sourceName?: string
): Promise<DocumentUploadResult> {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams();
    if (domainId) params.append('domain_id', domainId);
    if (sourceName) params.append('source_name', sourceName);

    const qs = params.toString();
    const url = `${API_BASE_URL}/governance/documents/upload-file${qs ? `?${qs}` : ''}`;

    const response = await fetch(url, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        let details: unknown;
        try {
            details = await response.json();
        } catch {
            details = await response.text();
        }
        throw new ApiError(response.status, `Upload Error: ${response.statusText}`, details);
    }

    return response.json();
}

export async function getDocumentProcessorStatus(): Promise<DocumentProcessorStatus> {
    return withRetry(() => apiFetch('/governance/documents/status'));
}

// ============================================================================
// Agent Memory API (Phase C — Persistent Cross-Session Memory)
// ============================================================================

export interface MemoryStatus {
    backend: string;
    entries: number;
    patterns: Record<string, {
        count: number;
        avg_confidence: number;
        methods: Record<string, number>;
        verdicts: Record<string, number>;
    }>;
}

export interface MemoryRecallResult {
    entry: {
        query: string;
        domain: string;
        domain_confidence: number;
        response_summary: string;
        causal_effect: number | null;
        bayesian_posterior: number | null;
        guardian_verdict: string | null;
        quality_score: number | null;
        session_id: string;
        triggered_method: string;
        timestamp: string;
    };
    similarity: number;
}

export async function getMemoryStatus(): Promise<MemoryStatus> {
    return withRetry(() => apiFetch('/governance/memory/status'));
}

export async function compactMemory(): Promise<{ status: string; entries: number }> {
    return withRetry(() =>
        apiFetch('/governance/memory/compact', { method: 'POST' })
    );
}

export async function recallMemory(
    query: string,
    topK = 5
): Promise<MemoryRecallResult[]> {
    return withRetry(() =>
        apiFetch('/governance/memory/recall', {
            method: 'POST',
            body: JSON.stringify({ query, top_k: topK }),
        })
    );
}

// =============================================================================
// Phase 17: World Model, Counterfactual, Neurosymbolic Endpoints
// =============================================================================

export async function runCounterfactual(request: {
    query: string;
    context?: Record<string, unknown>;
    dataset_id?: string;
}): Promise<{
    factual_outcome: string;
    counterfactual_outcome: string;
    causal_attribution: Array<Record<string, unknown>>;
    confidence: number;
    narrative: string;
    reasoning_steps: string[];
}> {
    return api(`${API_BASE_URL}/world-model/counterfactual`, {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

export async function compareCounterfactualScenarios(request: {
    base_query: string;
    alternative_interventions: Record<string, number>[];
    outcome_variable: string;
    context?: Record<string, unknown>;
}): Promise<{
    scenarios: Array<Record<string, unknown>>;
    best_scenario_index: number;
    ranking_rationale: string;
    outcome_range: [number, number];
}> {
    return api(`${API_BASE_URL}/world-model/counterfactual/compare`, {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

export async function runCausalAttribution(request: {
    outcome_description: string;
    context?: Record<string, unknown>;
    dataset_id?: string;
}): Promise<{
    outcome: string;
    attributions: Array<Record<string, unknown>>;
    but_for_tests: Array<Record<string, unknown>>;
    narrative: string;
}> {
    return api(`${API_BASE_URL}/world-model/counterfactual/attribute`, {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

export async function simulateWorldModel(request: {
    query: string;
    initial_conditions?: Record<string, number>;
    interventions?: Record<string, number>;
    steps?: number;
    dataset_id?: string;
    context?: Record<string, unknown>;
}): Promise<{
    trajectory: Record<string, number>[];
    variables: string[];
    interventions_applied: Record<string, number>;
    model_confidence: number;
    interpretation: string;
}> {
    return api(`${API_BASE_URL}/world-model/simulate`, {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

export async function runNeurosymbolicReasoning(request: {
    query: string;
    context?: Record<string, unknown>;
    use_knowledge_graph?: boolean;
    max_iterations?: number;
}): Promise<{
    conclusion: string;
    derived_facts: Array<Record<string, unknown>>;
    rule_chain: string[];
    shortcut_warnings: string[];
    iterations: number;
    confidence: number;
    symbolic_grounding: Array<Record<string, unknown>>;
}> {
    return api(`${API_BASE_URL}/world-model/neurosymbolic/reason`, {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

export async function validateReasoning(request: {
    claim: string;
    evidence?: string[];
    context?: Record<string, unknown>;
}): Promise<{
    claim: string;
    is_valid: boolean;
    violations: string[];
    shortcut_warnings: string[];
    supporting_rules: string[];
    confidence: number;
}> {
    const params = new URLSearchParams({ claim: request.claim });
    return api(`${API_BASE_URL}/world-model/neurosymbolic/validate?${params}`, {
        method: 'POST',
        body: JSON.stringify({
            evidence: request.evidence,
            context: request.context,
        }),
    });
}

export async function runDeepAnalysis(request: {
    query: string;
    context?: Record<string, unknown>;
    include_counterfactual?: boolean;
    include_neurosymbolic?: boolean;
    include_simulation?: boolean;
}): Promise<Record<string, unknown>> {
    const params = new URLSearchParams({ query: request.query });
    if (request.include_counterfactual !== undefined)
        params.set('include_counterfactual', String(request.include_counterfactual));
    if (request.include_neurosymbolic !== undefined)
        params.set('include_neurosymbolic', String(request.include_neurosymbolic));
    if (request.include_simulation !== undefined)
        params.set('include_simulation', String(request.include_simulation));

    return api(`${API_BASE_URL}/world-model/analyze-deep?${params}`, {
        method: 'POST',
        body: JSON.stringify(request.context || {}),
    });
}

// ============================================================================
// Phase 18: Monitoring API
// ============================================================================

export async function getMonitoringDriftStatus(): Promise<import('../types/carf').DriftStatus> {
    return withRetry(() => apiFetch('/monitoring/drift'));
}

export async function getMonitoringDriftHistory(limit = 20): Promise<{ snapshots: import('../types/carf').DriftSnapshot[] }> {
    return withRetry(() => apiFetch(`/monitoring/drift/history?limit=${limit}`));
}

export async function resetMonitoringDriftBaseline(): Promise<{ status: string }> {
    return withRetry(() => apiFetch('/monitoring/drift/reset', { method: 'POST' }));
}

export async function getMonitoringBiasAudit(): Promise<import('../types/carf').BiasReport> {
    return withRetry(() => apiFetch('/monitoring/bias-audit'));
}

export async function getMonitoringConvergence(): Promise<import('../types/carf').ConvergenceStatus> {
    return withRetry(() => apiFetch('/monitoring/convergence'));
}

export async function getMonitoringStatus(): Promise<import('../types/carf').MonitoringStatus> {
    return withRetry(() => apiFetch('/monitoring/status'));
}

export default api;
