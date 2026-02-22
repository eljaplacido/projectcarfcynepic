/**
 * PolicyIngestionPanel — Extract governance rules from unstructured text.
 *
 * Textarea for pasting policy text, extraction via LLM, preview and accept extracted rules.
 */

import React, { useState } from 'react';
import type { GovernanceDomain } from '../../types/carf';
import {
    extractPoliciesFromText,
    createFederatedPolicy,
    getGovernanceDomains,
} from '../../services/apiService';

interface ExtractedRule {
    name: string;
    condition: Record<string, unknown>;
    constraint: Record<string, unknown>;
    message: string;
    severity: string;
    accepted: boolean;
}

interface PolicyIngestionPanelProps {
    onRulesAdded?: () => void;
}

const SEVERITY_COLORS: Record<string, string> = {
    critical: '#EF4444',
    high: '#F97316',
    medium: '#F59E0B',
    low: '#10B981',
};

const PolicyIngestionPanel: React.FC<PolicyIngestionPanelProps> = ({ onRulesAdded }) => {
    const [text, setText] = useState('');
    const [sourceName, setSourceName] = useState('');
    const [targetDomain, setTargetDomain] = useState('');
    const [domains, setDomains] = useState<GovernanceDomain[]>([]);
    const [extractedRules, setExtractedRules] = useState<ExtractedRule[]>([]);
    const [extracting, setExtracting] = useState(false);
    const [adding, setAdding] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [domainsLoaded, setDomainsLoaded] = useState(false);

    const loadDomains = async () => {
        if (domainsLoaded) return;
        try {
            const d = await getGovernanceDomains();
            setDomains(d);
            setDomainsLoaded(true);
        } catch {
            // Governance may not be enabled
        }
    };

    const handleExtract = async () => {
        if (!text.trim()) return;
        setExtracting(true);
        setError(null);
        setExtractedRules([]);
        await loadDomains();

        try {
            const result = await extractPoliciesFromText(
                text,
                sourceName || 'pasted_text',
                targetDomain || undefined
            );
            if (result.error) {
                setError(result.error);
            }
            setExtractedRules(
                result.rules.map(r => ({ ...r, accepted: true }))
            );
        } catch (err) {
            setError(String(err));
        } finally {
            setExtracting(false);
        }
    };

    const toggleRule = (index: number) => {
        setExtractedRules(prev =>
            prev.map((r, i) => i === index ? { ...r, accepted: !r.accepted } : r)
        );
    };

    const handleAddSelected = async () => {
        const accepted = extractedRules.filter(r => r.accepted);
        if (accepted.length === 0) return;

        setAdding(true);
        try {
            const domain = targetDomain || 'legal';
            const policyName = sourceName || 'Extracted Policy';
            const namespace = `${domain}.extracted_${Date.now()}`;

            await createFederatedPolicy({
                name: policyName,
                domain_id: domain,
                namespace,
                description: `Rules extracted from: ${sourceName || 'pasted text'}`,
                rules: accepted.map(r => ({
                    name: r.name,
                    condition: r.condition,
                    constraint: r.constraint,
                    message: r.message,
                    severity: r.severity,
                })),
                priority: 50,
                is_active: true,
            });

            setExtractedRules([]);
            setText('');
            onRulesAdded?.();
        } catch (err) {
            setError(String(err));
        } finally {
            setAdding(false);
        }
    };

    const acceptedCount = extractedRules.filter(r => r.accepted).length;

    return (
        <div style={{
            padding: '16px', backgroundColor: '#1F2937', borderRadius: '8px',
            border: '1px solid #374151',
        }}>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#D1D5DB', marginBottom: '12px' }}>
                Policy Text Extraction
            </div>

            {/* Input Area */}
            <div style={{ marginBottom: '12px' }}>
                <textarea
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder="Paste policy text, regulatory guidelines, or compliance requirements here..."
                    rows={6}
                    style={{
                        width: '100%', padding: '10px', borderRadius: '6px',
                        border: '1px solid #374151', backgroundColor: '#111827',
                        color: '#E5E7EB', fontSize: '13px', resize: 'vertical',
                        fontFamily: 'inherit',
                    }}
                />
            </div>

            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>
                        Source Name
                    </label>
                    <input
                        value={sourceName}
                        onChange={e => setSourceName(e.target.value)}
                        placeholder="e.g., EU AI Act Art.9"
                        style={{
                            width: '100%', padding: '8px', borderRadius: '6px',
                            border: '1px solid #374151', backgroundColor: '#111827',
                            color: '#E5E7EB', fontSize: '12px',
                        }}
                    />
                </div>
                <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>
                        Target Domain (optional)
                    </label>
                    <select
                        value={targetDomain}
                        onChange={e => setTargetDomain(e.target.value)}
                        onFocus={loadDomains}
                        style={{
                            width: '100%', padding: '8px', borderRadius: '6px',
                            border: '1px solid #374151', backgroundColor: '#111827',
                            color: '#E5E7EB', fontSize: '12px',
                        }}
                    >
                        <option value="">Auto-detect</option>
                        {domains.map(d => (
                            <option key={d.domain_id} value={d.domain_id}>{d.display_name}</option>
                        ))}
                    </select>
                </div>
                <button
                    onClick={handleExtract}
                    disabled={extracting || !text.trim()}
                    style={{
                        padding: '8px 20px', borderRadius: '6px', border: 'none',
                        backgroundColor: '#3B82F6', color: '#fff',
                        cursor: extracting || !text.trim() ? 'not-allowed' : 'pointer',
                        fontSize: '12px', fontWeight: 600, whiteSpace: 'nowrap',
                        opacity: extracting || !text.trim() ? 0.5 : 1,
                    }}
                >
                    {extracting ? 'Extracting...' : 'Extract Rules'}
                </button>
            </div>

            {error && (
                <div style={{
                    padding: '8px 12px', marginBottom: '12px', borderRadius: '6px',
                    backgroundColor: '#EF444422', color: '#EF4444', fontSize: '12px',
                }}>
                    {error}
                </div>
            )}

            {/* Extracted Rules Preview */}
            {extractedRules.length > 0 && (
                <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '8px' }}>
                        Extracted Rules ({extractedRules.length})
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
                        {extractedRules.map((rule, idx) => (
                            <div key={idx} style={{
                                padding: '10px', borderRadius: '6px',
                                backgroundColor: '#111827',
                                border: `1px solid ${rule.accepted ? '#374151' : '#37415155'}`,
                                opacity: rule.accepted ? 1 : 0.5,
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <button
                                            onClick={() => toggleRule(idx)}
                                            style={{
                                                width: '18px', height: '18px', borderRadius: '4px',
                                                border: `2px solid ${rule.accepted ? '#10B981' : '#6B7280'}`,
                                                backgroundColor: rule.accepted ? '#10B981' : 'transparent',
                                                cursor: 'pointer', display: 'flex',
                                                alignItems: 'center', justifyContent: 'center',
                                                color: '#fff', fontSize: '10px',
                                            }}
                                        >
                                            {rule.accepted ? 'v' : ''}
                                        </button>
                                        <span style={{ fontWeight: 600, color: '#E5E7EB', fontSize: '12px' }}>
                                            {rule.name}
                                        </span>
                                    </div>
                                    <span style={{
                                        fontSize: '10px', padding: '2px 6px', borderRadius: '3px',
                                        backgroundColor: `${SEVERITY_COLORS[rule.severity] || '#6B7280'}22`,
                                        color: SEVERITY_COLORS[rule.severity] || '#6B7280',
                                        fontWeight: 600,
                                    }}>
                                        {rule.severity}
                                    </span>
                                </div>
                                <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '4px' }}>
                                    {rule.message}
                                </div>
                                {Object.keys(rule.condition).length > 0 && (
                                    <div style={{ fontSize: '10px', color: '#6B7280', marginTop: '4px' }}>
                                        Conditions: {JSON.stringify(rule.condition)}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                            onClick={handleAddSelected}
                            disabled={adding || acceptedCount === 0}
                            style={{
                                padding: '8px 16px', borderRadius: '6px', border: 'none',
                                backgroundColor: '#10B981', color: '#fff',
                                cursor: adding || acceptedCount === 0 ? 'not-allowed' : 'pointer',
                                fontSize: '12px', fontWeight: 600,
                                opacity: adding || acceptedCount === 0 ? 0.5 : 1,
                            }}
                        >
                            {adding ? 'Adding...' : `Add ${acceptedCount} Selected`}
                        </button>
                        <button
                            onClick={() => setExtractedRules([])}
                            style={{
                                padding: '8px 16px', borderRadius: '6px',
                                border: '1px solid #374151', backgroundColor: 'transparent',
                                color: '#9CA3AF', cursor: 'pointer', fontSize: '12px',
                            }}
                        >
                            Clear
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PolicyIngestionPanel;
