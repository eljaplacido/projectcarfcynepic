import React, { useState, useEffect, useCallback } from 'react';
import QueryInput from './QueryInput';
import CynefinRouter from './CynefinRouter';
import CausalDAG from './CausalDAG';
import CausalAnalysisCard from './CausalAnalysisCard';
import BayesianPanel from './BayesianPanel';
import GuardianPanel from './GuardianPanel';
import ExecutionTrace from './ExecutionTrace';
import ConversationalResponse from './ConversationalResponse';
import OnboardingOverlay from './OnboardingOverlay';
import IntelligentChatTab from './IntelligentChatTab';
import WalkthroughManager from './WalkthroughManager';
import DataOnboardingWizard from './DataOnboardingWizard';
import MethodologyModal from './MethodologyModal';
import AnalysisHistoryPanel, { useAnalysisHistory } from './AnalysisHistoryPanel';
import ConversationalQueryFlow from './ConversationalQueryFlow';
import FileAnalysisModal from './FileAnalysisModal';
import DeveloperView from './DeveloperView';
import SimulationArena from './SimulationArena';
import SettingsModal from './SettingsModal';
import DomainVisualization from './DomainVisualization';
import ExecutiveKPIPanel from './ExecutiveKPIPanel';
import InterventionSimulator from './InterventionSimulator';
import SensitivityPlot from './SensitivityPlot';
import PromptGuidancePanel from './PromptGuidancePanel';
import EscalationModal from './EscalationModal';
import TransparencyPanel from './TransparencyPanel';
import { QuickThemeToggle } from '../ui/ThemeToggle';
import type { Suggestion } from './PromptGuidancePanel';
import { useQuery, useScenarios, useConfigStatus } from '../../hooks/useCarfApi';
import api from '../../services/apiService';
import type { ChatMessage, ViewMode, AnalysisSession, SlashCommand, QueryResponse, DAGNode, DAGEdge } from '../../types/carf';
import type { FileAnalysisResult } from '../../services/apiService';
import type { HighlightTarget } from '../../config/questioningFlow';

// Mapping from HighlightTarget to DOM element IDs/selectors
const HIGHLIGHT_TARGET_MAP: Record<HighlightTarget, string> = {
    'cynefin-panel': 'cynefin-panel',
    'causal-panel': 'causal-results',
    'bayesian-panel': 'bayesian-panel',
    'guardian-panel': 'guardian-panel',
    'dag-viewer': 'dag-viewer',
    'domain-badge': 'domain-badge',
    'confidence-indicator': 'confidence-indicator',
    'effect-estimate': 'effect-estimate',
    'uncertainty-chart': 'uncertainty-chart',
    'policy-list': 'policy-list',
};

// Helper function to generate DAG nodes and edges from causal result
function generateDAGFromCausalResult(causalResult: QueryResponse['causalResult'] | undefined): { nodes: DAGNode[]; edges: DAGEdge[] } {
    if (!causalResult) {
        return { nodes: [], edges: [] };
    }

    const nodes: DAGNode[] = [];
    const edges: DAGEdge[] = [];

    // Treatment node (intervention)
    const treatmentId = 'treatment';
    nodes.push({
        id: treatmentId,
        label: causalResult.treatment || 'Treatment',
        type: 'intervention',
        position: { x: 100, y: 150 },
        value: 1,
        unit: '',
    });

    // Outcome node
    const outcomeId = 'outcome';
    nodes.push({
        id: outcomeId,
        label: causalResult.outcome || 'Outcome',
        type: 'outcome',
        position: { x: 400, y: 150 },
        value: causalResult.effect,
        unit: causalResult.unit || 'units',
    });

    // Main causal edge
    edges.push({
        id: 'treatment-outcome',
        source: treatmentId,
        target: outcomeId,
        effectSize: causalResult.effect,
        pValue: causalResult.pValue ?? 0.05,
        validated: (causalResult.refutationsPassed ?? 0) > 0,
    });

    // Add confounder nodes if available
    const confounders = causalResult.confoundersControlled || [];
    confounders.forEach((confounder, idx) => {
        const confounderId = `confounder-${idx}`;
        const yOffset = 50 + idx * 80;

        nodes.push({
            id: confounderId,
            label: typeof confounder === 'string' ? confounder : `Confounder ${idx + 1}`,
            type: 'confounder',
            position: { x: 250, y: yOffset },
        });

        // Confounder affects treatment
        edges.push({
            id: `${confounderId}-treatment`,
            source: confounderId,
            target: treatmentId,
            effectSize: 0.3, // Default effect size for visualization
            pValue: 0.01, // Confounders assumed significant
            validated: true,
        });

        // Confounder affects outcome
        edges.push({
            id: `${confounderId}-outcome`,
            source: confounderId,
            target: outcomeId,
            effectSize: 0.2, // Default effect size for visualization
            pValue: 0.01, // Confounders assumed significant
            validated: true,
        });
    });

    return { nodes, edges };
}

const DashboardLayout: React.FC = () => {
    // Core state
    const [selectedScenario, setSelectedScenario] = useState<string>('');
    const [sessionId] = useState<string>(() =>
        `session_${Date.now()}_${Math.random().toString(36).substring(7)}`
    );
    const [isProcessing, setIsProcessing] = useState<boolean>(false);
    const [processingMessage, setProcessingMessage] = useState<string>('');
    const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null);
    const [apiError, setApiError] = useState<string | null>(null);
    const [, setQueryStartTime] = useState<number>(0);

    // Phase 7: View mode state
    const [viewMode, setViewMode] = useState<ViewMode>('analyst');

    // Phase 7: Analysis history
    const { history, saveAnalysis, deleteAnalysis, clearHistory } = useAnalysisHistory();
    const [showHistoryPanel, setShowHistoryPanel] = useState<boolean>(false);

    // Phase 7: Query flow mode
    const [useConversationalFlow, setUseConversationalFlow] = useState<boolean>(true);

    // UI state for new components - check localStorage for first visit
    const [showOnboarding, setShowOnboarding] = useState<boolean>(() =>
        !localStorage.getItem('carf-visited')
    );
    const [showWalkthrough, setShowWalkthrough] = useState<boolean>(false);
    const [showDataWizard, setShowDataWizard] = useState<boolean>(false);
    const [showMethodologyModal, setShowMethodologyModal] = useState<boolean>(false);
    const [methodologyType, setMethodologyType] = useState<'causal' | 'bayesian' | 'guardian'>('causal');
    const [showFileAnalysisModal, setShowFileAnalysisModal] = useState<boolean>(false);
    const [fileAnalysisResult, setFileAnalysisResult] = useState<FileAnalysisResult | null>(null);
    const [comparisonSessions, setComparisonSessions] = useState<[AnalysisSession, AnalysisSession] | null>(null);
    const [showSettingsModal, setShowSettingsModal] = useState<boolean>(false);
    const [showEscalationModal, setShowEscalationModal] = useState<boolean>(false);
    const [pendingEscalationsCount, setPendingEscalationsCount] = useState<number>(0);

    // Fetch pending escalations count periodically
    useEffect(() => {
        const fetchEscalationCount = async () => {
            try {
                const response = await fetch('http://localhost:8000/escalations?pending_only=true');
                if (response.ok) {
                    const data = await response.json();
                    setPendingEscalationsCount(data.length);
                }
            } catch {
                // Silently fail - backend might not be running
            }
        };
        fetchEscalationCount();
        const interval = setInterval(fetchEscalationCount, 30000); // Check every 30s
        return () => clearInterval(interval);
    }, []);

    // API hooks
    const { isDemoMode } = useConfigStatus();
    const { scenarios: apiScenarios } = useScenarios();
    const { submitQuery: apiSubmitQuery, loading: apiLoading, progress: apiProgress } = useQuery();

    // Chat state
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
    const [currentQuery, setCurrentQuery] = useState<string>('');

    // Socratic mode highlighting state
    const [highlightedPanels, setHighlightedPanels] = useState<HighlightTarget[]>([]);

    // Dynamic suggested queries based on scenario
    const [dynamicSuggestedQueries, setDynamicSuggestedQueries] = useState<string[]>([]);
    const [scenarioContext, setScenarioContext] = useState<Record<string, unknown> | null>(null);

    // Phase 8: Agentic Guidance
    const [aiSuggestions, setAiSuggestions] = useState<Suggestion[]>([]);

    // Track columns from file analysis or scenario for AI suggestions
    const [dataColumns, setDataColumns] = useState<string[]>([]);

    // Update columns when file analysis completes or scenario changes
    useEffect(() => {
        if (fileAnalysisResult?.columns) {
            setDataColumns(fileAnalysisResult.columns.map((c: { name?: string } | string) =>
                typeof c === 'string' ? c : c.name || ''
            ));
        } else if (scenarioContext && 'columns' in scenarioContext && Array.isArray(scenarioContext.columns)) {
            setDataColumns(scenarioContext.columns as string[]);
        }
    }, [fileAnalysisResult, scenarioContext]);

    useEffect(() => {
        const fetchSuggestions = async () => {
            try {
                // Ensure we send a valid payload even for initial empty state
                const contextPayload = {
                    current_query: currentQuery || '',
                    last_domain: queryResponse?.domain || null,
                    last_confidence: queryResponse?.domainConfidence || null,
                    available_columns: dataColumns
                };

                // Use the correct backend URL
                const response = await fetch('http://localhost:8000/agent/suggest-improvements', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(contextPayload)
                });

                if (response.ok) {
                    const data = await response.json();
                    // Filter to only show suggestions with action_payload
                    const actionable = data.filter((s: Suggestion) => s.action_payload);
                    setAiSuggestions(actionable.length > 0 ? actionable : data);
                } else {
                    console.warn("AI Suggestions endpoint returned status:", response.status);
                    // Fallback for demo if API fails - include action_payload so they're usable
                    if (!currentQuery) {
                        const treatment = dataColumns.find(c => c.toLowerCase().includes('treatment') || c.toLowerCase().includes('program'));
                        const outcome = dataColumns.find(c => c.toLowerCase().includes('outcome') || c.toLowerCase().includes('emission') || c.toLowerCase().includes('cost'));
                        setAiSuggestions([
                            {
                                id: 'fallback_1',
                                type: 'prompt_refinement',
                                text: `Analyze causal effect of ${treatment || 'treatment'} on ${outcome || 'outcome'}`,
                                action_payload: `What is the causal effect of ${treatment || 'treatment'} on ${outcome || 'outcome'}?`
                            },
                            {
                                id: 'fallback_2',
                                type: 'next_step',
                                text: 'Explore data distributions',
                                action_payload: 'Show me the distribution of key variables in the dataset'
                            }
                        ]);
                    } else {
                        setAiSuggestions([]);
                    }
                }
            } catch (e) {
                console.error("Failed to fetch suggestions:", e);
                // Fallback for demo if network fails - with action_payload
                if (!currentQuery) {
                    setAiSuggestions([
                        {
                            id: 'fallback_1',
                            type: 'prompt_refinement',
                            text: 'Analyze causal relationships in the data',
                            action_payload: 'What are the key causal relationships in this dataset?'
                        }
                    ]);
                }
            }
        };
        fetchSuggestions();
    }, [queryResponse, selectedScenario, currentQuery, dataColumns]);

    const handleApplySuggestion = (suggestion: Suggestion) => {
        if (suggestion.action_payload) {
            handleQuerySubmit(suggestion.action_payload);
        }
    };

    const handleScenarioChange = useCallback(async (scenarioId: string) => {
        setSelectedScenario(scenarioId);
        setQueryResponse(null);
        setApiError(null);
        setShowOnboarding(false);
        setFileAnalysisResult(null);
        localStorage.setItem('carf-visited', 'true');

        // Clear chat messages for new scenario
        setChatMessages([]);

        if (!scenarioId) return;

        try {
            const scenarioDetail = await api.getScenario(scenarioId);
            if (scenarioDetail.scenario) {
                if (scenarioDetail.scenario.suggested_queries) {
                    setDynamicSuggestedQueries(scenarioDetail.scenario.suggested_queries);
                    setCurrentQuery(scenarioDetail.scenario.suggested_queries[0] || '');
                }
                setScenarioContext(scenarioDetail.payload || null);

                const welcomeMessage: ChatMessage = {
                    id: `msg_${Date.now()}_system`,
                    role: 'system',
                    content: `Switched to "${scenarioDetail.scenario.name}" scenario. ${scenarioDetail.scenario.description || ''}\n\nTry one of the suggested queries or ask your own question.`,
                    timestamp: new Date(),
                };
                setChatMessages([welcomeMessage]);
            }
        } catch (error) {
            console.error('Failed to fetch scenario from API:', error);
            setApiError('Backend unavailable. Please ensure the API server is running.');
            setDynamicSuggestedQueries([]);
            setScenarioContext(null);

            // Show error as system message
            const errorMessage: ChatMessage = {
                id: `msg_${Date.now()}_system`,
                role: 'system',
                content: 'Could not load scenario from backend. Please verify the API server is running at the configured URL.',
                timestamp: new Date(),
            };
            setChatMessages([errorMessage]);
        }
    }, []);

    const handleQuerySubmit = useCallback(async (query: string, context?: Record<string, unknown>) => {
        console.log('Query submitted:', query);
        setIsProcessing(true);
        setCurrentQuery(query);
        const startTime = Date.now();
        setQueryStartTime(startTime);

        // Add user message to chat
        const userMessage: ChatMessage = {
            id: `msg_${Date.now()}_user`,
            role: 'user',
            content: query,
            timestamp: new Date(),
        };
        setChatMessages(prev => [...prev, userMessage]);

        try {
            // Try API call first
            const apiResponse = await apiSubmitQuery({
                query,
                context: {
                    ...(scenarioContext || {}),
                    ...(fileAnalysisResult ? { file_analysis: fileAnalysisResult } : {}),
                    ...(context || {}),
                    scenario_id: selectedScenario || undefined,
                },
            });

            if (apiResponse) {
                const duration = Date.now() - startTime;

                // Convert API response to frontend format
                // Normalize domain to lowercase (Python enum uses 'Complicated', TS type expects 'complicated')
                const formattedResponse: QueryResponse = {
                    sessionId: apiResponse.sessionId || `session_${Date.now()}`,
                    domain: (apiResponse.domain?.toLowerCase() || 'disorder') as QueryResponse['domain'],
                    domainConfidence: apiResponse.domainConfidence,
                    domainEntropy: apiResponse.domainEntropy || 0,
                    guardianVerdict: apiResponse.guardianVerdict,
                    response: apiResponse.response,
                    requiresHuman: apiResponse.requiresHuman,
                    reasoningChain: apiResponse.reasoningChain || [],
                    causalResult: apiResponse.causalResult ? {
                        effect: apiResponse.causalResult.effect,
                        unit: apiResponse.causalResult.unit || 'units',
                        pValue: apiResponse.causalResult.pValue ?? null,
                        confidenceInterval: apiResponse.causalResult.confidenceInterval || [0, 0],
                        description: apiResponse.causalResult.description || '',
                        refutationsPassed: apiResponse.causalResult.refutationsPassed ?? 0,
                        refutationsTotal: apiResponse.causalResult.refutationsTotal ?? 0,
                        refutationDetails: [],
                        confoundersControlled: [],
                        evidenceBase: '',
                        metaAnalysis: false,
                        studies: 1,
                        treatment: apiResponse.causalResult.treatment || '',
                        outcome: apiResponse.causalResult.outcome || '',
                    } : null,
                    bayesianResult: apiResponse.bayesianResult ? {
                        variable: apiResponse.bayesianResult.variable || '',
                        priorMean: 0,
                        priorStd: 0,
                        posteriorMean: apiResponse.bayesianResult.posteriorMean ?? 0,
                        posteriorStd: 0,
                        confidenceLevel: (apiResponse.bayesianResult.confidenceLevel ?? 'medium') as 'high' | 'medium' | 'low',
                        interpretation: '',
                        epistemicUncertainty: apiResponse.bayesianResult.epistemicUncertainty ?? 0,
                        aleatoricUncertainty: apiResponse.bayesianResult.aleatoricUncertainty ?? 0,
                        totalUncertainty: (apiResponse.bayesianResult.epistemicUncertainty ?? 0) + (apiResponse.bayesianResult.aleatoricUncertainty ?? 0),
                        recommendedProbe: apiResponse.bayesianResult.recommendedProbe,
                    } : null,
                    guardianResult: apiResponse.guardianResult ? {
                        overallStatus: apiResponse.guardianResult.overallStatus || 'pending',
                        proposedAction: apiResponse.guardianResult.proposedAction || { type: '', target: '', amount: 0, unit: '', expectedEffect: '' },
                        policies: apiResponse.guardianResult.policies || [],
                        requiresHumanApproval: apiResponse.guardianResult.requiresHumanApproval ?? false,
                    } : null,
                    error: apiResponse.error,
                    // Router transparency fields (Phase 11)
                    routerReasoning: apiResponse.routerReasoning,
                    routerKeyIndicators: apiResponse.routerKeyIndicators || [],
                    domainScores: apiResponse.domainScores || {},
                    triggeredMethod: apiResponse.triggeredMethod,
                };

                setQueryResponse(formattedResponse as QueryResponse);
                setIsProcessing(false);
                setProcessingMessage('');

                // Save to analysis history
                const analysisSession: AnalysisSession = {
                    id: `analysis_${Date.now()}`,
                    timestamp: new Date().toISOString(),
                    query: query,
                    scenarioId: selectedScenario || undefined,
                    domain: formattedResponse.domain,
                    confidence: formattedResponse.domainConfidence,
                    result: formattedResponse,
                    duration: duration,
                };
                saveAnalysis(analysisSession);

                // Add assistant message to chat
                const assistantMessage: ChatMessage = {
                    id: `msg_${Date.now()}_assistant`,
                    role: 'assistant',
                    content: formattedResponse.response || 'Analysis complete. The causal effect has been estimated.',
                    timestamp: new Date(),
                    confidence: formattedResponse.domainConfidence >= 0.8 ? 'high' : formattedResponse.domainConfidence >= 0.5 ? 'medium' : 'low',
                    linkedPanel: 'causal-results',
                };
                setChatMessages(prev => [...prev, assistantMessage]);
                return;
            }
        } catch (error) {
            console.error('API call failed:', error);
            setIsProcessing(false);
            setProcessingMessage('');
            setApiError('Analysis failed. Please check that the backend API is running.');

            const errorMessage: ChatMessage = {
                id: `msg_${Date.now()}_system`,
                role: 'system',
                content: `Analysis request failed: ${error instanceof Error ? error.message : 'Backend unavailable'}. Please ensure the API server is running.`,
                timestamp: new Date(),
            };
            setChatMessages(prev => [...prev, errorMessage]);
        }
    }, [selectedScenario, saveAnalysis, apiSubmitQuery, fileAnalysisResult, scenarioContext]);

    // Phase 7: Handle intelligent chat messages with slash commands
    const handleIntelligentChatMessage = useCallback((
        message: string,
        isSlashCommand?: boolean,
        commandType?: SlashCommand
    ) => {
        const chatMessage: ChatMessage = {
            id: `msg_${Date.now()}_${isSlashCommand ? 'system' : 'assistant'}`,
            role: isSlashCommand ? 'system' : 'assistant',
            content: message,
            timestamp: new Date(),
            isSlashCommand,
            commandType,
        };
        setChatMessages(prev => [...prev, chatMessage]);
    }, []);

    // Phase 7: Handle viewing a session from history
    const handleViewSession = useCallback((session: AnalysisSession) => {
        setQueryResponse(session.result);
        setShowHistoryPanel(false);
    }, []);

    const handleCompareSessions = useCallback((sessionA: AnalysisSession, sessionB: AnalysisSession) => {
        setComparisonSessions([sessionA, sessionB]);
        setShowHistoryPanel(false);
    }, []);

    // Phase 7: Handle rerunning a simulation with modified parameters
    const handleRerunWithChanges = useCallback((session: AnalysisSession, changes: Record<string, number>) => {
        console.log('Rerunning with changes:', changes);
        setComparisonSessions(null);

        // Trigger new analysis with method overrides
        handleQuerySubmit(session.query, {
            run_type: 'simulation_rerun',
            parent_session_id: session.result.sessionId,
            method_overrides: changes,
            scenario_id: session.scenarioId,
        });
    }, [handleQuerySubmit]);

    // Handle domain-specific action buttons (Deep Analysis, Sensitivity Check, Run Probe, Explore Scenarios)
    const handleDomainAction = useCallback((action: string) => {
        const domain = queryResponse?.domain || 'unknown';
        const currentQuery = queryResponse?.response || '';

        switch (action) {
            case 'deep_analysis': {
                setProcessingMessage('Running deep causal analysis with alternative estimators...');
                const prompt = `Perform a deeper causal analysis of: "${currentQuery}". Focus on identifying additional confounders, testing alternative causal pathways, and providing sensitivity analysis of the treatment effect estimate. Include heterogeneous treatment effects across subgroups.`;
                handleQuerySubmit(prompt, { run_type: 'deep_analysis', parent_domain: domain });
                break;
            }
            case 'sensitivity_check': {
                setProcessingMessage('Running sensitivity and refutation checks...');
                const prompt = `Run sensitivity and refutation checks for the causal analysis of: "${currentQuery}". Test with placebo treatments, random common causes, and data subset validation. Report which assumptions are most fragile.`;
                handleQuerySubmit(prompt, { run_type: 'sensitivity_check', parent_domain: domain });
                break;
            }
            case 'run_probe': {
                const prompt = `Design and evaluate safe-to-fail probes for: "${currentQuery}". This is a Complex domain scenario - suggest small experiments that could reduce uncertainty and identify which variables most influence the outcome.`;
                handleQuerySubmit(prompt, { run_type: 'probe_design', parent_domain: domain });
                break;
            }
            case 'explore_scenarios': {
                // Open simulation arena with current analysis if history available
                if (history.length >= 2) {
                    setComparisonSessions([history[0], history[1]]);
                } else {
                    const prompt = `Generate scenario comparisons for: "${currentQuery}". Compare optimistic, baseline, and pessimistic scenarios with different treatment intensities. Show how outcomes vary under each scenario.`;
                    handleQuerySubmit(prompt, { run_type: 'scenario_exploration', parent_domain: domain });
                }
                break;
            }
            case 'apply': {
                const prompt = `Apply established best practices for: "${currentQuery}". This is a Clear domain problem - retrieve and format the standard operating procedure or guideline.`;
                handleQuerySubmit(prompt, { run_type: 'best_practice', parent_domain: domain });
                break;
            }
            case 'halt':
            case 'escalate': {
                setShowEscalationModal(true);
                break;
            }
            case 'fallback': {
                const prompt = `Re-analyze "${currentQuery}" using a more conservative approach. Reduce complexity assumptions and provide a simplified assessment with wider confidence intervals.`;
                handleQuerySubmit(prompt, { run_type: 'fallback_analysis', parent_domain: domain });
                break;
            }
            case 'resubmit': {
                if (currentQuery) {
                    handleQuerySubmit(currentQuery);
                }
                break;
            }
            default:
                console.log('Unhandled domain action:', action);
        }
    }, [queryResponse, handleQuerySubmit, history, setComparisonSessions, setShowEscalationModal]);

    // Phase 7: Handle rerunning a session from history
    const handleRerunSession = useCallback((session: AnalysisSession) => {
        setShowHistoryPanel(false);
        handleQuerySubmit(session.query);
    }, [handleQuerySubmit]);

    const handleFollowUpQuestion = (question: string) => {
        setCurrentQuery(question);
        handleQuerySubmit(question);
    };

    const handleViewMethodology = (type: 'causal' | 'bayesian' | 'guardian') => {
        setMethodologyType(type);
        setShowMethodologyModal(true);
    };

    const handleLinkClick = (panelId: string) => {
        // Scroll to the relevant panel
        const element = document.getElementById(panelId);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            element.classList.add('tour-highlight');
            setTimeout(() => element.classList.remove('tour-highlight'), 2000);
        }
    };

    // Handle Socratic mode panel highlighting
    const handleHighlightPanels = useCallback((targets: HighlightTarget[]) => {
        // Remove previous highlights
        highlightedPanels.forEach(target => {
            const elementId = HIGHLIGHT_TARGET_MAP[target];
            const element = document.getElementById(elementId);
            if (element) {
                element.classList.remove('socratic-highlight', 'socratic-highlight-subtle');
            }
        });

        // Update state
        setHighlightedPanels(targets);

        // Apply new highlights
        if (targets.length > 0) {
            // Primary target gets strong highlight
            const primaryTarget = targets[0];
            const primaryElement = document.getElementById(HIGHLIGHT_TARGET_MAP[primaryTarget]);
            if (primaryElement) {
                primaryElement.classList.add('socratic-highlight');
                primaryElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            // Secondary targets get subtle highlight
            targets.slice(1).forEach(target => {
                const elementId = HIGHLIGHT_TARGET_MAP[target];
                const element = document.getElementById(elementId);
                if (element) {
                    element.classList.add('socratic-highlight-subtle');
                }
            });
        }
    }, [highlightedPanels]);

    const handleDataWizardComplete = (config: any) => {
        console.log('Data wizard complete:', config);
        setShowDataWizard(false);

        // Execute the analysis with the user's data configuration
        handleQuerySubmit(config.query, {
            run_type: 'user_data_analysis',
            dataset_context: {
                filename: config.dataPreview?.fileName,
                columns: config.dataPreview?.columns?.map((c: any) => c.name),
                variables: {
                    treatment: config.treatment,
                    outcome: config.outcome,
                    covariates: config.covariates
                },
                analysisType: config.analysisType
            }
        });
    };

    const suggestedQueries = dynamicSuggestedQueries;

    return (
        <div className="min-h-screen bg-[--bg-page]">
            {/* Onboarding Overlay - First Run Experience */}
            {showOnboarding && (
                <OnboardingOverlay
                    scenarios={apiScenarios}
                    onSelectScenario={handleScenarioChange}
                    onUploadData={() => {
                        setShowOnboarding(false);
                        setShowDataWizard(true);
                    }}
                    onStartChat={() => {
                        setShowOnboarding(false);
                        localStorage.setItem('carf-visited', 'true');
                    }}
                    onDismiss={() => {
                        setShowOnboarding(false);
                        localStorage.setItem('carf-visited', 'true');
                    }}
                    onStartTour={() => {
                        setShowOnboarding(false);
                        setShowWalkthrough(true);
                        localStorage.setItem('carf-visited', 'true');
                    }}
                />
            )}

            {/* Walkthrough Manager */}
            {showWalkthrough && (
                <WalkthroughManager
                    onClose={() => setShowWalkthrough(false)}
                    onTrackComplete={(trackId) => {
                        console.log('Completed walkthrough track:', trackId);
                        localStorage.setItem(`carf-tour-${trackId}`, 'completed');
                    }}
                />
            )}

            {/* Data Onboarding Wizard */}
            <DataOnboardingWizard
                isOpen={showDataWizard}
                onClose={() => setShowDataWizard(false)}
                onComplete={handleDataWizardComplete}
            />

            {/* Methodology Modal */}
            <MethodologyModal
                isOpen={showMethodologyModal}
                onClose={() => setShowMethodologyModal(false)}
                type={methodologyType}
                causalResult={queryResponse?.causalResult}
                bayesianResult={queryResponse?.bayesianResult}
                dataSource={{
                    name: selectedScenario ? `${selectedScenario}.csv` : 'demo_data.csv',
                    rows: 1247,
                    columns: 8,
                }}
            />

            {/* File Analysis Modal */}
            <FileAnalysisModal
                isOpen={showFileAnalysisModal}
                onClose={() => setShowFileAnalysisModal(false)}
                onAnalysisComplete={(result) => {
                    setFileAnalysisResult(result);
                    console.log('File analysis complete:', result);
                }}
                onRunQuery={(query, context) => {
                    setShowFileAnalysisModal(false);
                    handleQuerySubmit(query, context);
                }}
            />

            {/* Demo Mode Banner */}
            {isDemoMode && (
                <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-center">
                    <span className="text-amber-800 text-sm">
                        Running in Demo Mode - Using synthetic data.{' '}
                        <button
                            onClick={() => setShowSettingsModal(true)}
                            className="font-medium text-amber-900 ml-1 hover:underline focus:outline-none"
                        >
                            (Connect backend API for production use)
                        </button>
                    </span>
                </div>
            )}

            {/* API Error Banner */}
            {apiError && (
                <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-center">
                    <span className="text-red-800 text-sm">
                        {apiError}{' '}
                        <button
                            onClick={() => setApiError(null)}
                            className="font-medium text-red-900 ml-1 hover:underline focus:outline-none"
                        >
                            Dismiss
                        </button>
                    </span>
                </div>
            )}

            {/* Settings Modal */}
            <SettingsModal
                isOpen={showSettingsModal}
                onClose={() => setShowSettingsModal(false)}
                onConfigUpdated={() => {
                    // Refresh page to pick up new config state
                    window.location.reload();
                }}
            />

            {/* Header with Help Button */}
            <header className="glass-strong border-b sticky top-0 z-40">
                <div className="container mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        {/* Left: Logo and Title */}
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            </div>
                            <div>
                                <h1 className="text-xl font-bold text-gradient">CYNEPIC Architecture</h1>
                                <p className="text-xs text-gray-500">v0.5 · Epistemic Cockpit</p>
                            </div>
                        </div>

                        {/* Center: View Mode Tabs + Scenario Selector */}
                        <div className="flex items-center gap-4" data-tour="scenario-selector">
                            {/* Phase 7: View Mode Tabs */}
                            <div className="flex items-center bg-gray-100 rounded-lg p-1">
                                {(['analyst', 'developer', 'executive'] as ViewMode[]).map((mode) => (
                                    <button
                                        key={mode}
                                        onClick={() => setViewMode(mode)}
                                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${viewMode === mode
                                            ? 'bg-white text-primary shadow-sm'
                                            : 'text-gray-600 hover:text-gray-900'
                                            }`}
                                    >
                                        {mode.charAt(0).toUpperCase() + mode.slice(1)}
                                    </button>
                                ))}
                            </div>

                            <select
                                value={selectedScenario}
                                onChange={(e) => handleScenarioChange(e.target.value)}
                                className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary min-w-[200px]"
                            >
                                <option value="">Select Scenario...</option>
                                {apiScenarios.map((scenario) => (
                                    <option key={scenario.id} value={scenario.id}>
                                        {scenario.emoji} {scenario.name}
                                    </option>
                                ))}
                            </select>

                            {/* Session Badge */}
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-lg">
                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                                <span className="text-xs font-mono text-green-700">
                                    {sessionId.slice(0, 16)}...
                                </span>
                            </div>
                        </div>

                        {/* Right: Controls */}
                        <div className="flex items-center gap-2">
                            {/* Human-in-the-Loop Escalations Button */}
                            <button
                                onClick={() => setShowEscalationModal(true)}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors group relative"
                                title="Human review queue"
                            >
                                <svg className="w-5 h-5 text-gray-600 group-hover:text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                                {pendingEscalationsCount > 0 && (
                                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-orange-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center animate-pulse">
                                        {pendingEscalationsCount > 9 ? '9+' : pendingEscalationsCount}
                                    </span>
                                )}
                            </button>
                            {/* Phase 7: History Button */}
                            <button
                                onClick={() => setShowHistoryPanel(true)}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors group relative"
                                title="Analysis history"
                            >
                                <svg className="w-5 h-5 text-gray-600 group-hover:text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                {history.length > 0 && (
                                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-primary text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                                        {history.length > 9 ? '9+' : history.length}
                                    </span>
                                )}
                            </button>
                            {/* Help/Walkthrough Button */}
                            <button
                                onClick={() => setShowWalkthrough(true)}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors group"
                                title="Start guided tour"
                            >
                                <svg className="w-5 h-5 text-gray-600 group-hover:text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </button>
                            <button
                                onClick={() => setShowOnboarding(true)}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                                title="Show scenario picker"
                            >
                                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                                </svg>
                            </button>
                            {/* Dark Mode Toggle */}
                            <QuickThemeToggle className="mr-1" />
                            <button className="p-2 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
                                <svg className="w-5 h-5 text-gray-600 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                            </button>
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white text-sm font-semibold">
                                U
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content Area - View Mode Conditional */}
            <div className="container mx-auto px-4 py-6">
                {viewMode === 'developer' ? (
                    /* DEVELOPER VIEW - Full transparency cockpit */
                    <div className="grid grid-cols-12 gap-6">
                        {/* Left: Query Input + Developer Cockpit */}
                        <div className="col-span-4 space-y-4">
                            <div className="card" data-tour="query-input">
                                <div className="flex items-center justify-between mb-3">
                                    <h2 className="text-lg font-semibold text-gray-900">Query Input</h2>
                                    <button
                                        onClick={() => setUseConversationalFlow(!useConversationalFlow)}
                                        className="text-xs text-gray-500 hover:text-primary transition-colors"
                                    >
                                        {useConversationalFlow ? 'Simple mode' : 'Guided mode'}
                                    </button>
                                </div>
                                {useConversationalFlow ? (
                                    <ConversationalQueryFlow
                                        onSubmitQuery={(query) => handleQuerySubmit(query)}
                                        suggestedQueries={suggestedQueries}
                                        hasDataset={!!selectedScenario}
                                        datasetName={selectedScenario || undefined}
                                        isProcessing={isProcessing}
                                    />
                                ) : (
                                    <QueryInput
                                        onSubmit={handleQuerySubmit}
                                        suggestedQueries={suggestedQueries}
                                        isProcessing={isProcessing}
                                    />
                                )}
                            </div>

                            {/* Developer Cockpit - Architecture, Logs, Timeline */}
                            <div className="card min-h-[500px]">
                                <DeveloperView
                                    response={queryResponse}
                                    executionTrace={queryResponse?.reasoningChain?.map((step) => ({
                                        layer: step.node?.toLowerCase().includes('guardian') ? 'guardian'
                                            : step.node?.toLowerCase().includes('router') ? 'router'
                                                : step.node?.toLowerCase().includes('bayesian') ? 'mesh'
                                                    : 'services',
                                        node: step.node,
                                        action: step.action,
                                        durationMs: step.durationMs,
                                        confidence: step.confidence || 'medium',
                                        timestamp: step.timestamp,
                                    })) || []}
                                    isProcessing={isProcessing}
                                />
                            </div>
                        </div>

                        {/* Center: Analysis Components */}
                        <div className="col-span-5 space-y-4">
                            <div className="card min-h-[350px]" data-tour="results-area" id="dag-viewer">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Causal DAG</h2>
                                <CausalDAG
                                    nodes={generateDAGFromCausalResult(queryResponse?.causalResult).nodes}
                                    edges={generateDAGFromCausalResult(queryResponse?.causalResult).edges}
                                    onNodeClick={(id) => console.log('Node clicked:', id)}
                                />
                            </div>
                            <div className="card" id="causal-results">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Causal Analysis</h2>
                                <CausalAnalysisCard result={queryResponse?.causalResult || null} />
                            </div>
                        </div>

                        {/* Right: Domain Classification + Raw State */}
                        <div className="col-span-3 space-y-4">
                            <div className="card" id="cynefin-panel">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Cynefin Router</h2>
                                <CynefinRouter
                                    domain={queryResponse?.domain || null}
                                    confidence={queryResponse?.domainConfidence || 0}
                                    entropy={queryResponse?.domainEntropy || 0}
                                    solver={queryResponse?.triggeredMethod || (queryResponse?.domain === 'complicated' ? 'Causal Analyst' : queryResponse?.domain === 'complex' ? 'Bayesian Explorer' : 'Unknown')}
                                    isProcessing={isProcessing}
                                    scores={queryResponse?.domainScores as Record<import('../../types/carf').CynefinDomain, number> | undefined}
                                    reasoning={queryResponse?.routerReasoning || undefined}
                                    keyIndicators={queryResponse?.routerKeyIndicators}
                                    triggeredMethod={queryResponse?.triggeredMethod || undefined}
                                />
                            </div>
                            {/* Domain-Specific Visualization */}
                            <DomainVisualization
                                domain={queryResponse?.domain || null}
                                confidence={queryResponse?.domainConfidence || 0}
                                onEscalate={() => setShowEscalationModal(true)}
                                onAction={handleDomainAction}
                                isProcessing={isProcessing}
                                causalResult={queryResponse?.causalResult || null}
                                bayesianResult={queryResponse?.bayesianResult || null}
                            />
                            {/* Transparency Panel for Developer View */}
                            <TransparencyPanel
                                queryResponse={queryResponse}
                            />
                            <div className="card" id="bayesian-panel">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Bayesian Panel</h2>
                                <BayesianPanel belief={queryResponse?.bayesianResult || null} />
                            </div>
                            <div className="card" id="guardian-panel">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Guardian</h2>
                                <GuardianPanel decision={queryResponse?.guardianResult || null} />
                            </div>
                        </div>
                    </div>
                ) : viewMode === 'executive' ? (
                    /* EXECUTIVE VIEW - High-level KPI Dashboard and Decision Summary */
                    <div className="space-y-6">
                        <div className="grid grid-cols-12 gap-6">
                            {/* Left: Quick Query + Decision Status */}
                            <div className="col-span-3 space-y-4">
                                <div className="card" data-tour="query-input">
                                    <h2 className="text-lg font-semibold text-gray-900 mb-3">Ask a Question</h2>
                                    <QueryInput
                                        onSubmit={handleQuerySubmit}
                                        suggestedQueries={suggestedQueries.slice(0, 2)}
                                        isProcessing={isProcessing}
                                    />
                                </div>

                                {/* Guardian Decision - Prominent */}
                                <div className="card">
                                    <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                        <span className="text-xl">🛡️</span> Policy Status
                                    </h2>
                                    <GuardianPanel decision={queryResponse?.guardianResult || null} />
                                </div>
                            </div>

                            {/* Center: Key Insights and Recommendations */}
                            <div className="col-span-6 space-y-4">
                                <div className="card">
                                    <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                        <span className="text-xl">💡</span> Key Insights
                                    </h2>
                                    {queryResponse?.keyInsights && queryResponse.keyInsights.length > 0 ? (
                                        <ul className="space-y-2">
                                            {queryResponse.keyInsights.map((insight, idx) => (
                                                <li key={idx} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg">
                                                    <span className="text-green-500 mt-0.5">✓</span>
                                                    <span className="text-sm text-gray-700">{insight}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    ) : (
                                        <p className="text-sm text-gray-500 italic">Submit a query to generate insights</p>
                                    )}
                                </div>

                                {/* Executive KPI Panel with Dynamic Visualization */}
                                <div className="card">
                                    <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                        <span className="text-xl">📊</span> Analysis Board
                                    </h2>
                                    <ExecutiveKPIPanel
                                        queryResponse={queryResponse}
                                        causalResult={queryResponse?.causalResult || null}
                                        bayesianResult={queryResponse?.bayesianResult || null}
                                        guardianResult={queryResponse?.guardianResult || null}
                                        context={queryResponse?.domain || 'general'}
                                        onDrillDown={() => setViewMode('analyst')}
                                    />
                                </div>

                                <div className="card">
                                    <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                        <span className="text-xl">🎯</span> Recommended Actions
                                    </h2>
                                    {queryResponse?.nextSteps && queryResponse.nextSteps.length > 0 ? (
                                        <ol className="space-y-2">
                                            {queryResponse.nextSteps.map((step, idx) => (
                                                <li key={idx} className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-100 rounded-lg">
                                                    <span className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                                                        {idx + 1}
                                                    </span>
                                                    <span className="text-sm text-gray-700">{step}</span>
                                                </li>
                                            ))}
                                        </ol>
                                    ) : (
                                        <p className="text-sm text-gray-500 italic">Run an analysis to see recommended actions</p>
                                    )}
                                </div>
                            </div>

                            {/* Right: Analysis Response */}
                            <div className="col-span-3 space-y-4">
                                <div className="card">
                                    <h2 className="text-lg font-semibold text-gray-900 mb-3">Analysis Summary</h2>
                                    <ConversationalResponse
                                        response={queryResponse}
                                        onFollowUpQuestion={handleFollowUpQuestion}
                                        onViewMethodology={handleViewMethodology}
                                        onViewData={() => setShowDataWizard(true)}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                ) : (
                    /* ANALYST VIEW (default) - Full analysis dashboard */
                    <div className="grid grid-cols-12 gap-6">
                        {/* Left Sidebar (3 columns) */}
                        <div className="col-span-3 space-y-4">
                            <div className="card" data-tour="query-input">
                                <div className="flex items-center justify-between mb-3">
                                    <h2 className="text-lg font-semibold text-gray-900">Query Input</h2>
                                    <button
                                        onClick={() => setUseConversationalFlow(!useConversationalFlow)}
                                        className="text-xs text-gray-500 hover:text-primary transition-colors"
                                    >
                                        {useConversationalFlow ? 'Simple mode' : 'Guided mode'}
                                    </button>
                                </div>

                                {/* Processing Progress Indicator */}
                                {(isProcessing || apiLoading) && (
                                    <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full" />
                                            <span className="text-sm font-medium text-blue-700">
                                                {processingMessage || 'Processing query...'}
                                            </span>
                                        </div>
                                        <div className="w-full bg-blue-200 rounded-full h-2 overflow-hidden">
                                            <div
                                                className="h-2 bg-blue-500 rounded-full transition-all duration-300"
                                                style={{ width: `${apiProgress}%` }}
                                            />
                                        </div>
                                    </div>
                                )}
                                {useConversationalFlow ? (
                                    <ConversationalQueryFlow
                                        onSubmitQuery={(query) => handleQuerySubmit(query)}
                                        suggestedQueries={suggestedQueries}
                                        hasDataset={!!selectedScenario}
                                        datasetName={selectedScenario || undefined}
                                        isProcessing={isProcessing}
                                    />
                                ) : (
                                    <QueryInput
                                        onSubmit={handleQuerySubmit}
                                        suggestedQueries={suggestedQueries}
                                        isProcessing={isProcessing}
                                    />
                                )}
                            </div>

                            {/* AI Guidance Panel */}
                            {aiSuggestions.length > 0 && (
                                <div className="mb-4">
                                    <PromptGuidancePanel
                                        suggestions={aiSuggestions}
                                        onApplySuggestion={handleApplySuggestion}
                                        isLoading={false}
                                    />
                                </div>
                            )}

                            <div className="card" id="cynefin-panel">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Cynefin Router</h2>
                                <CynefinRouter
                                    domain={queryResponse?.domain || null}
                                    confidence={queryResponse?.domainConfidence || 0}
                                    entropy={queryResponse?.domainEntropy || 0}
                                    solver={queryResponse?.triggeredMethod || (queryResponse?.domain === 'complicated' ? 'Causal Analyst' : queryResponse?.domain === 'complex' ? 'Bayesian Explorer' : 'Unknown')}
                                    isProcessing={isProcessing}
                                    scores={queryResponse?.domainScores as Record<import('../../types/carf').CynefinDomain, number> | undefined}
                                    reasoning={queryResponse?.routerReasoning || undefined}
                                    keyIndicators={queryResponse?.routerKeyIndicators}
                                    triggeredMethod={queryResponse?.triggeredMethod || undefined}
                                />
                            </div>

                            <div className="card" id="bayesian-panel">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Bayesian Panel</h2>
                                <BayesianPanel belief={queryResponse?.bayesianResult || null} />
                            </div>
                        </div>

                        {/* Center Column (6 columns) */}
                        <div className="col-span-6 space-y-4">
                            <div className="card min-h-[450px]" data-tour="results-area" id="dag-viewer">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Causal DAG</h2>
                                <CausalDAG
                                    nodes={generateDAGFromCausalResult(queryResponse?.causalResult).nodes}
                                    edges={generateDAGFromCausalResult(queryResponse?.causalResult).edges}
                                    onNodeClick={(id) => console.log('Node clicked:', id)}
                                />
                            </div>

                            <div className="card" id="causal-results">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Causal Analysis Results</h2>
                                <CausalAnalysisCard result={queryResponse?.causalResult || null} />
                            </div>

                            <div className="card" id="intervention-sim">
                                <InterventionSimulator
                                    treatment={queryResponse?.causalResult?.treatment || 'Treatment'}
                                    outcome={queryResponse?.causalResult?.outcome || 'Outcome'}
                                    baseTreatmentValue={10.0}
                                    baseOutcomeValue={50.0}
                                    effectSize={queryResponse?.causalResult?.effect || 0.5}
                                    unit={queryResponse?.causalResult?.unit}
                                />
                            </div>

                            <div className="card" id="guardian-panel">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Guardian Panel</h2>
                                <GuardianPanel decision={queryResponse?.guardianResult || null} />
                            </div>

                            {/* Conversational Response - Dialog-based results with confidence zones */}
                            <div className="card">
                                <ConversationalResponse
                                    response={queryResponse}
                                    onFollowUpQuestion={handleFollowUpQuestion}
                                    onViewMethodology={handleViewMethodology}
                                    onViewData={() => setShowDataWizard(true)}
                                />
                            </div>
                        </div>

                        {/* Right Sidebar (3 columns) */}
                        <div className="col-span-3 space-y-4">
                            {/* Transparency Panel - Reliability, Agents, EU AI Act */}
                            <TransparencyPanel
                                queryResponse={queryResponse}
                            />

                            {queryResponse?.causalResult && (
                                <div className="card h-[300px]">
                                    <SensitivityPlot
                                        gamma={
                                            // Derive gamma from refutation test robustness
                                            // More tests passed = higher hidden bias tolerance
                                            queryResponse.causalResult.refutationsTotal > 0
                                                ? 1 + (queryResponse.causalResult.refutationsPassed / queryResponse.causalResult.refutationsTotal) * 1.5
                                                : 1.5
                                        }
                                        treatment={queryResponse.causalResult.treatment}
                                        outcome={queryResponse.causalResult.outcome}
                                        refutationsPassed={queryResponse.causalResult.refutationsPassed}
                                        refutationsTotal={queryResponse.causalResult.refutationsTotal}
                                    />
                                </div>
                            )}
                            <div className="card min-h-[400px]">
                                <h2 className="text-lg font-semibold text-gray-900 mb-3">Execution Trace</h2>
                                <ExecutionTrace
                                    steps={queryResponse?.reasoningChain || []}
                                    sessionId={queryResponse?.sessionId || sessionId}
                                />
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Human-in-the-Loop Escalation Modal */}
            <EscalationModal
                isOpen={showEscalationModal}
                onClose={() => setShowEscalationModal(false)}
                onResolved={(escalation) => {
                    console.log('Escalation resolved:', escalation);
                    setPendingEscalationsCount(prev => Math.max(0, prev - 1));
                }}
            />

            {/* Phase 7: Analysis History Panel */}
            <AnalysisHistoryPanel
                isOpen={showHistoryPanel}
                onClose={() => setShowHistoryPanel(false)}
                history={history}
                onViewSession={handleViewSession}
                onRerunSession={handleRerunSession}
                onDeleteSession={deleteAnalysis}
                onClearHistory={clearHistory}
                onCompare={handleCompareSessions}
            />

            {/* Phase 7: Simulation Arena */}
            {(!comparisonSessions || (comparisonSessions[0] && comparisonSessions[1])) && (
            <SimulationArena
                isOpen={!!comparisonSessions}
                onClose={() => setComparisonSessions(null)}
                sessionA={comparisonSessions ? comparisonSessions[0] : history[0]}
                sessionB={comparisonSessions ? comparisonSessions[1] : (history.length > 1 ? history[1] : history[0])}
                onRerunWithChanges={handleRerunWithChanges}
            />
            )}

            {/* Phase 7: Intelligent Chat Tab - Always visible in bottom-right */}
            <IntelligentChatTab
                messages={chatMessages}
                onSendMessage={handleIntelligentChatMessage}
                onExecuteQuery={handleQuerySubmit}
                onOpenHistory={() => setShowHistoryPanel(true)}
                onOpenAnalyze={() => setShowFileAnalysisModal(true)}
                onLinkClick={handleLinkClick}
                onHighlightPanels={handleHighlightPanels}
                isProcessing={isProcessing || apiLoading}
                lastQueryResponse={queryResponse}
            />
        </div>
    );
};

export default DashboardLayout;
