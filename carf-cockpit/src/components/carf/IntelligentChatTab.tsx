import React, { useState, useRef, useEffect, useCallback } from 'react';
import type { ChatMessage, SlashCommand, SlashCommandConfig, SocraticModeState, QueryResponse } from '../../types/carf';
import api from '../../services/apiService';
import {
    QUESTIONING_FLOWS,
    getApplicableFlows,
    type QuestioningFlow,
    type QuestioningStep,
    type HighlightTarget,
} from '../../config/questioningFlow';

// Slash command definitions
const SLASH_COMMANDS: SlashCommandConfig[] = [
    {
        command: '/analyze',
        description: 'Upload and analyze a file or paste text content',
        usage: '/analyze',
        example: '/analyze',
    },
    {
        command: '/question',
        description: 'Start Socratic mode - AI asks probing questions to improve your analysis',
        usage: '/question',
        example: '/question',
    },
    {
        command: '/query',
        description: 'Execute an analysis query directly',
        usage: '/query [your question]',
        example: '/query What drives Scope 3 emissions?',
    },
    {
        command: '/analysis',
        description: 'View snapshot of last analysis with key metrics',
        usage: '/analysis',
        example: '/analysis',
    },
    {
        command: '/history',
        description: 'Browse past analyses',
        usage: '/history',
        example: '/history',
    },
    {
        command: '/help',
        description: 'Show available commands and platform guide',
        usage: '/help [topic]',
        example: '/help causal',
    },
    {
        command: '/benchmark',
        description: 'Run benchmark tests against known datasets',
        usage: '/benchmark [id]',
        example: '/benchmark sustainability_carbon_footprint',
    },
    { command: '/summary', description: 'Generate executive summary of current analysis', usage: '/summary', example: '/summary' },
];

interface IntelligentChatTabProps {
    messages: ChatMessage[];
    onSendMessage: (message: string, isSlashCommand?: boolean, commandType?: SlashCommand) => void;
    onExecuteQuery: (query: string) => void;
    onOpenHistory: () => void;
    onOpenAnalyze?: () => void;
    onLinkClick?: (panelId: string) => void;
    onHighlightPanels?: (targets: HighlightTarget[]) => void;
    isProcessing?: boolean;
    lastQueryResponse?: QueryResponse | null;
}

// Extended Socratic state with flow tracking
interface EnhancedSocraticState extends SocraticModeState {
    activeFlow?: QuestioningFlow;
    currentFlowStep?: QuestioningStep;
    flowHistory: { stepId: string; answer: string }[];
}

const IntelligentChatTab: React.FC<IntelligentChatTabProps> = ({
    messages,
    onSendMessage,
    onExecuteQuery,
    onOpenHistory,
    onOpenAnalyze,
    onLinkClick,
    onHighlightPanels,
    isProcessing = false,
    lastQueryResponse,
}) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const [showCommandMenu, setShowCommandMenu] = useState(false);
    const [filteredCommands, setFilteredCommands] = useState<SlashCommandConfig[]>([]);
    const [selectedCommandIndex, setSelectedCommandIndex] = useState(0);
    const [socraticMode, setSocraticMode] = useState<EnhancedSocraticState>({
        isActive: false,
        currentStep: 0,
        totalSteps: 4,
        questions: [],
        answers: [],
        suggestions: [],
        flowHistory: [],
    });

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (isExpanded && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isExpanded]);

    useEffect(() => {
        if (isExpanded && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isExpanded]);

    // Handle slash command detection
    useEffect(() => {
        if (inputValue.startsWith('/')) {
            const query = inputValue.toLowerCase();
            const matches = SLASH_COMMANDS.filter(cmd =>
                cmd.command.toLowerCase().startsWith(query.split(' ')[0])
            );
            setFilteredCommands(matches);
            setShowCommandMenu(matches.length > 0);
            setSelectedCommandIndex(0);
        } else {
            setShowCommandMenu(false);
            setFilteredCommands([]);
        }
    }, [inputValue]);

    const handleCommandSelect = useCallback((command: SlashCommandConfig) => {
        setInputValue(command.command + ' ');
        setShowCommandMenu(false);
        inputRef.current?.focus();
    }, []);

    const processSlashCommand = useCallback(async (input: string) => {
        const parts = input.trim().split(' ');
        const command = parts[0].toLowerCase() as SlashCommand;
        const args = parts.slice(1).join(' ');

        switch (command) {
            case '/analyze':
                if (onOpenAnalyze) {
                    onOpenAnalyze();
                    onSendMessage('Opening file analysis dialog...', true, '/analyze' as SlashCommand);
                } else {
                    onSendMessage('File analysis is not available. Use the "Upload Data" button in the main interface.', false);
                }
                return true;

            case '/question':
                startSocraticMode();
                return true;

            case '/query':
                if (args) {
                    onExecuteQuery(args);
                } else {
                    onSendMessage('Please provide a query after /query. Example: /query What drives emissions?', false);
                }
                return true;

            case '/analysis':
                showAnalysisSnapshot();
                return true;

            case '/history':
                onOpenHistory();
                return true;

            case '/help':
                showHelp(args);
                return true;

            case '/benchmark':
                handleBenchmark(args);
                return true;

            case '/summary': {
                // Generate executive summary from current analysis context
                const summaryContext = {
                    domain: lastQueryResponse?.domain || 'unknown',
                    domain_confidence: lastQueryResponse?.domainConfidence || 0,
                    causal_effect: lastQueryResponse?.causalResult?.effect || null,
                    refutation_pass_rate: lastQueryResponse?.causalResult?.refutationsPassed != null && lastQueryResponse?.causalResult?.refutationsTotal
                        ? lastQueryResponse.causalResult.refutationsPassed / lastQueryResponse.causalResult.refutationsTotal
                        : null,
                    bayesian_uncertainty: lastQueryResponse?.bayesianResult?.epistemicUncertainty || null,
                    guardian_verdict: lastQueryResponse?.guardianVerdict || 'unknown',
                    treatment: lastQueryResponse?.causalResult?.treatment || null,
                    outcome: lastQueryResponse?.causalResult?.outcome || null,
                    p_value: lastQueryResponse?.causalResult?.pValue || null,
                };

                try {
                    const { getExecutiveSummary } = await import('../../services/apiService');
                    const summary = await getExecutiveSummary(summaryContext);
                    onSendMessage(
                        `## Executive Summary\n\n` +
                        `**Key Finding:** ${summary.key_finding}\n\n` +
                        `**Confidence:** ${summary.confidence_level}\n\n` +
                        `**Risk Assessment:** ${summary.risk_assessment}\n\n` +
                        `**Recommendation:** ${summary.recommended_action}\n\n` +
                        `---\n\n${summary.plain_explanation}`,
                        true, '/summary' as SlashCommand
                    );
                } catch {
                    onSendMessage(
                        'Unable to generate executive summary. Please run an analysis first using /query.',
                        false
                    );
                }
                return true;
            }

            default:
                return false;
        }
    }, [onExecuteQuery, onOpenHistory, onOpenAnalyze, onSendMessage]);

    const startSocraticMode = () => {
        // Determine applicable flows based on query results
        const applicableFlows = getApplicableFlows({
            domain: lastQueryResponse?.domain,
            hasCausalAnalysis: !!lastQueryResponse?.causalResult,
            hasBayesianAnalysis: !!lastQueryResponse?.bayesianResult,
            hasUncertainty: (lastQueryResponse?.domainConfidence || 0) < 0.8,
        });

        // Select the most appropriate flow or default to cynefin-orientation
        const selectedFlow = applicableFlows.length > 0
            ? applicableFlows[0]
            : QUESTIONING_FLOWS.find(f => f.id === 'cynefin-orientation')!;

        const firstStep = selectedFlow.steps[0];

        setSocraticMode({
            isActive: true,
            currentStep: 0,
            totalSteps: selectedFlow.steps.length,
            questions: selectedFlow.steps.map(s => s.question),
            answers: [],
            suggestions: [],
            activeFlow: selectedFlow,
            currentFlowStep: firstStep,
            flowHistory: [],
        });

        // Trigger panel highlighting for the first step
        if (onHighlightPanels && firstStep.highlightTargets.length > 0) {
            onHighlightPanels(firstStep.highlightTargets);
        }

        // Build intro message with hint if available
        const hintText = firstStep.hint ? `\n\n*Hint: ${firstStep.hint}*` : '';
        const introMessage = `**Starting Socratic Mode: ${selectedFlow.name}**

${selectedFlow.description}

I'll guide you through ${selectedFlow.steps.length} questions to deepen your understanding.

**Step 1/${selectedFlow.steps.length} - ${firstStep.phase.charAt(0).toUpperCase() + firstStep.phase.slice(1)}:**
${firstStep.question}${hintText}`;

        onSendMessage(introMessage, true, '/question');
    };

    const showAnalysisSnapshot = () => {
        if (!lastQueryResponse) {
            onSendMessage('No analysis results available yet. Run a query first using /query or the main input.', false);
            return;
        }

        const snapshot = `**Last Analysis Snapshot**

**Query Domain:** ${lastQueryResponse.domain} (${(lastQueryResponse.domainConfidence * 100).toFixed(0)}% confidence)
**Entropy:** ${lastQueryResponse.domainEntropy.toFixed(2)}

${lastQueryResponse.causalResult ? `**Causal Effect:** ${lastQueryResponse.causalResult.effect} ${lastQueryResponse.causalResult.unit}
**p-value:** ${lastQueryResponse.causalResult.pValue}
**Refutations:** ${lastQueryResponse.causalResult.refutationsPassed}/${lastQueryResponse.causalResult.refutationsTotal} passed` : ''}

${lastQueryResponse.bayesianResult ? `**Bayesian Posterior:** ${lastQueryResponse.bayesianResult.posteriorMean.toFixed(3)}
**Uncertainty:** Epistemic ${(lastQueryResponse.bayesianResult.epistemicUncertainty * 100).toFixed(0)}% | Aleatoric ${(lastQueryResponse.bayesianResult.aleatoricUncertainty * 100).toFixed(0)}%` : ''}

**Guardian Verdict:** ${lastQueryResponse.guardianVerdict || 'N/A'}

Use /history to see all past analyses.`;

        onSendMessage(snapshot, true, '/analysis');
    };

    const showHelp = (topic?: string) => {
        let helpText = '';

        if (!topic) {
            helpText = `**CARF Chat Commands**

| Command | Description |
|---------|-------------|
| \`/question\` | Start Socratic mode for guided analysis improvement |
| \`/query [text]\` | Execute an analysis query |
| \`/analysis\` | View last analysis snapshot |
| \`/history\` | Browse past analyses |
| \`/help [topic]\` | Show help (topics: causal, bayesian, cynefin, guardian) |

**Tips:**
- Type \`/\` to see command autocomplete
- Ask natural questions about your data
- Click on linked panels to see details`;
        } else {
            const topics: Record<string, string> = {
                causal: `**Causal Analysis Help**

CARF uses DoWhy/EconML for causal inference:
- **Treatment:** The variable you can change
- **Outcome:** The effect you want to measure
- **Confounders:** Variables that affect both treatment and outcome

**Refutation tests** validate the causal claim by testing robustness.`,
                bayesian: `**Bayesian Analysis Help**

CARF uses Bayesian inference for uncertainty quantification:
- **Prior:** Your belief before seeing data
- **Posterior:** Updated belief after data
- **Epistemic Uncertainty:** Reducible with more data
- **Aleatoric Uncertainty:** Inherent randomness`,
                cynefin: `**Cynefin Framework Help**

CARF classifies queries into 5 domains:
- **Clear:** Obvious cause-effect, best practices
- **Complicated:** Expert analysis needed
- **Complex:** Emergent patterns, probe-sense-respond
- **Chaotic:** Crisis mode, act first
- **Disorder:** Cannot classify`,
                guardian: `**Guardian Policy Help**

The Guardian layer enforces policies before actions:
- Checks budget thresholds
- Validates confidence levels
- Ensures compliance rules
- May require human approval`,
                simulation: `**Simulation Arena Help**

The Simulation Arena lets you run "What-If" scenarios:
- **Compare** multiple analysis sessions side-by-side
- **What-If sliders** adjust treatment variables
- **Outcome charts** show predicted effects
- **Parameter diff** compares configuration changes`,
                benchmark: `**Benchmarking Help**

Test CARF against known datasets:
- \`/benchmark\` - List available benchmarks
- \`/benchmark [id]\` - Run a specific test
- Results show effect size, confidence, and direction

**Available benchmarks:** sustainability, finance, supply_chain`,
                'getting-started': `**Getting Started with CARF**

1. **Upload data** using the Data Wizard or /analyze
2. **Ask a question** about causal relationships
3. **Review the Cynefin classification** for analysis type
4. **Explore results** in Causal/Bayesian panels
5. **Use /history** to track past analyses

Type \`/help [topic]\` for specific guidance.`,
            };

            helpText = topics[topic.toLowerCase()] || `Unknown help topic: ${topic}. Try: causal, bayesian, cynefin, guardian, simulation, benchmark, getting-started`;
        }

        onSendMessage(helpText, true, '/help');
    };

    const handleBenchmark = async (args: string) => {
        const API_BASE = 'http://localhost:8000';

        if (!args.trim()) {
            // List available benchmarks
            try {
                const response = await fetch(`${API_BASE}/benchmarks`);
                if (response.ok) {
                    const benchmarks = await response.json();
                    const list = benchmarks
                        .map((b: { id: string; name: string; domain: string }) => `- **${b.id}**: ${b.name} (${b.domain})`)
                        .join('\n');
                    onSendMessage(`**Available Benchmarks:**\n\n${list}\n\nRun with: \`/benchmark [id]\``, true, '/benchmark');
                } else {
                    onSendMessage('Failed to fetch benchmarks. Is the backend running?', false);
                }
            } catch {
                onSendMessage('Cannot connect to backend. Ensure the API is running at localhost:8000.', false);
            }
        } else {
            // Run specific benchmark
            const benchmarkId = args.trim();
            onSendMessage(`Running benchmark: **${benchmarkId}**...`, true, '/benchmark');

            try {
                const response = await fetch(`${API_BASE}/benchmarks/${benchmarkId}/run`, { method: 'POST' });
                if (response.ok) {
                    const result = await response.json();
                    const status = result.passed ? '✅ PASSED' : '❌ FAILED';
                    const details = [
                        `**Status:** ${status}`,
                        `**Effect:** ${result.actual_effect?.toFixed(4)} (expected: ${result.expected_range?.[0]} to ${result.expected_range?.[1]})`,
                        `**Confidence:** ${(result.actual_confidence * 100)?.toFixed(1)}% (min: ${(result.expected_confidence_min * 100)?.toFixed(1)}%)`,
                        `**Direction match:** ${result.effect_direction_match ? '✓ Yes' : '✗ No'}`,
                    ].join('\n');
                    onSendMessage(`**Benchmark Result: ${benchmarkId}**\n\n${details}`, true, '/benchmark');
                } else if (response.status === 404) {
                    onSendMessage(`Benchmark "${benchmarkId}" not found. Use \`/benchmark\` to list available benchmarks.`, false);
                } else {
                    onSendMessage(`Benchmark failed: ${response.statusText}`, false);
                }
            } catch {
                onSendMessage('Cannot connect to backend for benchmark run.', false);
            }
        }
    };

    const handleSocraticAnswer = (answer: string) => {
        const newAnswers = [...socraticMode.answers, answer];
        const nextStepIndex = socraticMode.currentStep + 1;
        const currentStep = socraticMode.currentFlowStep;
        const activeFlow = socraticMode.activeFlow;

        // Record this step in history
        const newHistory = [...socraticMode.flowHistory];
        if (currentStep) {
            newHistory.push({ stepId: currentStep.id, answer });
        }

        if (nextStepIndex >= socraticMode.totalSteps || !activeFlow) {
            // Finish Socratic mode
            const suggestions = generateSuggestions(newAnswers, activeFlow, currentStep);

            // Clear highlights when finishing
            if (onHighlightPanels) {
                onHighlightPanels([]);
            }

            setSocraticMode({
                ...socraticMode,
                isActive: false,
                answers: newAnswers,
                suggestions,
                flowHistory: newHistory,
            });

            // Build comprehensive summary with concept explanations
            const conceptSummary = currentStep?.conceptExplanation
                ? `\n\n**Key Insight:** ${currentStep.conceptExplanation}`
                : '';

            const summaryMessage = `**Socratic Exploration Complete**

Based on your responses, here are insights and suggestions:

${suggestions.map((s, i) => `${i + 1}. ${s}`).join('\n')}${conceptSummary}

Would you like to:
- Explore a related topic (type a follow-up question)
- Run a new analysis with /query
- Review another aspect with /question`;

            onSendMessage(summaryMessage, false);
        } else {
            // Continue to next question
            const nextFlowStep = activeFlow.steps[nextStepIndex];

            // Update highlights for the new step
            if (onHighlightPanels && nextFlowStep.highlightTargets.length > 0) {
                onHighlightPanels(nextFlowStep.highlightTargets);
            }

            setSocraticMode({
                ...socraticMode,
                currentStep: nextStepIndex,
                answers: newAnswers,
                currentFlowStep: nextFlowStep,
                flowHistory: newHistory,
            });

            // Provide feedback on their answer before next question
            const feedbackPrefix = currentStep?.conceptExplanation
                ? `*${currentStep.conceptExplanation.substring(0, 100)}...*\n\n`
                : '';

            const hintText = nextFlowStep.hint ? `\n\n*Hint: ${nextFlowStep.hint}*` : '';
            const phaseLabel = nextFlowStep.phase.charAt(0).toUpperCase() + nextFlowStep.phase.slice(1);

            const nextMessage = `${feedbackPrefix}**Step ${nextStepIndex + 1}/${socraticMode.totalSteps} - ${phaseLabel}:**
${nextFlowStep.question}${hintText}`;

            onSendMessage(nextMessage, false);
        }
    };

    const generateSuggestions = (
        answers: string[],
        flow?: QuestioningFlow,
        lastStep?: QuestioningStep
    ): string[] => {
        const suggestions: string[] = [];

        // Flow-specific suggestions based on the questioning path
        if (flow) {
            switch (flow.id) {
                case 'cynefin-orientation':
                    if (answers.some(a => a.toLowerCase().includes('complex') || a.toLowerCase().includes('emergent'))) {
                        suggestions.push('Your problem shows characteristics of complexity - consider probe-sense-respond approaches');
                    }
                    if (answers.some(a => a.toLowerCase().includes('expert') || a.toLowerCase().includes('analyze'))) {
                        suggestions.push('Expert analysis may help decompose this problem into manageable parts');
                    }
                    break;

                case 'causal-exploration':
                    if (answers.some(a => a.toLowerCase().includes('confounder') || a.toLowerCase().includes('variable'))) {
                        suggestions.push('Consider adding identified confounders to your DAG for more robust estimates');
                    }
                    if (answers.some(a => a.toLowerCase().includes('reverse') || a.toLowerCase().includes('both ways'))) {
                        suggestions.push('Test for reverse causality using temporal data or instrumental variables');
                    }
                    break;

                case 'bayesian-reasoning':
                    if (answers.some(a => a.toLowerCase().includes('uncertain') || a.toLowerCase().includes('unsure'))) {
                        suggestions.push('Use wider priors to reflect uncertainty, then let data drive the posterior');
                    }
                    if (answers.some(a => a.toLowerCase().includes('more data'))) {
                        suggestions.push('Additional data collection could reduce epistemic uncertainty significantly');
                    }
                    break;

                case 'guardian-policies':
                    if (answers.some(a => a.toLowerCase().includes('human') || a.toLowerCase().includes('review'))) {
                        suggestions.push('Consider adding human-in-the-loop checkpoints for high-stakes decisions');
                    }
                    break;
            }
        }

        // Legacy pattern-based suggestions
        if (answers[0]?.length > 20) {
            suggestions.push('Consider narrowing your domain scope for more precise results');
        }
        if (answers.some(a => a.toLowerCase().includes('limited') || a.toLowerCase().includes('few'))) {
            suggestions.push('Collecting more data samples could reduce epistemic uncertainty');
        }
        if (answers.some(a => a.toLowerCase().includes('yes') || a.toLowerCase().includes('possibly'))) {
            suggestions.push('Add identified confounders to your causal model');
        }

        // Include follow-up questions from the last step
        if (lastStep?.followUpQuestions && lastStep.followUpQuestions.length > 0) {
            suggestions.push(`Consider exploring: "${lastStep.followUpQuestions[0]}"`);
        }

        if (suggestions.length === 0) {
            suggestions.push('Your analysis setup looks reasonable');
            suggestions.push('Consider running sensitivity analysis');
        }

        // Deduplicate suggestions
        return [...new Set(suggestions)];
    };

    const [isLoadingChat, setIsLoadingChat] = useState(false);

    const handleSubmit = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!inputValue.trim() || isProcessing || isLoadingChat) return;

        const trimmedInput = inputValue.trim();

        // Check if in Socratic mode
        if (socraticMode.isActive) {
            onSendMessage(trimmedInput, false);
            handleSocraticAnswer(trimmedInput);
            setInputValue('');
            return;
        }

        // Check for slash command
        if (trimmedInput.startsWith('/')) {
            const handled = await processSlashCommand(trimmedInput);
            if (handled) {
                setInputValue('');
                return;
            }
        }

        // Regular message - send to user first, then get AI response
        onSendMessage(trimmedInput, false);
        setInputValue('');

        // Try to get AI response
        setIsLoadingChat(true);
        try {
            const chatMessages = messages.map(m => ({
                role: m.role,
                content: m.content,
            }));
            chatMessages.push({ role: 'user' as const, content: trimmedInput });

            const response = await api.sendChatMessage({
                messages: chatMessages,
                query_context: lastQueryResponse ? {
                    domain: lastQueryResponse.domain,
                    domainConfidence: lastQueryResponse.domainConfidence,
                    causalResult: lastQueryResponse.causalResult,
                    bayesianResult: lastQueryResponse.bayesianResult,
                    guardianResult: lastQueryResponse.guardianResult,
                } : null,
            });

            // Add AI response
            onSendMessage(response.message, false);

            // If there are suggestions, add them as a system message
            if (response.suggestions && response.suggestions.length > 0) {
                const suggestionsText = `**Suggestions:**\n${response.suggestions.map(s => `- ${s}`).join('\n')}`;
                onSendMessage(suggestionsText, true);
            }
        } catch (error) {
            console.warn('Chat API call failed:', error);
            // Fallback: just show a generic response
            onSendMessage('I received your message. How can I help you with your analysis?', false);
        } finally {
            setIsLoadingChat(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (showCommandMenu) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedCommandIndex(i => Math.min(i + 1, filteredCommands.length - 1));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedCommandIndex(i => Math.max(i - 1, 0));
            } else if (e.key === 'Enter' || e.key === 'Tab') {
                e.preventDefault();
                if (filteredCommands[selectedCommandIndex]) {
                    handleCommandSelect(filteredCommands[selectedCommandIndex]);
                }
            } else if (e.key === 'Escape') {
                setShowCommandMenu(false);
            }
        } else if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const getConfidenceColor = (confidence?: string) => {
        switch (confidence) {
            case 'high': return 'bg-green-100 text-green-800';
            case 'medium': return 'bg-yellow-100 text-yellow-800';
            case 'low': return 'bg-red-100 text-red-800';
            default: return '';
        }
    };

    const handleExport = () => {
        const data = {
            exportedAt: new Date().toISOString(),
            messages: messages.map(m => ({
                ...m,
                timestamp: m.timestamp.toISOString(),
            })),
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `carf-chat-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    // Collapsed state
    if (!isExpanded) {
        return (
            <button
                onClick={() => setIsExpanded(true)}
                className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 bg-gradient-to-r from-primary to-accent text-white rounded-full shadow-lg hover:shadow-xl transition-all group"
            >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="font-medium">AI Chat</span>
                {messages.length > 0 && (
                    <span className="w-5 h-5 bg-white text-primary text-xs font-bold rounded-full flex items-center justify-center">
                        {messages.length}
                    </span>
                )}
                {socraticMode.isActive && (
                    <span className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-400 rounded-full animate-pulse" />
                )}
            </button>
        );
    }

    // Expanded state
    return (
        <div className="fixed bottom-6 right-6 z-40 w-[420px] max-h-[550px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 bg-gradient-to-r from-primary to-accent text-white flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    <span className="font-semibold">CARF Intelligent Chat</span>
                    {socraticMode.isActive && (
                        <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">
                            Socratic Mode {socraticMode.currentStep + 1}/{socraticMode.totalSteps}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-1">
                    <button
                        onClick={handleExport}
                        className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                        title="Export conversation"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                    </button>
                    <button
                        onClick={() => setIsExpanded(false)}
                        className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                        title="Minimize"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                        </svg>
                    </button>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-grow overflow-y-auto p-4 space-y-3">
                {messages.length === 0 ? (
                    <div className="text-center text-gray-500 py-6">
                        <svg className="w-10 h-10 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <p className="text-sm font-medium">Intelligent Assistant</p>
                        <p className="text-xs mt-1 mb-3">Type <code className="bg-gray-100 px-1 rounded">/help</code> to see commands</p>
                        <div className="flex flex-wrap gap-2 justify-center">
                            {['/question', '/analysis', '/help'].map(cmd => (
                                <button
                                    key={cmd}
                                    onClick={() => setInputValue(cmd + ' ')}
                                    className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded transition-colors"
                                >
                                    {cmd}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[85%] rounded-2xl px-4 py-2 ${message.role === 'user'
                                    ? 'bg-primary text-white rounded-br-md'
                                    : message.role === 'system'
                                        ? 'bg-blue-50 text-blue-900 border border-blue-200 rounded-bl-md'
                                        : 'bg-gray-100 text-gray-900 rounded-bl-md'
                                    }`}
                            >
                                <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className={`text-xs ${message.role === 'user' ? 'text-white/70' : 'text-gray-500'}`}>
                                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                    {message.isSlashCommand && message.commandType && (
                                        <span className="text-xs bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded">
                                            {message.commandType}
                                        </span>
                                    )}
                                    {message.confidence && (
                                        <span className={`text-xs px-1.5 py-0.5 rounded ${getConfidenceColor(message.confidence)}`}>
                                            {message.confidence}
                                        </span>
                                    )}
                                    {message.linkedPanel && onLinkClick && (
                                        <button
                                            onClick={() => onLinkClick(message.linkedPanel!)}
                                            className={`text-xs underline ${message.role === 'user' ? 'text-white/80' : 'text-primary'}`}
                                        >
                                            View
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))
                )}
                {(isProcessing || isLoadingChat) && (
                    <div className="flex justify-start">
                        <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
                            <div className="flex items-center gap-2">
                                <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                                </div>
                                <span className="text-xs text-gray-500">
                                    {isLoadingChat ? 'AI is thinking...' : 'Processing...'}
                                </span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Command Menu */}
            {showCommandMenu && filteredCommands.length > 0 && (
                <div className="absolute bottom-20 left-3 right-3 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
                    {filteredCommands.map((cmd, index) => (
                        <button
                            key={cmd.command}
                            onClick={() => handleCommandSelect(cmd)}
                            className={`w-full px-3 py-2 text-left hover:bg-gray-50 flex items-center gap-2 ${index === selectedCommandIndex ? 'bg-gray-100' : ''
                                }`}
                        >
                            <code className="text-sm text-primary font-mono">{cmd.command}</code>
                            <span className="text-xs text-gray-500">{cmd.description}</span>
                        </button>
                    ))}
                </div>
            )}

            {/* Input */}
            <form onSubmit={handleSubmit} className="p-3 border-t border-gray-200 flex-shrink-0">
                {socraticMode.isActive && (
                    <div className="mb-2 px-2 py-1 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                        Socratic Mode: Answer the question above or type "skip" to continue
                    </div>
                )}
                <div className="flex items-end gap-2">
                    <textarea
                        ref={inputRef}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={socraticMode.isActive ? "Type your answer..." : "Type / for commands or ask a question..."}
                        disabled={isProcessing || isLoadingChat}
                        className="flex-grow px-3 py-2 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm disabled:bg-gray-50"
                        rows={1}
                        style={{ minHeight: '40px', maxHeight: '100px' }}
                    />
                    <button
                        type="submit"
                        disabled={!inputValue.trim() || isProcessing || isLoadingChat}
                        className="p-2 bg-gradient-to-r from-primary to-accent text-white rounded-xl hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </div>
            </form>
        </div>
    );
};

export default IntelligentChatTab;
