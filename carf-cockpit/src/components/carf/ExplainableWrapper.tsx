/**
 * ExplainableWrapper Component
 *
 * Wraps any component to add right-click explanation functionality.
 * Uses the /explain API to fetch LLM-generated explanations.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useExplanation } from '../../hooks/useCarfApi';
import type { ExplanationComponent } from '../../services/apiService';

interface ExplainableWrapperProps {
    children: React.ReactNode;
    component: ExplanationComponent;
    elementId?: string;
    context?: Record<string, unknown>;
    title?: string;
    disabled?: boolean;
}

interface ContextMenuPosition {
    x: number;
    y: number;
}

const ExplainableWrapper: React.FC<ExplainableWrapperProps> = ({
    children,
    component,
    elementId,
    context,
    title,
    disabled = false,
}) => {
    const [showContextMenu, setShowContextMenu] = useState(false);
    const [menuPosition, setMenuPosition] = useState<ContextMenuPosition>({ x: 0, y: 0 });
    const [showModal, setShowModal] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    const { explanation, loading, error, explain, reset } = useExplanation();

    // Handle right-click
    const handleContextMenu = useCallback((e: React.MouseEvent) => {
        if (disabled) return;

        e.preventDefault();
        e.stopPropagation();

        // Calculate position, ensuring menu stays within viewport
        const x = Math.min(e.clientX, window.innerWidth - 200);
        const y = Math.min(e.clientY, window.innerHeight - 100);

        setMenuPosition({ x, y });
        setShowContextMenu(true);
    }, [disabled]);

    // Handle explain click
    const handleExplain = useCallback(async () => {
        setShowContextMenu(false);
        setShowModal(true);
        await explain(component, elementId, context);
    }, [component, elementId, context, explain]);

    // Close context menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setShowContextMenu(false);
            }
        };

        if (showContextMenu) {
            document.addEventListener('mousedown', handleClickOutside);
            return () => document.removeEventListener('mousedown', handleClickOutside);
        }
    }, [showContextMenu]);

    // Close context menu on escape
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                setShowContextMenu(false);
                setShowModal(false);
            }
        };

        document.addEventListener('keydown', handleEscape);
        return () => document.removeEventListener('keydown', handleEscape);
    }, []);

    const handleCloseModal = useCallback(() => {
        setShowModal(false);
        reset();
    }, [reset]);

    return (
        <>
            <div
                onContextMenu={handleContextMenu}
                className={disabled ? '' : 'cursor-context-menu'}
                title={disabled ? undefined : 'Right-click for explanation'}
            >
                {children}
            </div>

            {/* Context Menu */}
            {showContextMenu && (
                <div
                    ref={menuRef}
                    className="fixed z-50 bg-white rounded-lg shadow-xl border border-gray-200 py-1 min-w-[160px]"
                    style={{ left: menuPosition.x, top: menuPosition.y }}
                >
                    <button
                        onClick={handleExplain}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2"
                    >
                        <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Explain this
                    </button>
                    <button
                        onClick={() => {
                            setShowContextMenu(false);
                            navigator.clipboard.writeText(JSON.stringify({ component, elementId, context }, null, 2));
                        }}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2"
                    >
                        <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        Copy details
                    </button>
                </div>
            )}

            {/* Explanation Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col mx-4">
                        {/* Header */}
                        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-primary/5 to-accent/5">
                            <div className="flex items-center gap-2">
                                <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <h2 className="text-lg font-semibold text-gray-900">
                                    {loading ? 'Loading explanation...' : explanation?.title || title || 'Explanation'}
                                </h2>
                            </div>
                            <button
                                onClick={handleCloseModal}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* Content */}
                        <div className="flex-grow overflow-y-auto p-6">
                            {loading && (
                                <div className="flex items-center justify-center py-12">
                                    <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                                </div>
                            )}

                            {error && (
                                <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
                                    <div className="flex items-center gap-2 text-red-700">
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        <span className="font-medium">Failed to load explanation</span>
                                    </div>
                                    <p className="text-sm text-red-600 mt-1">{error.message}</p>
                                </div>
                            )}

                            {explanation && !loading && (
                                <div className="space-y-4">
                                    {/* Summary */}
                                    <div>
                                        <p className="text-gray-700">{explanation.summary}</p>
                                    </div>

                                    {/* Key Points */}
                                    {explanation.key_points.length > 0 && (
                                        <div>
                                            <h3 className="font-semibold text-gray-900 mb-2">Key Points</h3>
                                            <ul className="space-y-1">
                                                {explanation.key_points.map((point, i) => (
                                                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                                                        <svg className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                        </svg>
                                                        {point}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Implications */}
                                    {explanation.implications && (
                                        <div>
                                            <h3 className="font-semibold text-gray-900 mb-2">Implications</h3>
                                            <p className="text-sm text-gray-600">{explanation.implications}</p>
                                        </div>
                                    )}

                                    {/* Reliability */}
                                    <div className="p-3 bg-gray-50 rounded-lg">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-sm font-medium text-gray-700">Reliability</span>
                                            <span className="text-sm text-gray-500">
                                                {(explanation.reliability_score * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <div className="w-full bg-gray-200 rounded-full h-2">
                                            <div
                                                className={`h-2 rounded-full ${
                                                    explanation.reliability_score >= 0.8
                                                        ? 'bg-green-500'
                                                        : explanation.reliability_score >= 0.5
                                                        ? 'bg-yellow-500'
                                                        : 'bg-red-500'
                                                }`}
                                                style={{ width: `${explanation.reliability_score * 100}%` }}
                                            />
                                        </div>
                                        <p className="text-xs text-gray-500 mt-1">{explanation.reliability}</p>
                                    </div>

                                    {/* Related Concepts */}
                                    {explanation.related_concepts.length > 0 && (
                                        <div>
                                            <h3 className="font-semibold text-gray-900 mb-2">Related Concepts</h3>
                                            <div className="flex flex-wrap gap-2">
                                                {explanation.related_concepts.map((concept, i) => (
                                                    <span
                                                        key={i}
                                                        className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full"
                                                    >
                                                        {concept}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Learn More Links */}
                                    {explanation.learn_more_links.length > 0 && (
                                        <div>
                                            <h3 className="font-semibold text-gray-900 mb-2">Learn More</h3>
                                            <ul className="space-y-1">
                                                {explanation.learn_more_links.map((link, i) => (
                                                    <li key={i}>
                                                        <a
                                                            href={link}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-sm text-primary hover:underline flex items-center gap-1"
                                                        >
                                                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                                            </svg>
                                                            {link}
                                                        </a>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
                            <button
                                onClick={handleCloseModal}
                                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default ExplainableWrapper;
