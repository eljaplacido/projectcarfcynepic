/**
 * ExperienceBufferPanel - Developer view for experience replay tracking
 * 
 * Displays the learning buffer for the CHIMEPIC experience replay system:
 * - Past decisions and outcomes
 * - Correction signals from Guardian/Human
 * - Pattern recognition from similar queries
 */

import React, { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ExperienceEntry {
    id: string;
    timestamp: string;
    query_summary: string;
    domain: string;
    outcome: 'success' | 'failure' | 'corrected';
    correction_source?: 'guardian' | 'human' | 'reflector';
    effect_estimate?: number;
    confidence: number;
    learned_pattern?: string;
}

interface ExperienceBufferProps {
    sessionId?: string;
    maxEntries?: number;
    onApplyLearning?: (pattern: string) => void;
}

const ExperienceBufferPanel: React.FC<ExperienceBufferProps> = ({
    sessionId,
    onApplyLearning,
}) => {
    const [entries, setEntries] = useState<ExperienceEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedEntry, setSelectedEntry] = useState<ExperienceEntry | null>(null);

    const fetchExperiences = useCallback(async () => {
        setLoading(true);
        try {
            // Fetch patterns to get overall buffer data
            const patternsRes = await fetch(`${API_BASE_URL}/experience/patterns`);
            // Fetch similar experiences based on latest query if sessionId available
            const similarRes = await fetch(`${API_BASE_URL}/experience/similar?query=recent+analysis&top_k=10`);

            if (similarRes.ok) {
                const data = await similarRes.json();
                const apiEntries: ExperienceEntry[] = (data.matches || []).map((m: Record<string, unknown>, idx: number) => ({
                    id: `exp-${idx}`,
                    timestamp: m.timestamp as string || new Date().toISOString(),
                    query_summary: (m.query as string || '').slice(0, 80),
                    domain: m.domain as string || 'unknown',
                    outcome: m.guardian_verdict === 'approved' ? 'success' as const
                        : m.guardian_verdict === 'rejected' ? 'corrected' as const
                        : 'success' as const,
                    correction_source: m.guardian_verdict === 'rejected' ? 'guardian' as const : undefined,
                    effect_estimate: m.causal_effect as number | undefined,
                    confidence: m.domain_confidence as number || 0,
                }));

                if (apiEntries.length > 0) {
                    setEntries(apiEntries);
                    return;
                }
            }
        } catch {
            // API unavailable — fall through to demo data
        } finally {
            setLoading(false);
        }

        // Fallback demo data when API is unavailable or returns empty
        setEntries([
            {
                id: 'exp-001',
                timestamp: new Date(Date.now() - 3600000).toISOString(),
                query_summary: 'Scope 3 emissions for EU suppliers',
                domain: 'Complicated',
                outcome: 'success',
                effect_estimate: -75.3,
                confidence: 0.92,
                learned_pattern: 'EU suppliers show strongest program effect',
            },
            {
                id: 'exp-002',
                timestamp: new Date(Date.now() - 7200000).toISOString(),
                query_summary: 'Supply chain disruption risk assessment',
                domain: 'Complex',
                outcome: 'corrected',
                correction_source: 'guardian',
                effect_estimate: 4.2,
                confidence: 0.78,
                learned_pattern: 'Climate stress requires multi-region analysis',
            },
            {
                id: 'exp-003',
                timestamp: new Date(Date.now() - 10800000).toISOString(),
                query_summary: 'Budget approval for program expansion',
                domain: 'Complicated',
                outcome: 'corrected',
                correction_source: 'human',
                confidence: 0.65,
                learned_pattern: 'Budget >$1M requires executive approval',
            },
            {
                id: 'exp-004',
                timestamp: new Date(Date.now() - 14400000).toISOString(),
                query_summary: 'APAC supplier program effectiveness',
                domain: 'Complicated',
                outcome: 'success',
                effect_estimate: -45.8,
                confidence: 0.88,
            },
        ]);
    }, [sessionId]);

    useEffect(() => {
        fetchExperiences();
    }, [fetchExperiences]);

    const getOutcomeIcon = (outcome: ExperienceEntry['outcome']) => {
        switch (outcome) {
            case 'success':
                return '✅';
            case 'failure':
                return '❌';
            case 'corrected':
                return '⚠️';
        }
    };

    const getOutcomeBadge = (entry: ExperienceEntry) => {
        const variants: Record<string, string> = {
            success: 'bg-green-100 text-green-700',
            failure: 'bg-red-100 text-red-700',
            corrected: 'bg-yellow-100 text-yellow-700',
        };

        const label = entry.outcome === 'corrected' && entry.correction_source
            ? `${entry.outcome} by ${entry.correction_source}`
            : entry.outcome;

        return (
            <span className={`px-1.5 py-0.5 rounded text-xs ${variants[entry.outcome]}`}>
                {label}
            </span>
        );
    };

    const formatTime = (isoString: string) => {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);

        if (diffHours < 1) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return date.toLocaleDateString();
    };

    const successRate = entries.length > 0
        ? (entries.filter(e => e.outcome === 'success').length / entries.length * 100).toFixed(0)
        : 0;

    const correctionRate = entries.length > 0
        ? (entries.filter(e => e.outcome === 'corrected').length / entries.length * 100).toFixed(0)
        : 0;

    const patternsLearned = entries.filter(e => e.learned_pattern).length;

    const handleRefresh = () => {
        fetchExperiences();
    };

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            {/* Header */}
            <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                            💾 Experience Buffer
                        </h3>
                        <p className="text-xs text-gray-500 mt-1">
                            Learning from past decisions and corrections
                        </p>
                    </div>
                    <button
                        onClick={handleRefresh}
                        className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 flex items-center gap-1"
                    >
                        <span className={loading ? 'animate-spin' : ''}>🔄</span>
                        Refresh
                    </button>
                </div>
            </div>

            {/* Stats Summary */}
            <div className="grid grid-cols-3 gap-3 p-4 border-b border-gray-200">
                <div className="text-center p-2 bg-gray-50 rounded-lg">
                    <div className="text-xl font-bold text-green-600">{successRate}%</div>
                    <div className="text-xs text-gray-500">Success Rate</div>
                </div>
                <div className="text-center p-2 bg-gray-50 rounded-lg">
                    <div className="text-xl font-bold text-yellow-600">{correctionRate}%</div>
                    <div className="text-xs text-gray-500">Correction Rate</div>
                </div>
                <div className="text-center p-2 bg-gray-50 rounded-lg">
                    <div className="text-xl font-bold text-blue-600">{patternsLearned}</div>
                    <div className="text-xs text-gray-500">Patterns Learned</div>
                </div>
            </div>

            {/* Experience Entries */}
            <div className="p-4">
                <div className="space-y-2 max-h-64 overflow-y-auto">
                    {entries.map((entry) => (
                        <div
                            key={entry.id}
                            className={`p-3 rounded-lg border cursor-pointer transition-colors ${selectedEntry?.id === entry.id
                                    ? 'border-blue-500 bg-blue-50'
                                    : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
                                }`}
                            onClick={() => setSelectedEntry(selectedEntry?.id === entry.id ? null : entry)}
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex items-start gap-2 flex-1 min-w-0">
                                    <span className="flex-shrink-0">{getOutcomeIcon(entry.outcome)}</span>
                                    <div className="min-w-0 flex-1">
                                        <div className="text-xs font-medium text-gray-900 truncate">
                                            {entry.query_summary}
                                        </div>
                                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                                            <span className="px-1.5 py-0.5 text-xs bg-gray-200 text-gray-600 rounded">
                                                {entry.domain}
                                            </span>
                                            <span className="text-xs text-gray-500">{formatTime(entry.timestamp)}</span>
                                            <span className="text-xs text-gray-500">
                                                Conf: {(entry.confidence * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    {getOutcomeBadge(entry)}
                                    <span className="text-gray-400">›</span>
                                </div>
                            </div>

                            {/* Learned Pattern */}
                            {entry.learned_pattern && (
                                <div className="mt-2 p-2 bg-blue-100 rounded text-xs flex items-start gap-2">
                                    <span>🧠</span>
                                    <span className="text-blue-700">{entry.learned_pattern}</span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {/* Selected Entry Details */}
                {selectedEntry && (
                    <div className="mt-4 p-3 bg-gray-100 rounded-lg border border-gray-200">
                        <div className="flex items-center justify-between mb-2">
                            <h4 className="text-xs font-semibold text-gray-900">Entry Details</h4>
                            <button
                                onClick={() => setSelectedEntry(null)}
                                className="text-gray-400 hover:text-gray-600"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                                <span className="text-gray-500">ID:</span>
                                <span className="ml-1 font-mono text-gray-700">{selectedEntry.id}</span>
                            </div>
                            <div>
                                <span className="text-gray-500">Domain:</span>
                                <span className="ml-1 text-gray-700">{selectedEntry.domain}</span>
                            </div>
                            {selectedEntry.effect_estimate !== undefined && (
                                <div>
                                    <span className="text-gray-500">Effect:</span>
                                    <span className="ml-1 font-mono text-gray-700">{selectedEntry.effect_estimate.toFixed(1)} tCO2e</span>
                                </div>
                            )}
                            <div>
                                <span className="text-gray-500">Confidence:</span>
                                <span className="ml-1 text-gray-700">{(selectedEntry.confidence * 100).toFixed(0)}%</span>
                            </div>
                        </div>

                        {selectedEntry.learned_pattern && onApplyLearning && (
                            <button
                                onClick={() => onApplyLearning(selectedEntry.learned_pattern!)}
                                className="w-full mt-3 px-3 py-2 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors flex items-center justify-center gap-1"
                            >
                                🧠 Apply This Learning
                            </button>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ExperienceBufferPanel;
