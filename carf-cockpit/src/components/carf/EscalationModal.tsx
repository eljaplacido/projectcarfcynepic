/**
 * EscalationModal.tsx - Human-in-the-Loop review modal
 *
 * Displays escalations requiring human decision and allows
 * approve/reject/clarify actions with optional notes.
 *
 * Features:
 * - Full transparency on what triggered the escalation
 * - Detailed Guardian layer mechanism explanation
 * - Channel configuration for feedback notifications
 * - Always-available manual intervention option
 */

import React, { useState, useEffect } from 'react';

// Types
interface NotificationContext {
    what: string;
    why: string;
    risk: string;
}

interface TriggerDetails {
    mechanism: string;
    threshold: string;
    currentValue: string;
    guardianRule?: string;
    affectedPolicies?: string[];
}

interface Escalation {
    id: string;
    session_id: string;
    reason: string;
    reason_type: 'low_confidence' | 'policy_violation' | 'disorder' | 'high_risk';
    context: NotificationContext;
    state_snapshot: Record<string, unknown>;
    created_at: string;
    resolved_at: string | null;
    resolution: string | null;
    resolver_notes: string | null;
    resolver_email: string | null;
    trigger_details?: TriggerDetails;
}

interface NotificationChannel {
    id: string;
    name: string;
    type: 'slack' | 'email' | 'teams' | 'webhook';
    enabled: boolean;
}

interface EscalationModalProps {
    isOpen: boolean;
    onClose: () => void;
    onResolved?: (escalation: Escalation) => void;
}

const API_BASE = 'http://localhost:8000';

// Styles
const styles = {
    overlay: {
        position: 'fixed' as const,
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
    },
    modal: {
        backgroundColor: '#1a1a2e',
        borderRadius: '16px',
        maxWidth: '600px',
        width: '100%',
        maxHeight: '80vh',
        overflow: 'auto',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: '0 24px 48px rgba(0, 0, 0, 0.4)',
    },
    header: {
        padding: '1.5rem',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    title: {
        fontSize: '1.25rem',
        fontWeight: 600,
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
    },
    closeButton: {
        background: 'transparent',
        border: 'none',
        color: '#888',
        fontSize: '1.5rem',
        cursor: 'pointer',
        lineHeight: 1,
    },
    body: {
        padding: '1.5rem',
    },
    emptyState: {
        textAlign: 'center' as const,
        padding: '3rem 1rem',
        color: '#888',
    },
    escalationCard: {
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        borderRadius: '12px',
        padding: '1.25rem',
        marginBottom: '1rem',
        border: '1px solid rgba(255, 255, 255, 0.08)',
    },
    badge: {
        display: 'inline-block',
        padding: '0.25rem 0.75rem',
        borderRadius: '100px',
        fontSize: '0.75rem',
        fontWeight: 600,
        textTransform: 'uppercase' as const,
        marginBottom: '0.75rem',
    },
    contextSection: {
        marginTop: '1rem',
        padding: '1rem',
        backgroundColor: 'rgba(0, 0, 0, 0.2)',
        borderRadius: '8px',
        fontSize: '0.875rem',
    },
    contextLabel: {
        color: '#888',
        fontSize: '0.75rem',
        textTransform: 'uppercase' as const,
        marginBottom: '0.25rem',
    },
    contextValue: {
        color: '#fff',
        marginBottom: '0.75rem',
    },
    actions: {
        display: 'flex',
        gap: '0.75rem',
        marginTop: '1.25rem',
        flexWrap: 'wrap' as const,
    },
    button: {
        flex: 1,
        padding: '0.75rem 1rem',
        borderRadius: '8px',
        border: 'none',
        fontWeight: 600,
        cursor: 'pointer',
        fontSize: '0.875rem',
        transition: 'all 0.2s',
        minWidth: '100px',
    },
    approveBtn: {
        backgroundColor: '#10b981',
        color: '#fff',
    },
    rejectBtn: {
        backgroundColor: '#ef4444',
        color: '#fff',
    },
    clarifyBtn: {
        backgroundColor: '#6366f1',
        color: '#fff',
    },
    notesInput: {
        width: '100%',
        padding: '0.75rem',
        borderRadius: '8px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        backgroundColor: 'rgba(0, 0, 0, 0.3)',
        color: '#fff',
        fontSize: '0.875rem',
        resize: 'vertical' as const,
        marginTop: '1rem',
        minHeight: '80px',
    },
};

const reasonTypeColors: Record<string, { bg: string; text: string }> = {
    low_confidence: { bg: 'rgba(251, 191, 36, 0.2)', text: '#fbbf24' },
    policy_violation: { bg: 'rgba(239, 68, 68, 0.2)', text: '#ef4444' },
    disorder: { bg: 'rgba(156, 163, 175, 0.2)', text: '#9ca3af' },
    high_risk: { bg: 'rgba(239, 68, 68, 0.2)', text: '#ef4444' },
};

// Trigger explanation mapping
const TRIGGER_EXPLANATIONS: Record<string, { title: string; description: string; recommendation: string }> = {
    low_confidence: {
        title: 'Low Confidence Detection',
        description: 'The system\'s domain classification confidence fell below the configured threshold. This typically occurs when the query contains ambiguous terms or spans multiple Cynefin domains.',
        recommendation: 'Review the query context and provide clarification on the specific domain or rephrase the question.',
    },
    policy_violation: {
        title: 'Guardian Policy Violation',
        description: 'One or more governance policies defined in the Guardian layer have been violated. These policies ensure ethical, legal, and operational compliance.',
        recommendation: 'Review the violated policies and determine if an exception is warranted or if the action needs modification.',
    },
    disorder: {
        title: 'Disorder Domain Classification',
        description: 'The query could not be clearly categorized into Clear, Complicated, Complex, or Chaotic domains. This suggests the problem statement needs clarification.',
        recommendation: 'Help clarify the query by providing additional context or breaking it into smaller, more focused questions.',
    },
    high_risk: {
        title: 'High Risk Assessment',
        description: 'The proposed action has been flagged as high-risk based on potential impact analysis. This may involve significant financial, operational, or reputational implications.',
        recommendation: 'Carefully evaluate the potential consequences and ensure proper safeguards are in place before approval.',
    },
};

// Default notification channels
const DEFAULT_CHANNELS: NotificationChannel[] = [
    { id: 'slack', name: 'Slack', type: 'slack', enabled: true },
    { id: 'email', name: 'Email', type: 'email', enabled: false },
    { id: 'teams', name: 'Microsoft Teams', type: 'teams', enabled: false },
    { id: 'webhook', name: 'Custom Webhook', type: 'webhook', enabled: false },
];

const EscalationModal: React.FC<EscalationModalProps> = ({
    isOpen,
    onClose,
    onResolved,
}) => {
    const [escalations, setEscalations] = useState<Escalation[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedNotes, setSelectedNotes] = useState<Record<string, string>>({});
    const [resolving, setResolving] = useState<string | null>(null);
    const [showTriggerDetails, setShowTriggerDetails] = useState<Record<string, boolean>>({});
    const [channels, setChannels] = useState<NotificationChannel[]>(DEFAULT_CHANNELS);
    const [showChannelSettings, setShowChannelSettings] = useState(false);
    const [manualInterventionOpen, setManualInterventionOpen] = useState(false);

    // Fetch pending escalations
    useEffect(() => {
        if (isOpen) {
            fetchEscalations();
        }
    }, [isOpen]);

    const fetchEscalations = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE}/escalations?pending_only=true`);
            if (response.ok) {
                const data = await response.json();
                setEscalations(data);
            }
        } catch (error) {
            console.error('Failed to fetch escalations:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleResolve = async (
        escalationId: string,
        resolution: 'approve' | 'reject' | 'clarify'
    ) => {
        setResolving(escalationId);
        try {
            const response = await fetch(
                `${API_BASE}/escalations/${escalationId}/resolve`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        resolution,
                        notes: selectedNotes[escalationId] || null,
                    }),
                }
            );

            if (response.ok) {
                const resolved = await response.json();
                setEscalations((prev) => prev.filter((e) => e.id !== escalationId));
                onResolved?.(resolved);
            }
        } catch (error) {
            console.error('Failed to resolve escalation:', error);
        } finally {
            setResolving(null);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={styles.overlay} onClick={onClose}>
            <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div style={styles.header}>
                    <div style={styles.title}>
                        <span>⚠️</span>
                        <span>Human Review Required</span>
                        {escalations.length > 0 && (
                            <span
                                style={{
                                    backgroundColor: '#ef4444',
                                    color: '#fff',
                                    borderRadius: '100px',
                                    padding: '0.125rem 0.5rem',
                                    fontSize: '0.75rem',
                                    marginLeft: '0.5rem',
                                }}
                            >
                                {escalations.length}
                            </span>
                        )}
                    </div>
                    <button style={styles.closeButton} onClick={onClose}>
                        ×
                    </button>
                </div>

                {/* Toolbar with Channel Config */}
                <div style={{
                    padding: '0.75rem 1.5rem',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    backgroundColor: 'rgba(0, 0, 0, 0.2)',
                }}>
                    <button
                        onClick={() => setManualInterventionOpen(!manualInterventionOpen)}
                        style={{
                            ...styles.button,
                            flex: 'none',
                            backgroundColor: 'rgba(99, 102, 241, 0.2)',
                            color: '#818cf8',
                            fontSize: '0.75rem',
                            padding: '0.5rem 1rem',
                        }}
                    >
                        + Request Manual Review
                    </button>
                    <button
                        onClick={() => setShowChannelSettings(!showChannelSettings)}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#888',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            fontSize: '0.75rem',
                        }}
                    >
                        <span>⚙️</span> Notification Channels
                    </button>
                </div>

                {/* Channel Configuration Panel */}
                {showChannelSettings && (
                    <div style={{
                        padding: '1rem 1.5rem',
                        backgroundColor: 'rgba(0, 0, 0, 0.3)',
                        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                    }}>
                        <div style={{ color: '#888', fontSize: '0.75rem', marginBottom: '0.75rem', textTransform: 'uppercase' }}>
                            Configure where to receive escalation notifications:
                        </div>
                        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                            {channels.map(channel => (
                                <label key={channel.id} style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    cursor: 'pointer',
                                    color: channel.enabled ? '#fff' : '#666',
                                }}>
                                    <input
                                        type="checkbox"
                                        checked={channel.enabled}
                                        onChange={() => {
                                            setChannels(prev => prev.map(c =>
                                                c.id === channel.id ? { ...c, enabled: !c.enabled } : c
                                            ));
                                        }}
                                        style={{ accentColor: '#6366f1' }}
                                    />
                                    {channel.name}
                                </label>
                            ))}
                        </div>
                        <div style={{
                            marginTop: '0.75rem',
                            padding: '0.5rem',
                            backgroundColor: 'rgba(99, 102, 241, 0.1)',
                            borderRadius: '6px',
                            fontSize: '0.75rem',
                            color: '#a5b4fc',
                        }}>
                            💡 Tip: Enable multiple channels to ensure you never miss critical escalations.
                        </div>
                    </div>
                )}

                {/* Manual Intervention Form */}
                {manualInterventionOpen && (
                    <div style={{
                        padding: '1rem 1.5rem',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        borderBottom: '1px solid rgba(99, 102, 241, 0.3)',
                    }}>
                        <div style={{ color: '#fff', fontWeight: 500, marginBottom: '0.75rem' }}>
                            Request Manual Review
                        </div>
                        <div style={{ color: '#a5b4fc', fontSize: '0.875rem', marginBottom: '1rem' }}>
                            You can always request human review for any analysis, even if the system didn't trigger an automatic escalation.
                        </div>
                        <textarea
                            placeholder="Describe what you'd like reviewed and why..."
                            style={{
                                ...styles.notesInput,
                                marginTop: 0,
                                minHeight: '60px',
                            }}
                        />
                        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem' }}>
                            <button
                                style={{
                                    ...styles.button,
                                    backgroundColor: '#6366f1',
                                    color: '#fff',
                                    flex: 'none',
                                }}
                            >
                                Submit Review Request
                            </button>
                            <button
                                onClick={() => setManualInterventionOpen(false)}
                                style={{
                                    ...styles.button,
                                    backgroundColor: 'transparent',
                                    color: '#888',
                                    border: '1px solid rgba(255, 255, 255, 0.1)',
                                    flex: 'none',
                                }}
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                )}

                {/* Body */}
                <div style={styles.body}>
                    {loading ? (
                        <div style={styles.emptyState}>Loading escalations...</div>
                    ) : escalations.length === 0 ? (
                        <div style={styles.emptyState}>
                            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>✓</div>
                            <div>No pending escalations</div>
                            <div style={{ fontSize: '0.875rem', marginTop: '0.25rem' }}>
                                All decisions are automated or have been resolved.
                            </div>
                            <div style={{ fontSize: '0.75rem', marginTop: '1rem', color: '#6366f1' }}>
                                You can always request manual review using the button above.
                            </div>
                        </div>
                    ) : (
                        escalations.map((escalation) => {
                            const colors = reasonTypeColors[escalation.reason_type] || {
                                bg: 'rgba(255,255,255,0.1)',
                                text: '#fff',
                            };

                            return (
                                <div key={escalation.id} style={styles.escalationCard}>
                                    {/* Badge */}
                                    <span
                                        style={{
                                            ...styles.badge,
                                            backgroundColor: colors.bg,
                                            color: colors.text,
                                        }}
                                    >
                                        {escalation.reason_type.replace('_', ' ')}
                                    </span>

                                    {/* Reason */}
                                    <div style={{ color: '#fff', fontWeight: 500 }}>
                                        {escalation.reason}
                                    </div>

                                    {/* Trigger Explanation Toggle */}
                                    <button
                                        onClick={() => setShowTriggerDetails(prev => ({
                                            ...prev,
                                            [escalation.id]: !prev[escalation.id]
                                        }))}
                                        style={{
                                            background: 'transparent',
                                            border: 'none',
                                            color: '#6366f1',
                                            cursor: 'pointer',
                                            fontSize: '0.75rem',
                                            padding: '0.5rem 0',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.25rem',
                                        }}
                                    >
                                        {showTriggerDetails[escalation.id] ? '▼' : '▶'} Why was this triggered?
                                    </button>

                                    {/* Trigger Details Explanation */}
                                    {showTriggerDetails[escalation.id] && (
                                        <div style={{
                                            padding: '1rem',
                                            backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                            borderRadius: '8px',
                                            marginBottom: '0.75rem',
                                            border: '1px solid rgba(99, 102, 241, 0.2)',
                                        }}>
                                            <div style={{ color: '#a5b4fc', fontWeight: 600, marginBottom: '0.5rem' }}>
                                                {TRIGGER_EXPLANATIONS[escalation.reason_type]?.title || 'Escalation Triggered'}
                                            </div>
                                            <div style={{ color: '#d1d5db', fontSize: '0.875rem', marginBottom: '0.75rem' }}>
                                                {TRIGGER_EXPLANATIONS[escalation.reason_type]?.description || 'This escalation was triggered based on system analysis.'}
                                            </div>
                                            <div style={{
                                                padding: '0.75rem',
                                                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                                borderRadius: '6px',
                                                border: '1px solid rgba(16, 185, 129, 0.2)',
                                            }}>
                                                <div style={{ color: '#34d399', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                                                    💡 RECOMMENDATION
                                                </div>
                                                <div style={{ color: '#a7f3d0', fontSize: '0.875rem' }}>
                                                    {TRIGGER_EXPLANATIONS[escalation.reason_type]?.recommendation || 'Review the context and make an informed decision.'}
                                                </div>
                                            </div>
                                            {escalation.trigger_details && (
                                                <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#9ca3af' }}>
                                                    <div>Mechanism: {escalation.trigger_details.mechanism}</div>
                                                    <div>Threshold: {escalation.trigger_details.threshold}</div>
                                                    <div>Current Value: {escalation.trigger_details.currentValue}</div>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* 3-Point Context */}
                                    <div style={styles.contextSection}>
                                        <div style={styles.contextLabel}>What</div>
                                        <div style={styles.contextValue}>
                                            {escalation.context.what}
                                        </div>

                                        <div style={styles.contextLabel}>Why</div>
                                        <div style={styles.contextValue}>
                                            {escalation.context.why}
                                        </div>

                                        <div style={styles.contextLabel}>Risk</div>
                                        <div style={{ ...styles.contextValue, marginBottom: 0 }}>
                                            {escalation.context.risk}
                                        </div>
                                    </div>

                                    {/* Notes */}
                                    <textarea
                                        style={styles.notesInput}
                                        placeholder="Add notes (optional)..."
                                        value={selectedNotes[escalation.id] || ''}
                                        onChange={(e) =>
                                            setSelectedNotes((prev) => ({
                                                ...prev,
                                                [escalation.id]: e.target.value,
                                            }))
                                        }
                                    />

                                    {/* Action Buttons */}
                                    <div style={styles.actions}>
                                        <button
                                            style={{ ...styles.button, ...styles.approveBtn }}
                                            onClick={() => handleResolve(escalation.id, 'approve')}
                                            disabled={resolving === escalation.id}
                                        >
                                            ✓ Approve
                                        </button>
                                        <button
                                            style={{ ...styles.button, ...styles.rejectBtn }}
                                            onClick={() => handleResolve(escalation.id, 'reject')}
                                            disabled={resolving === escalation.id}
                                        >
                                            ✕ Reject
                                        </button>
                                        <button
                                            style={{ ...styles.button, ...styles.clarifyBtn }}
                                            onClick={() => handleResolve(escalation.id, 'clarify')}
                                            disabled={resolving === escalation.id}
                                        >
                                            ? Clarify
                                        </button>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
};

export default EscalationModal;
