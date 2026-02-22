/**
 * PolicyEditorModal — Create/Edit federated governance policy.
 *
 * Modal with form for policy details and rule builder.
 */

import React, { useState, useEffect } from 'react';
import type { FederatedPolicyInfo, GovernanceDomain } from '../../types/carf';
import {
    createFederatedPolicy,
    updateFederatedPolicy,
    getGovernanceDomains,
} from '../../services/apiService';

interface PolicyEditorModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSaved: () => void;
    editPolicy?: FederatedPolicyInfo | null;
}

interface RuleFormData {
    name: string;
    condition: Array<{ key: string; value: string }>;
    constraint: Array<{ key: string; value: string }>;
    message: string;
    severity: string;
}

const SEVERITIES = ['critical', 'high', 'medium', 'low'];

const emptyRule = (): RuleFormData => ({
    name: '',
    condition: [{ key: '', value: '' }],
    constraint: [{ key: '', value: '' }],
    message: '',
    severity: 'medium',
});

function kvToDict(pairs: Array<{ key: string; value: string }>): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const { key, value } of pairs) {
        if (!key) continue;
        if (value === 'true') result[key] = true;
        else if (value === 'false') result[key] = false;
        else if (!isNaN(Number(value)) && value !== '') result[key] = Number(value);
        else result[key] = value;
    }
    return result;
}

function dictToKv(dict: Record<string, unknown>): Array<{ key: string; value: string }> {
    const pairs = Object.entries(dict).map(([key, value]) => ({
        key,
        value: String(value),
    }));
    return pairs.length > 0 ? pairs : [{ key: '', value: '' }];
}

const PolicyEditorModal: React.FC<PolicyEditorModalProps> = ({
    isOpen,
    onClose,
    onSaved,
    editPolicy,
}) => {
    const [domains, setDomains] = useState<GovernanceDomain[]>([]);
    const [name, setName] = useState('');
    const [domainId, setDomainId] = useState('');
    const [namespace, setNamespace] = useState('');
    const [description, setDescription] = useState('');
    const [priority, setPriority] = useState(50);
    const [isActive, setIsActive] = useState(true);
    const [rules, setRules] = useState<RuleFormData[]>([emptyRule()]);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            getGovernanceDomains().then(setDomains).catch(() => {});
        }
    }, [isOpen]);

    useEffect(() => {
        if (editPolicy) {
            setName(editPolicy.name);
            setDomainId(editPolicy.domain_id);
            setNamespace(editPolicy.namespace);
            setDescription(editPolicy.description);
            setPriority(editPolicy.priority);
            setIsActive(editPolicy.is_active);
            setRules(
                editPolicy.rules.length > 0
                    ? editPolicy.rules.map(r => ({
                        name: r.name,
                        condition: dictToKv(r.condition as Record<string, unknown>),
                        constraint: dictToKv(r.constraint as Record<string, unknown>),
                        message: r.message,
                        severity: r.severity,
                    }))
                    : [emptyRule()]
            );
        } else {
            setName('');
            setDomainId('');
            setNamespace('');
            setDescription('');
            setPriority(50);
            setIsActive(true);
            setRules([emptyRule()]);
        }
        setError(null);
    }, [editPolicy, isOpen]);

    useEffect(() => {
        if (!editPolicy && domainId && name) {
            setNamespace(`${domainId}.${name.toLowerCase().replace(/\s+/g, '_')}`);
        }
    }, [domainId, name, editPolicy]);

    const handleAddRule = () => setRules(prev => [...prev, emptyRule()]);

    const handleRemoveRule = (index: number) => {
        setRules(prev => prev.filter((_, i) => i !== index));
    };

    const updateRule = (index: number, field: string, value: unknown) => {
        setRules(prev => prev.map((r, i) => i === index ? { ...r, [field]: value } : r));
    };

    const addKVPair = (ruleIndex: number, field: 'condition' | 'constraint') => {
        setRules(prev => prev.map((r, i) =>
            i === ruleIndex ? { ...r, [field]: [...r[field], { key: '', value: '' }] } : r
        ));
    };

    const updateKVPair = (
        ruleIndex: number,
        field: 'condition' | 'constraint',
        pairIndex: number,
        pairField: 'key' | 'value',
        value: string
    ) => {
        setRules(prev => prev.map((r, i) => {
            if (i !== ruleIndex) return r;
            const pairs = [...r[field]];
            pairs[pairIndex] = { ...pairs[pairIndex], [pairField]: value };
            return { ...r, [field]: pairs };
        }));
    };

    const handleSave = async () => {
        if (!name || !domainId || !namespace) {
            setError('Name, domain, and namespace are required.');
            return;
        }

        setSaving(true);
        setError(null);
        try {
            const policyRules = rules
                .filter(r => r.name)
                .map(r => ({
                    name: r.name,
                    condition: kvToDict(r.condition),
                    constraint: kvToDict(r.constraint),
                    message: r.message,
                    severity: r.severity,
                }));

            if (editPolicy) {
                await updateFederatedPolicy(editPolicy.namespace, {
                    description,
                    priority,
                    is_active: isActive,
                });
            } else {
                await createFederatedPolicy({
                    name,
                    domain_id: domainId,
                    namespace,
                    description,
                    rules: policyRules,
                    priority,
                    is_active: isActive,
                });
            }
            onSaved();
            onClose();
        } catch (err) {
            setError(String(err));
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            backgroundColor: 'rgba(0,0,0,0.6)',
        }}>
            <div style={{
                width: '700px', maxHeight: '85vh', overflowY: 'auto',
                backgroundColor: '#111827', borderRadius: '12px',
                border: '1px solid #374151', padding: '24px',
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#E5E7EB', margin: 0 }}>
                        {editPolicy ? 'Edit Policy' : 'Create Policy'}
                    </h2>
                    <button onClick={onClose} style={{
                        background: 'none', border: 'none', color: '#9CA3AF',
                        fontSize: '18px', cursor: 'pointer',
                    }}>x</button>
                </div>

                {error && (
                    <div style={{ padding: '8px 12px', marginBottom: '12px', borderRadius: '6px', backgroundColor: '#EF444422', color: '#EF4444', fontSize: '12px' }}>
                        {error}
                    </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                    <div>
                        <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>Name</label>
                        <input
                            value={name}
                            onChange={e => setName(e.target.value)}
                            disabled={!!editPolicy}
                            style={{
                                width: '100%', padding: '8px', borderRadius: '6px',
                                border: '1px solid #374151', backgroundColor: '#1F2937',
                                color: '#E5E7EB', fontSize: '13px',
                            }}
                        />
                    </div>
                    <div>
                        <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>Domain</label>
                        <select
                            value={domainId}
                            onChange={e => setDomainId(e.target.value)}
                            disabled={!!editPolicy}
                            style={{
                                width: '100%', padding: '8px', borderRadius: '6px',
                                border: '1px solid #374151', backgroundColor: '#1F2937',
                                color: '#E5E7EB', fontSize: '13px',
                            }}
                        >
                            <option value="">Select domain...</option>
                            {domains.map(d => (
                                <option key={d.domain_id} value={d.domain_id}>{d.display_name}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>Namespace</label>
                        <input
                            value={namespace}
                            onChange={e => setNamespace(e.target.value)}
                            disabled={!!editPolicy}
                            style={{
                                width: '100%', padding: '8px', borderRadius: '6px',
                                border: '1px solid #374151', backgroundColor: '#1F2937',
                                color: '#E5E7EB', fontSize: '13px',
                            }}
                        />
                    </div>
                    <div>
                        <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>
                            Priority: {priority}
                        </label>
                        <input
                            type="range" min={0} max={100} value={priority}
                            onChange={e => setPriority(Number(e.target.value))}
                            style={{ width: '100%' }}
                        />
                    </div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                    <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>Description</label>
                    <textarea
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        rows={2}
                        style={{
                            width: '100%', padding: '8px', borderRadius: '6px',
                            border: '1px solid #374151', backgroundColor: '#1F2937',
                            color: '#E5E7EB', fontSize: '13px', resize: 'vertical',
                        }}
                    />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <label style={{ fontSize: '11px', color: '#9CA3AF' }}>Active</label>
                    <button
                        onClick={() => setIsActive(!isActive)}
                        style={{
                            width: '36px', height: '20px', borderRadius: '10px', border: 'none',
                            backgroundColor: isActive ? '#10B981' : '#374151',
                            cursor: 'pointer', position: 'relative',
                        }}
                    >
                        <div style={{
                            width: '16px', height: '16px', borderRadius: '50%',
                            backgroundColor: '#fff', position: 'absolute', top: '2px',
                            left: isActive ? '18px' : '2px', transition: 'left 0.2s',
                        }} />
                    </button>
                </div>

                {/* Rules */}
                <div style={{ marginBottom: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB' }}>
                            Rules ({rules.length})
                        </span>
                        {!editPolicy && (
                            <button
                                onClick={handleAddRule}
                                style={{
                                    padding: '4px 10px', borderRadius: '4px',
                                    border: '1px solid #3B82F6', backgroundColor: 'transparent',
                                    color: '#60A5FA', cursor: 'pointer', fontSize: '11px',
                                }}
                            >
                                + Add Rule
                            </button>
                        )}
                    </div>

                    {!editPolicy && rules.map((rule, ruleIdx) => (
                        <div key={ruleIdx} style={{
                            padding: '12px', marginBottom: '8px', borderRadius: '8px',
                            backgroundColor: '#1F2937', border: '1px solid #374151',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                <input
                                    placeholder="Rule name"
                                    value={rule.name}
                                    onChange={e => updateRule(ruleIdx, 'name', e.target.value)}
                                    style={{
                                        padding: '6px', borderRadius: '4px', border: '1px solid #374151',
                                        backgroundColor: '#111827', color: '#E5E7EB', fontSize: '12px',
                                        flex: 1, marginRight: '8px',
                                    }}
                                />
                                <select
                                    value={rule.severity}
                                    onChange={e => updateRule(ruleIdx, 'severity', e.target.value)}
                                    style={{
                                        padding: '6px', borderRadius: '4px', border: '1px solid #374151',
                                        backgroundColor: '#111827', color: '#E5E7EB', fontSize: '11px',
                                        marginRight: '8px',
                                    }}
                                >
                                    {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
                                </select>
                                {rules.length > 1 && (
                                    <button onClick={() => handleRemoveRule(ruleIdx)} style={{
                                        background: 'none', border: 'none', color: '#EF4444',
                                        cursor: 'pointer', fontSize: '14px',
                                    }}>x</button>
                                )}
                            </div>

                            <div style={{ marginBottom: '6px' }}>
                                <div style={{ fontSize: '10px', color: '#9CA3AF', marginBottom: '4px' }}>Conditions:</div>
                                {rule.condition.map((pair, pi) => (
                                    <div key={pi} style={{ display: 'flex', gap: '4px', marginBottom: '2px' }}>
                                        <input placeholder="key" value={pair.key}
                                            onChange={e => updateKVPair(ruleIdx, 'condition', pi, 'key', e.target.value)}
                                            style={{ flex: 1, padding: '4px', borderRadius: '3px', border: '1px solid #374151', backgroundColor: '#111827', color: '#E5E7EB', fontSize: '11px' }}
                                        />
                                        <input placeholder="value" value={pair.value}
                                            onChange={e => updateKVPair(ruleIdx, 'condition', pi, 'value', e.target.value)}
                                            style={{ flex: 1, padding: '4px', borderRadius: '3px', border: '1px solid #374151', backgroundColor: '#111827', color: '#E5E7EB', fontSize: '11px' }}
                                        />
                                    </div>
                                ))}
                                <button onClick={() => addKVPair(ruleIdx, 'condition')}
                                    style={{ background: 'none', border: 'none', color: '#60A5FA', cursor: 'pointer', fontSize: '10px', padding: '2px 0' }}>
                                    + add condition
                                </button>
                            </div>

                            <div style={{ marginBottom: '6px' }}>
                                <div style={{ fontSize: '10px', color: '#9CA3AF', marginBottom: '4px' }}>Constraints:</div>
                                {rule.constraint.map((pair, pi) => (
                                    <div key={pi} style={{ display: 'flex', gap: '4px', marginBottom: '2px' }}>
                                        <input placeholder="key" value={pair.key}
                                            onChange={e => updateKVPair(ruleIdx, 'constraint', pi, 'key', e.target.value)}
                                            style={{ flex: 1, padding: '4px', borderRadius: '3px', border: '1px solid #374151', backgroundColor: '#111827', color: '#E5E7EB', fontSize: '11px' }}
                                        />
                                        <input placeholder="value" value={pair.value}
                                            onChange={e => updateKVPair(ruleIdx, 'constraint', pi, 'value', e.target.value)}
                                            style={{ flex: 1, padding: '4px', borderRadius: '3px', border: '1px solid #374151', backgroundColor: '#111827', color: '#E5E7EB', fontSize: '11px' }}
                                        />
                                    </div>
                                ))}
                                <button onClick={() => addKVPair(ruleIdx, 'constraint')}
                                    style={{ background: 'none', border: 'none', color: '#60A5FA', cursor: 'pointer', fontSize: '10px', padding: '2px 0' }}>
                                    + add constraint
                                </button>
                            </div>

                            <input placeholder="Rule message" value={rule.message}
                                onChange={e => updateRule(ruleIdx, 'message', e.target.value)}
                                style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #374151', backgroundColor: '#111827', color: '#E5E7EB', fontSize: '11px' }}
                            />
                        </div>
                    ))}
                </div>

                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                    <button onClick={onClose} style={{
                        padding: '8px 20px', borderRadius: '6px', border: '1px solid #374151',
                        backgroundColor: 'transparent', color: '#9CA3AF', cursor: 'pointer', fontSize: '13px',
                    }}>Cancel</button>
                    <button onClick={handleSave} disabled={saving} style={{
                        padding: '8px 20px', borderRadius: '6px', border: 'none',
                        backgroundColor: '#3B82F6', color: '#fff',
                        cursor: saving ? 'wait' : 'pointer', fontSize: '13px', fontWeight: 600,
                    }}>{saving ? 'Saving...' : 'Save'}</button>
                </div>
            </div>
        </div>
    );
};

export default PolicyEditorModal;
