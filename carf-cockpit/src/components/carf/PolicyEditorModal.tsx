/**
 * Policy Editor Modal
 *
 * Full-screen modal for managing CSL policies and rules.
 * Provides CRUD operations for policy rules with a visual editor.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
    getCSLStatus,
    getCSLPolicies,
    addCSLRule,
    evaluateCSLPolicy,
    reloadCSLPolicies,
    type CSLPolicyDetail,
    type CSLStatus,
    type CSLEvaluationResult,
} from '../../services/apiService';

interface PolicyEditorModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const PolicyEditorModal: React.FC<PolicyEditorModalProps> = ({ isOpen, onClose }) => {
    const [status, setStatus] = useState<CSLStatus | null>(null);
    const [policies, setPolicies] = useState<CSLPolicyDetail[]>([]);
    const [selectedPolicy, setSelectedPolicy] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Add rule form state
    const [showAddRule, setShowAddRule] = useState(false);
    const [newRuleNL, setNewRuleNL] = useState('');
    const [addingRule, setAddingRule] = useState(false);

    // Test evaluation state
    const [testResult, setTestResult] = useState<CSLEvaluationResult | null>(null);
    const [testing, setTesting] = useState(false);

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const [statusData, policiesData] = await Promise.all([
                getCSLStatus(),
                getCSLPolicies(),
            ]);
            setStatus(statusData);
            setPolicies(policiesData);
            if (!selectedPolicy && policiesData.length > 0) {
                setSelectedPolicy(policiesData[0].name);
            }
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load policies');
        } finally {
            setLoading(false);
        }
    }, [selectedPolicy]);

    useEffect(() => {
        if (isOpen) {
            fetchData();
        }
    }, [isOpen, fetchData]);

    const currentPolicy = policies.find(p => p.name === selectedPolicy);

    const handleAddRule = async () => {
        if (!selectedPolicy || !newRuleNL.trim()) return;
        setAddingRule(true);
        try {
            await addCSLRule(selectedPolicy, newRuleNL.trim());
            setNewRuleNL('');
            setShowAddRule(false);
            await fetchData();
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to add rule');
        } finally {
            setAddingRule(false);
        }
    };

    const handleTestPolicy = async () => {
        if (!selectedPolicy) return;
        setTesting(true);
        try {
            const sampleContext = {
                'domain.type': 'Complicated',
                'domain.confidence': 0.85,
                'action.type': 'transfer',
                'action.amount': 5000,
                'user.role': 'junior',
                'risk.level': 'LOW',
                'approval.status': '',
                'approval.escalated': false,
                'prediction.source': 'causal',
                'prediction.effect_size': 0.5,
                'prediction.confidence': 0.85,
                'data.contains_pii': false,
                'data.is_masked': false,
            };
            const result = await evaluateCSLPolicy(selectedPolicy, sampleContext);
            setTestResult(result);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to evaluate policy');
        } finally {
            setTesting(false);
        }
    };

    const handleReload = async () => {
        try {
            await reloadCSLPolicies();
            await fetchData();
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to reload policies');
        }
    };

    const formatCondition = (condition: Record<string, unknown>): string => {
        const entries = Object.entries(condition);
        if (entries.length === 0) return 'Always applies';
        return entries.map(([k, v]) => `${k} = ${JSON.stringify(v)}`).join(' AND ');
    };

    const formatConstraint = (constraint: Record<string, unknown>): string => {
        return Object.entries(constraint).map(([k, v]) => {
            if (typeof v === 'object' && v !== null) {
                const obj = v as Record<string, unknown>;
                const parts = [];
                if ('min' in obj) parts.push(`${k} >= ${obj.min}`);
                if ('max' in obj) parts.push(`${k} <= ${obj.max}`);
                if ('eq' in obj) parts.push(`${k} == ${obj.eq}`);
                if ('neq' in obj) parts.push(`${k} != ${obj.neq}`);
                return parts.join(', ');
            }
            if (typeof v === 'boolean') return `${k} must be ${v}`;
            if (typeof v === 'number') return `${k} <= ${v}`;
            return `${k} = ${JSON.stringify(v)}`;
        }).join('; ');
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="bg-white dark:bg-gray-900 rounded-xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                    <div>
                        <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
                            Policy Configuration
                        </h2>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {status ? `${status.engine} engine — ${status.policy_count} policies, ${status.rule_count} rules` : 'Loading...'}
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleReload}
                            className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                        >
                            Reload
                        </button>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Error banner */}
                {error && (
                    <div className="mx-6 mt-3 p-2 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded text-xs text-red-700 dark:text-red-300 flex justify-between">
                        <span>{error}</span>
                        <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700 ml-2">✕</button>
                    </div>
                )}

                {/* Body */}
                <div className="flex flex-1 overflow-hidden">
                    {/* Sidebar: policy list */}
                    <div className="w-56 border-r border-gray-200 dark:border-gray-700 overflow-y-auto p-4 space-y-1">
                        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Policies</h3>
                        {policies.map(policy => (
                            <button
                                key={policy.name}
                                onClick={() => { setSelectedPolicy(policy.name); setTestResult(null); }}
                                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                                    selectedPolicy === policy.name
                                        ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200 font-medium'
                                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                                }`}
                            >
                                <div className="font-medium">{policy.name.replace(/_/g, ' ')}</div>
                                <div className="text-[10px] text-gray-500 dark:text-gray-400">{policy.rules?.length ?? 0} rules</div>
                            </button>
                        ))}
                    </div>

                    {/* Main: rules for selected policy */}
                    <div className="flex-1 overflow-y-auto p-6">
                        {loading ? (
                            <div className="flex items-center justify-center h-40 text-gray-500">Loading policies...</div>
                        ) : currentPolicy ? (
                            <>
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <h3 className="text-base font-bold text-gray-900 dark:text-gray-100">
                                            {currentPolicy.name.replace(/_/g, ' ')}
                                        </h3>
                                        <p className="text-xs text-gray-500 dark:text-gray-400">{currentPolicy.description} — v{currentPolicy.version}</p>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={handleTestPolicy}
                                            disabled={testing}
                                            className="text-xs px-3 py-1.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-200 dark:hover:bg-purple-800 transition-colors disabled:opacity-50"
                                        >
                                            {testing ? 'Testing...' : 'Test Policy'}
                                        </button>
                                        <button
                                            onClick={() => setShowAddRule(!showAddRule)}
                                            className="text-xs px-3 py-1.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                                        >
                                            + Add Rule
                                        </button>
                                    </div>
                                </div>

                                {/* Test result */}
                                {testResult && (
                                    <div className={`mb-4 p-3 rounded-lg border text-sm ${
                                        testResult.allow
                                            ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-800 dark:text-green-200'
                                            : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-800 dark:text-red-200'
                                    }`}>
                                        <div className="font-medium mb-1">
                                            {testResult.allow ? '✓ All checks passed' : `✗ ${testResult.rules_failed} violation(s)`}
                                        </div>
                                        <div className="text-xs">
                                            Checked {testResult.rules_checked} rules — {testResult.rules_passed} passed, {testResult.rules_failed} failed
                                        </div>
                                        {testResult.violations.length > 0 && (
                                            <ul className="mt-2 space-y-1">
                                                {testResult.violations.map((v, i) => (
                                                    <li key={i} className="text-xs">• {v.rule_name}: {v.message}</li>
                                                ))}
                                            </ul>
                                        )}
                                        <button onClick={() => setTestResult(null)} className="text-xs mt-2 underline opacity-60 hover:opacity-100">Dismiss</button>
                                    </div>
                                )}

                                {/* Add rule form */}
                                {showAddRule && (
                                    <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                                        <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-200 mb-2">Add Rule (Natural Language)</h4>
                                        <p className="text-xs text-blue-700 dark:text-blue-300 mb-2">
                                            Describe the rule in plain English, e.g. "Block transfers over $5000 for junior users"
                                        </p>
                                        <div className="flex gap-2">
                                            <input
                                                type="text"
                                                value={newRuleNL}
                                                onChange={e => setNewRuleNL(e.target.value)}
                                                placeholder="e.g., Require approval for exports exceeding $10,000"
                                                className="flex-1 text-sm px-3 py-2 border border-blue-300 dark:border-blue-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-400 outline-none"
                                                onKeyDown={e => e.key === 'Enter' && handleAddRule()}
                                            />
                                            <button
                                                onClick={handleAddRule}
                                                disabled={addingRule || !newRuleNL.trim()}
                                                className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors disabled:opacity-50"
                                            >
                                                {addingRule ? 'Adding...' : 'Add'}
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {/* Rules list */}
                                <div className="space-y-3">
                                    {currentPolicy.rules.map((rule, idx) => (
                                        <div
                                            key={`${rule.name}-${idx}`}
                                            className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 transition-colors"
                                        >
                                            <div className="flex items-start justify-between mb-2">
                                                <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                                                    {rule.name.replace(/_/g, ' ')}
                                                </h4>
                                            </div>
                                            <div className="space-y-1.5 text-xs">
                                                <div>
                                                    <span className="font-medium text-gray-600 dark:text-gray-400">When: </span>
                                                    <span className="text-gray-800 dark:text-gray-200 font-mono bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
                                                        {formatCondition(rule.condition)}
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="font-medium text-gray-600 dark:text-gray-400">Then: </span>
                                                    <span className="text-gray-800 dark:text-gray-200 font-mono bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
                                                        {formatConstraint(rule.constraint)}
                                                    </span>
                                                </div>
                                                {rule.message && (
                                                    <div className="text-gray-500 dark:text-gray-400 italic mt-1">
                                                        {rule.message}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </>
                        ) : (
                            <div className="flex items-center justify-center h-40 text-gray-500">
                                Select a policy from the sidebar
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PolicyEditorModal;
