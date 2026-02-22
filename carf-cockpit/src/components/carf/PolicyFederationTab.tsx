/**
 * PolicyFederationTab — RESOLVE pillar visualization.
 *
 * Domain sidebar + policy cards with CRUD + conflict panel + policy ingestion.
 */

import React, { useEffect, useState, useCallback } from 'react';
import type { GovernanceDomain, FederatedPolicyInfo, PolicyConflict } from '../../types/carf';
import {
    getGovernanceDomains,
    getFederatedPolicies,
    getConflicts,
    resolveConflict,
    deleteFederatedPolicy,
    updateFederatedPolicy,
} from '../../services/apiService';
import PolicyEditorModal from './PolicyEditorModal';
import PolicyIngestionPanel from './PolicyIngestionPanel';

const DOMAIN_COLORS: Record<string, string> = {
    procurement: '#3B82F6',
    sustainability: '#10B981',
    security: '#EF4444',
    legal: '#8B5CF6',
    finance: '#F59E0B',
};

const SEVERITY_COLORS: Record<string, string> = {
    critical: '#EF4444',
    high: '#F97316',
    medium: '#F59E0B',
    low: '#10B981',
};

const PolicyFederationTab: React.FC = () => {
    const [domains, setDomains] = useState<GovernanceDomain[]>([]);
    const [policies, setPolicies] = useState<FederatedPolicyInfo[]>([]);
    const [conflicts, setConflicts] = useState<PolicyConflict[]>([]);
    const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [editorOpen, setEditorOpen] = useState(false);
    const [editingPolicy, setEditingPolicy] = useState<FederatedPolicyInfo | null>(null);

    const loadData = useCallback(async () => {
        try {
            const [d, p, c] = await Promise.all([
                getGovernanceDomains(),
                getFederatedPolicies(),
                getConflicts(),
            ]);
            setDomains(d);
            setPolicies(p);
            setConflicts(c);
        } catch {
            // Governance may not be enabled
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const filteredPolicies = selectedDomain
        ? policies.filter(p => p.domain_id === selectedDomain)
        : policies;

    const handleResolve = async (conflictId: string) => {
        const resolution = prompt('Enter resolution description:');
        if (!resolution) return;
        try {
            await resolveConflict(conflictId, resolution);
            setConflicts(prev => prev.filter(c => c.conflict_id !== conflictId));
        } catch (err) {
            console.error('Failed to resolve conflict:', err);
        }
    };

    const handleDeletePolicy = async (namespace: string) => {
        if (!confirm('Delete this policy?')) return;
        try {
            await deleteFederatedPolicy(namespace);
            setPolicies(prev => prev.filter(p => p.namespace !== namespace));
        } catch (err) {
            console.error('Failed to delete policy:', err);
        }
    };

    const handleTogglePolicy = async (policy: FederatedPolicyInfo) => {
        try {
            await updateFederatedPolicy(policy.namespace, { is_active: !policy.is_active });
            setPolicies(prev => prev.map(p =>
                p.namespace === policy.namespace ? { ...p, is_active: !p.is_active } : p
            ));
        } catch (err) {
            console.error('Failed to toggle policy:', err);
        }
    };

    const handleEditPolicy = (policy: FederatedPolicyInfo) => {
        setEditingPolicy(policy);
        setEditorOpen(true);
    };

    const handleCreatePolicy = () => {
        setEditingPolicy(null);
        setEditorOpen(true);
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', color: '#9CA3AF' }}>
                Loading policy federation...
            </div>
        );
    }

    if (domains.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>RESOLVE</div>
                <p style={{ fontSize: '14px' }}>
                    No federated policies loaded. Add policy YAML files to <code>config/federated_policies/</code>.
                </p>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
            {/* Policy Editor Modal */}
            <PolicyEditorModal
                isOpen={editorOpen}
                onClose={() => { setEditorOpen(false); setEditingPolicy(null); }}
                onSaved={loadData}
                editPolicy={editingPolicy}
            />

            <div style={{ display: 'flex', gap: '16px', flex: 1 }}>
                {/* Domain Sidebar */}
                <div style={{
                    width: '220px',
                    flexShrink: 0,
                    backgroundColor: '#1F2937',
                    borderRadius: '8px',
                    padding: '12px',
                    border: '1px solid #374151',
                    overflowY: 'auto',
                }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#9CA3AF', marginBottom: '8px', textTransform: 'uppercase' }}>
                        Domains ({domains.length})
                    </div>
                    <button
                        onClick={() => setSelectedDomain(null)}
                        style={{
                            width: '100%', padding: '8px', borderRadius: '6px', border: 'none',
                            backgroundColor: !selectedDomain ? '#374151' : 'transparent',
                            color: !selectedDomain ? '#E5E7EB' : '#9CA3AF',
                            cursor: 'pointer', textAlign: 'left', marginBottom: '4px', fontSize: '12px',
                        }}
                    >
                        All Domains
                    </button>
                    {domains.map(domain => {
                        const color = DOMAIN_COLORS[domain.domain_id] || domain.color;
                        const pCount = policies.filter(p => p.domain_id === domain.domain_id).length;
                        return (
                            <button
                                key={domain.domain_id}
                                onClick={() => setSelectedDomain(domain.domain_id)}
                                style={{
                                    width: '100%', padding: '8px', borderRadius: '6px', border: 'none',
                                    backgroundColor: selectedDomain === domain.domain_id ? '#374151' : 'transparent',
                                    color: selectedDomain === domain.domain_id ? color : '#9CA3AF',
                                    cursor: 'pointer', textAlign: 'left', marginBottom: '4px', fontSize: '12px',
                                    borderLeft: `3px solid ${color}`,
                                }}
                            >
                                <div style={{ fontWeight: 600 }}>{domain.display_name}</div>
                                <div style={{ fontSize: '10px', opacity: 0.7 }}>{pCount} policies</div>
                            </button>
                        );
                    })}
                </div>

                {/* Main Content */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
                    {/* Policy Cards */}
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB' }}>
                                Policies ({filteredPolicies.length})
                            </div>
                            <button
                                onClick={handleCreatePolicy}
                                style={{
                                    padding: '6px 14px', borderRadius: '6px', border: '1px solid #3B82F6',
                                    backgroundColor: '#3B82F622', color: '#60A5FA', cursor: 'pointer',
                                    fontSize: '12px', fontWeight: 600,
                                }}
                            >
                                + Create Policy
                            </button>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '8px' }}>
                            {filteredPolicies.map(policy => {
                                const color = DOMAIN_COLORS[policy.domain_id] || '#6B7280';
                                return (
                                    <div key={policy.namespace} style={{
                                        padding: '12px',
                                        borderRadius: '8px',
                                        backgroundColor: '#1F2937',
                                        border: `1px solid ${color}33`,
                                        borderLeft: `3px solid ${color}`,
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span style={{ fontWeight: 600, color: '#E5E7EB', fontSize: '13px' }}>{policy.name}</span>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                {/* Active/Inactive Toggle */}
                                                <button
                                                    onClick={() => handleTogglePolicy(policy)}
                                                    title={policy.is_active ? 'Deactivate' : 'Activate'}
                                                    style={{
                                                        width: '32px', height: '16px', borderRadius: '8px', border: 'none',
                                                        backgroundColor: policy.is_active ? '#10B981' : '#374151',
                                                        cursor: 'pointer', position: 'relative',
                                                    }}
                                                >
                                                    <div style={{
                                                        width: '12px', height: '12px', borderRadius: '50%',
                                                        backgroundColor: '#fff', position: 'absolute', top: '2px',
                                                        left: policy.is_active ? '18px' : '2px', transition: 'left 0.2s',
                                                    }} />
                                                </button>
                                                {/* Edit */}
                                                <button
                                                    onClick={() => handleEditPolicy(policy)}
                                                    title="Edit"
                                                    style={{
                                                        background: 'none', border: 'none', color: '#60A5FA',
                                                        cursor: 'pointer', fontSize: '12px', padding: '2px 4px',
                                                    }}
                                                >
                                                    E
                                                </button>
                                                {/* Delete */}
                                                <button
                                                    onClick={() => handleDeletePolicy(policy.namespace)}
                                                    title="Delete"
                                                    style={{
                                                        background: 'none', border: 'none', color: '#EF4444',
                                                        cursor: 'pointer', fontSize: '12px', padding: '2px 4px',
                                                    }}
                                                >
                                                    x
                                                </button>
                                            </div>
                                        </div>
                                        <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '4px' }}>{policy.namespace}</div>
                                        <div style={{ fontSize: '11px', color: '#6B7280', marginTop: '4px' }}>
                                            {policy.rules.length} rules | Priority: {policy.priority}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Conflicts Panel */}
                    {conflicts.length > 0 && (
                        <div>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#F59E0B', marginBottom: '8px' }}>
                                Unresolved Conflicts ({conflicts.length})
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {conflicts.map(conflict => (
                                    <div key={conflict.conflict_id} style={{
                                        padding: '12px',
                                        borderRadius: '8px',
                                        backgroundColor: '#1F2937',
                                        border: `1px solid ${SEVERITY_COLORS[conflict.severity] || '#374151'}`,
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span style={{
                                                fontSize: '10px',
                                                padding: '2px 8px',
                                                borderRadius: '4px',
                                                backgroundColor: `${SEVERITY_COLORS[conflict.severity]}22`,
                                                color: SEVERITY_COLORS[conflict.severity],
                                                fontWeight: 600,
                                                textTransform: 'uppercase',
                                            }}>
                                                {conflict.severity}
                                            </span>
                                            <span style={{ fontSize: '10px', color: '#9CA3AF' }}>{conflict.conflict_type}</span>
                                        </div>
                                        <div style={{ fontSize: '12px', color: '#D1D5DB', marginTop: '8px' }}>
                                            <strong>{conflict.policy_a_name}</strong> ({conflict.policy_a_domain}) vs{' '}
                                            <strong>{conflict.policy_b_name}</strong> ({conflict.policy_b_domain})
                                        </div>
                                        <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '4px' }}>
                                            {conflict.description}
                                        </div>
                                        <button
                                            onClick={() => handleResolve(conflict.conflict_id)}
                                            style={{
                                                marginTop: '8px',
                                                padding: '4px 12px',
                                                borderRadius: '4px',
                                                border: '1px solid #F59E0B',
                                                backgroundColor: 'transparent',
                                                color: '#F59E0B',
                                                cursor: 'pointer',
                                                fontSize: '11px',
                                            }}
                                        >
                                            Resolve
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Policy Ingestion Panel */}
                    <PolicyIngestionPanel onRulesAdded={loadData} />
                </div>
            </div>
        </div>
    );
};

export default PolicyFederationTab;
