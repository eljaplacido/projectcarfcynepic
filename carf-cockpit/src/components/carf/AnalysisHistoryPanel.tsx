import React, { useState, useEffect, useCallback, useMemo } from 'react';
import type { AnalysisSession, CynefinDomain } from '../../types/carf';

// localStorage key
const HISTORY_STORAGE_KEY = 'carf-analysis-history';
const MAX_HISTORY_ITEMS = 100;

// Hook for managing analysis history
export const useAnalysisHistory = () => {
    const [history, setHistory] = useState<AnalysisSession[]>([]);

    // Load from localStorage on mount
    useEffect(() => {
        try {
            const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored) as AnalysisSession[];
                setHistory(parsed);
            }
        } catch (error) {
            console.error('Failed to load analysis history:', error);
        }
    }, []);

    // Save analysis session
    const saveAnalysis = useCallback((session: AnalysisSession) => {
        setHistory(prev => {
            const updated = [session, ...prev].slice(0, MAX_HISTORY_ITEMS);
            try {
                localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updated));
            } catch (error) {
                console.error('Failed to save analysis history:', error);
            }
            return updated;
        });
    }, []);

    // Delete analysis session
    const deleteAnalysis = useCallback((sessionId: string) => {
        setHistory(prev => {
            const updated = prev.filter(s => s.id !== sessionId);
            try {
                localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updated));
            } catch (error) {
                console.error('Failed to update analysis history:', error);
            }
            return updated;
        });
    }, []);

    // Clear all history
    const clearHistory = useCallback(() => {
        setHistory([]);
        try {
            localStorage.removeItem(HISTORY_STORAGE_KEY);
        } catch (error) {
            console.error('Failed to clear analysis history:', error);
        }
    }, []);

    return { history, saveAnalysis, deleteAnalysis, clearHistory };
};

interface AnalysisHistoryPanelProps {
    isOpen: boolean;
    onClose: () => void;
    history: AnalysisSession[];
    onViewSession: (session: AnalysisSession) => void;
    onRerunSession: (session: AnalysisSession) => void;
    onDeleteSession: (sessionId: string) => void;
    onClearHistory: () => void;
    onCompare?: (sessionA: AnalysisSession, sessionB: AnalysisSession) => void;
}

const AnalysisHistoryPanel: React.FC<AnalysisHistoryPanelProps> = ({
    isOpen,
    onClose,
    history,
    onViewSession,
    onRerunSession,
    onDeleteSession,
    onClearHistory,
    onCompare,
}) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [domainFilter, setDomainFilter] = useState<CynefinDomain | 'all'>('all');
    const [dateFilter, setDateFilter] = useState<'all' | 'today' | 'week' | 'month'>('all');
    const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
    const [showClearConfirm, setShowClearConfirm] = useState(false);

    // Filter history based on search and filters
    const filteredHistory = useMemo(() => {
        return history.filter(session => {
            // Search filter
            if (searchQuery) {
                const query = searchQuery.toLowerCase();
                if (!session.query.toLowerCase().includes(query) &&
                    !session.domain.toLowerCase().includes(query)) {
                    return false;
                }
            }

            // Domain filter
            if (domainFilter !== 'all' && session.domain !== domainFilter) {
                return false;
            }

            // Date filter
            if (dateFilter !== 'all') {
                const sessionDate = new Date(session.timestamp);
                const now = new Date();
                const daysDiff = Math.floor((now.getTime() - sessionDate.getTime()) / (1000 * 60 * 60 * 24));

                if (dateFilter === 'today' && daysDiff > 0) return false;
                if (dateFilter === 'week' && daysDiff > 7) return false;
                if (dateFilter === 'month' && daysDiff > 30) return false;
            }

            return true;
        });
    }, [history, searchQuery, domainFilter, dateFilter]);

    const toggleCompareSelection = (sessionId: string) => {
        setSelectedForCompare(prev => {
            if (prev.includes(sessionId)) {
                return prev.filter(id => id !== sessionId);
            }
            if (prev.length >= 2) {
                return [prev[1], sessionId];
            }
            return [...prev, sessionId];
        });
    };

    const handleCompare = () => {
        if (selectedForCompare.length === 2 && onCompare) {
            const sessionA = history.find(s => s.id === selectedForCompare[0]);
            const sessionB = history.find(s => s.id === selectedForCompare[1]);
            if (sessionA && sessionB) {
                onCompare(sessionA, sessionB);
            }
        }
    };

    const exportHistory = () => {
        const data = {
            exportedAt: new Date().toISOString(),
            totalSessions: history.length,
            sessions: history,
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `carf-history-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const formatRelativeTime = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    const getDomainColor = (domain: CynefinDomain) => {
        const colors: Record<CynefinDomain, string> = {
            clear: 'bg-green-100 text-green-800',
            complicated: 'bg-blue-100 text-blue-800',
            complex: 'bg-purple-100 text-purple-800',
            chaotic: 'bg-red-100 text-red-800',
            disorder: 'bg-gray-100 text-gray-800',
        };
        return colors[domain] || 'bg-gray-100 text-gray-800';
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white rounded-2xl shadow-2xl w-[700px] max-h-[80vh] flex flex-col overflow-hidden">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
                    <div className="flex items-center gap-3">
                        <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <h2 className="text-xl font-semibold text-gray-900">Analysis History</h2>
                        <span className="text-sm text-gray-500">({filteredHistory.length} of {history.length})</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={exportHistory}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            title="Export history"
                        >
                            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                        </button>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Filters */}
                <div className="px-6 py-3 border-b border-gray-100 flex items-center gap-3 flex-shrink-0">
                    {/* Search */}
                    <div className="flex-grow relative">
                        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Search queries..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                        />
                    </div>

                    {/* Domain filter */}
                    <select
                        value={domainFilter}
                        onChange={(e) => setDomainFilter(e.target.value as CynefinDomain | 'all')}
                        className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                        <option value="all">All Domains</option>
                        <option value="clear">Clear</option>
                        <option value="complicated">Complicated</option>
                        <option value="complex">Complex</option>
                        <option value="chaotic">Chaotic</option>
                        <option value="disorder">Disorder</option>
                    </select>

                    {/* Date filter */}
                    <select
                        value={dateFilter}
                        onChange={(e) => setDateFilter(e.target.value as typeof dateFilter)}
                        className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                        <option value="all">All Time</option>
                        <option value="today">Today</option>
                        <option value="week">This Week</option>
                        <option value="month">This Month</option>
                    </select>

                    {/* Compare button */}
                    {onCompare && selectedForCompare.length === 2 && (
                        <button
                            onClick={handleCompare}
                            className="px-3 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-light transition-colors"
                        >
                            Compare ({selectedForCompare.length})
                        </button>
                    )}
                </div>

                {/* History List */}
                <div className="flex-grow overflow-y-auto p-4">
                    {filteredHistory.length === 0 ? (
                        <div className="text-center py-12">
                            <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            <p className="text-gray-500 text-lg">No analyses found</p>
                            <p className="text-gray-400 text-sm mt-1">
                                {history.length === 0
                                    ? 'Run your first analysis to see it here'
                                    : 'Try adjusting your filters'}
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {filteredHistory.map((session) => (
                                <div
                                    key={session.id}
                                    className={`border rounded-xl p-4 hover:border-primary/50 transition-colors ${
                                        selectedForCompare.includes(session.id)
                                            ? 'border-primary bg-primary/5'
                                            : 'border-gray-200'
                                    }`}
                                >
                                    {/* Session Header */}
                                    <div className="flex items-start justify-between mb-2">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-gray-500">
                                                {formatRelativeTime(session.timestamp)}
                                            </span>
                                            <span className={`text-xs px-2 py-0.5 rounded-full ${getDomainColor(session.domain)}`}>
                                                {session.domain}
                                            </span>
                                            <span className="text-xs text-gray-500">
                                                {(session.confidence * 100).toFixed(0)}% conf
                                            </span>
                                        </div>
                                        {onCompare && (
                                            <button
                                                onClick={() => toggleCompareSelection(session.id)}
                                                className={`p-1 rounded transition-colors ${
                                                    selectedForCompare.includes(session.id)
                                                        ? 'bg-primary text-white'
                                                        : 'hover:bg-gray-100 text-gray-400'
                                                }`}
                                                title="Select for comparison"
                                            >
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                                </svg>
                                            </button>
                                        )}
                                    </div>

                                    {/* Query Text */}
                                    <p className="text-sm text-gray-900 font-medium mb-2 line-clamp-2">
                                        "{session.query}"
                                    </p>

                                    {/* Results Summary */}
                                    <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                                        {session.result.causalResult && (
                                            <span>
                                                Effect: {session.result.causalResult.effect.toFixed(2)}
                                            </span>
                                        )}
                                        {session.result.causalResult && (
                                            <span>
                                                Refutations: {session.result.causalResult.refutationsPassed}/{session.result.causalResult.refutationsTotal}
                                            </span>
                                        )}
                                        <span>
                                            Duration: {session.duration}ms
                                        </span>
                                    </div>

                                    {/* Tags */}
                                    {session.tags && session.tags.length > 0 && (
                                        <div className="flex flex-wrap gap-1 mb-3">
                                            {session.tags.map(tag => (
                                                <span
                                                    key={tag}
                                                    className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded"
                                                >
                                                    {tag}
                                                </span>
                                            ))}
                                        </div>
                                    )}

                                    {/* Actions */}
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => onViewSession(session)}
                                            className="px-3 py-1.5 text-xs font-medium text-primary border border-primary rounded-lg hover:bg-primary hover:text-white transition-colors"
                                        >
                                            View
                                        </button>
                                        <button
                                            onClick={() => onRerunSession(session)}
                                            className="px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
                                        >
                                            Rerun
                                        </button>
                                        <button
                                            onClick={() => onDeleteSession(session.id)}
                                            className="px-3 py-1.5 text-xs font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
                                        >
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-3 border-t border-gray-200 flex items-center justify-between flex-shrink-0">
                    <div className="text-xs text-gray-500">
                        Stored locally in browser. Max {MAX_HISTORY_ITEMS} sessions.
                    </div>
                    {history.length > 0 && (
                        <div className="relative">
                            {showClearConfirm ? (
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-gray-600">Clear all history?</span>
                                    <button
                                        onClick={() => {
                                            onClearHistory();
                                            setShowClearConfirm(false);
                                        }}
                                        className="px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 rounded transition-colors"
                                    >
                                        Yes, clear
                                    </button>
                                    <button
                                        onClick={() => setShowClearConfirm(false)}
                                        className="px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded transition-colors"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            ) : (
                                <button
                                    onClick={() => setShowClearConfirm(true)}
                                    className="text-xs text-red-500 hover:text-red-700 transition-colors"
                                >
                                    Clear All
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default AnalysisHistoryPanel;
