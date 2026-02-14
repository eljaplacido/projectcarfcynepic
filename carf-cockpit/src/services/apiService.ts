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

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
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
            const response = await fetch(`${API_BASE_URL}/query/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
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

    const response = await fetch(`${API_BASE_URL}/analyze`, {
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

export async function analyzeText(
    textContent: string,
    query = ''
): Promise<FileAnalysisResult> {
    const formData = new FormData();
    formData.append('text_content', textContent);
    formData.append('query', query);

    const response = await fetch(`${API_BASE_URL}/analyze`, {
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

export default api;
