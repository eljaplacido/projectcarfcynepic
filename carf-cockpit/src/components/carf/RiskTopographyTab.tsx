/**
 * RiskTopographyTab — Governance risk distribution heatmap.
 *
 * Shows a treemap-style grid of governance domains colored by risk severity.
 * Data sourced from federated policies and their compliance/conflict status.
 */

import React, { useEffect, useMemo, useState } from 'react';
import type { GovernanceDomain, FederatedPolicyInfo, PolicyConflict } from '../../types/carf';
import { getGovernanceDomains, getFederatedPolicies, getConflicts } from '../../services/apiService';

const RISK_COLORS: Record<string, { bg: string; border: string; text: string }> = {
    critical: { bg: '#7F1D1D', border: '#EF4444', text: '#FCA5A5' },
    high:     { bg: '#78350F', border: '#F59E0B', text: '#FDE68A' },
    medium:   { bg: '#1E3A5F', border: '#3B82F6', text: '#93C5FD' },
    low:      { bg: '#064E3B', border: '#10B981', text: '#A7F3D0' },
    none:     { bg: '#1F2937', border: '#374151', text: '#9CA3AF' },
};

interface DomainRisk {
    domain: GovernanceDomain;
    policyCount: number;
    activeConflicts: number;
    inactivePolicies: number;
    riskLevel: 'critical' | 'high' | 'medium' | 'low' | 'none';
    riskScore: number; // 0-100
    details: string[];
}

function computeRisk(
    domain: GovernanceDomain,
    policies: FederatedPolicyInfo[],
    conflicts: PolicyConflict[],
): DomainRisk {
    const domainPolicies = policies.filter(p => p.domain_id === domain.domain_id);
    const domainConflicts = conflicts.filter(
        c => c.policy_a_domain === domain.domain_id || c.policy_b_domain === domain.domain_id
    );
    const inactivePolicies = domainPolicies.filter(p => !p.is_active).length;

    const details: string[] = [];
    let score = 0;

    // Conflict severity scoring
    for (const c of domainConflicts) {
        const sev = c.severity?.toLowerCase() || 'medium';
        if (sev === 'critical') score += 30;
        else if (sev === 'high') score += 20;
        else if (sev === 'medium') score += 10;
        else score += 5;
    }
    if (domainConflicts.length > 0) {
        details.push(`${domainConflicts.length} active conflict${domainConflicts.length > 1 ? 's' : ''}`);
    }

    // Inactive policies add risk
    if (inactivePolicies > 0) {
        score += inactivePolicies * 8;
        details.push(`${inactivePolicies} inactive polic${inactivePolicies > 1 ? 'ies' : 'y'}`);
    }

    // No policies = governance gap
    if (domainPolicies.length === 0) {
        score += 25;
        details.push('No policies defined — governance gap');
    }

    if (details.length === 0) details.push('No issues detected');

    score = Math.min(100, score);
    let riskLevel: DomainRisk['riskLevel'] = 'none';
    if (score >= 60) riskLevel = 'critical';
    else if (score >= 40) riskLevel = 'high';
    else if (score >= 20) riskLevel = 'medium';
    else if (score > 0) riskLevel = 'low';

    return {
        domain,
        policyCount: domainPolicies.length,
        activeConflicts: domainConflicts.length,
        inactivePolicies,
        riskLevel,
        riskScore: score,
        details,
    };
}

const RiskTopographyTab: React.FC = () => {
    const [domains, setDomains] = useState<GovernanceDomain[]>([]);
    const [policies, setPolicies] = useState<FederatedPolicyInfo[]>([]);
    const [conflicts, setConflicts] = useState<PolicyConflict[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const [d, p, c] = await Promise.all([
                    getGovernanceDomains(),
                    getFederatedPolicies(),
                    getConflicts(true),
                ]);
                if (!cancelled) {
                    setDomains(d);
                    setPolicies(p);
                    setConflicts(c);
                }
            } catch {
                // Governance may not be enabled
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, []);

    const riskData = useMemo(
        () => domains
            .map(d => computeRisk(d, policies, conflicts))
            .sort((a, b) => b.riskScore - a.riskScore),
        [domains, policies, conflicts],
    );

    const overallScore = useMemo(() => {
        if (riskData.length === 0) return 0;
        return Math.round(riskData.reduce((sum, r) => sum + r.riskScore, 0) / riskData.length);
    }, [riskData]);

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px', color: '#9CA3AF' }}>
                Loading risk topography...
            </div>
        );
    }

    if (domains.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
                <div style={{ fontSize: '42px', marginBottom: '12px' }}>RT</div>
                <p style={{ fontSize: '13px' }}>
                    No governance domains configured. Enable <code>GOVERNANCE_ENABLED=true</code> and add domains to see risk topography.
                </p>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Summary bar */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                borderRadius: '8px',
                backgroundColor: '#111827',
                border: '1px solid #1F2937',
            }}>
                <div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#E2E8F0' }}>
                        Risk Topography
                    </div>
                    <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>
                        {domains.length} domains | {policies.length} policies | {conflicts.length} active conflicts
                    </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '11px', color: '#94A3B8' }}>Avg Risk Score</div>
                    <div style={{
                        fontSize: '22px',
                        fontWeight: 800,
                        color: overallScore >= 60 ? '#EF4444' : overallScore >= 40 ? '#F59E0B' : overallScore >= 20 ? '#3B82F6' : '#10B981',
                    }}>
                        {overallScore}
                    </div>
                </div>
            </div>

            {/* Risk grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
                gap: '10px',
            }}>
                {riskData.map(risk => {
                    const colors = RISK_COLORS[risk.riskLevel];
                    return (
                        <div key={risk.domain.domain_id} style={{
                            padding: '14px',
                            borderRadius: '8px',
                            backgroundColor: colors.bg,
                            border: `1px solid ${colors.border}`,
                            transition: 'transform 0.15s',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                <div style={{ fontSize: '14px', fontWeight: 700, color: colors.text }}>
                                    {risk.domain.display_name}
                                </div>
                                <div style={{
                                    padding: '2px 8px',
                                    borderRadius: '10px',
                                    fontSize: '10px',
                                    fontWeight: 700,
                                    backgroundColor: `${colors.border}33`,
                                    color: colors.text,
                                    textTransform: 'uppercase',
                                }}>
                                    {risk.riskLevel}
                                </div>
                            </div>

                            {/* Risk bar */}
                            <div style={{
                                height: '6px',
                                borderRadius: '3px',
                                backgroundColor: '#0F172A',
                                marginBottom: '10px',
                                overflow: 'hidden',
                            }}>
                                <div style={{
                                    width: `${risk.riskScore}%`,
                                    height: '100%',
                                    borderRadius: '3px',
                                    backgroundColor: colors.border,
                                    transition: 'width 0.5s ease',
                                }} />
                            </div>

                            {/* Stats */}
                            <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: '#94A3B8', marginBottom: '8px' }}>
                                <span>{risk.policyCount} policies</span>
                                <span>{risk.activeConflicts} conflicts</span>
                                <span>score: {risk.riskScore}</span>
                            </div>

                            {/* Details */}
                            <div style={{ fontSize: '11px', color: colors.text, opacity: 0.85 }}>
                                {risk.details.map((d, i) => (
                                    <div key={i} style={{ marginBottom: '2px' }}>
                                        {risk.riskLevel !== 'none' ? '!' : '-'} {d}
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default RiskTopographyTab;
