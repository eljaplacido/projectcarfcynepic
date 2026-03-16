// Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
/**
 * GovernanceView — Main container for Orchestration Governance (Phase 16+17).
 *
 * 6-tab layout: Boards | Spec Map | Semantic Graph | Cost Intelligence | Policy Federation | Compliance Audit
 */

import React, { useEffect, useState } from 'react';
import type { QueryResponse } from '../../types/carf';
import GovernanceBoardTab from './GovernanceBoardTab';
import SpecMapTab from './SpecMapTab';
import CostIntelligenceTab from './CostIntelligenceTab';
import PolicyFederationTab from './PolicyFederationTab';
import ComplianceAuditTab from './ComplianceAuditTab';
import GovernanceSemanticGraphTab from './GovernanceSemanticGraphTab';
import RiskTopographyTab from './RiskTopographyTab';
import MonitoringPanel from './MonitoringPanel';

export type GovernanceTab = 'boards' | 'specmap' | 'semantic' | 'risk' | 'cost' | 'policy' | 'compliance' | 'monitoring';

interface GovernanceViewProps {
    lastResult: QueryResponse | null;
    sessionId?: string;
    activeTabOverride?: GovernanceTab | null;
}

const TABS: { id: GovernanceTab; label: string; icon: string }[] = [
    { id: 'boards', label: 'Boards', icon: 'B' },
    { id: 'specmap', label: 'Spec Map', icon: 'M' },
    { id: 'semantic', label: 'Semantic Graph', icon: 'S' },
    { id: 'risk', label: 'Risk Topography', icon: 'R' },
    { id: 'cost', label: 'Cost Intelligence', icon: '$' },
    { id: 'policy', label: 'Policy Federation', icon: 'P' },
    { id: 'compliance', label: 'Compliance Audit', icon: 'C' },
    { id: 'monitoring', label: 'Monitoring', icon: 'M' },
];

const GovernanceView: React.FC<GovernanceViewProps> = ({ lastResult, sessionId, activeTabOverride = null }) => {
    const [activeTab, setActiveTab] = useState<GovernanceTab>('boards');
    const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null);

    useEffect(() => {
        if (activeTabOverride) {
            setActiveTab(activeTabOverride);
        }
    }, [activeTabOverride]);

    return (
        <div className="governance-view" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Tab Navigation */}
            <div style={{
                display: 'flex',
                gap: '2px',
                padding: '8px 12px',
                borderBottom: '1px solid #374151',
                backgroundColor: '#111827',
            }}>
                {TABS.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '6px 6px 0 0',
                            border: 'none',
                            backgroundColor: activeTab === tab.id ? '#1F2937' : 'transparent',
                            color: activeTab === tab.id ? '#60A5FA' : '#9CA3AF',
                            cursor: 'pointer',
                            fontWeight: activeTab === tab.id ? 600 : 400,
                            fontSize: '13px',
                            transition: 'all 0.2s',
                        }}
                    >
                        <span style={{ marginRight: '6px', opacity: 0.7 }}>{tab.icon}</span>
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
                {activeTab === 'boards' && (
                    <GovernanceBoardTab
                        onBoardSelect={setSelectedBoardId}
                        selectedBoardId={selectedBoardId}
                    />
                )}
                {activeTab === 'specmap' && (
                    <SpecMapTab lastResult={lastResult} selectedBoardId={selectedBoardId} />
                )}
                {activeTab === 'semantic' && (
                    <GovernanceSemanticGraphTab
                        selectedBoardId={selectedBoardId}
                        sessionId={sessionId || lastResult?.sessionId}
                    />
                )}
                {activeTab === 'risk' && (
                    <RiskTopographyTab />
                )}
                {activeTab === 'cost' && (
                    <CostIntelligenceTab
                        sessionId={sessionId || lastResult?.sessionId}
                        selectedBoardId={selectedBoardId}
                    />
                )}
                {activeTab === 'policy' && (
                    <PolicyFederationTab />
                )}
                {activeTab === 'compliance' && (
                    <ComplianceAuditTab selectedBoardId={selectedBoardId} />
                )}
                {activeTab === 'monitoring' && (
                    <MonitoringPanel />
                )}
            </div>
        </div>
    );
};

export default GovernanceView;
