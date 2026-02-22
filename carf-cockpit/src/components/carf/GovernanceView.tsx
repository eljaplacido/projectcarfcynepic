/**
 * GovernanceView — Main container for Orchestration Governance (Phase 16+17).
 *
 * 5-tab layout: Boards | Spec Map | Cost Intelligence | Policy Federation | Compliance Audit
 */

import React, { useState } from 'react';
import type { QueryResponse } from '../../types/carf';
import GovernanceBoardTab from './GovernanceBoardTab';
import SpecMapTab from './SpecMapTab';
import CostIntelligenceTab from './CostIntelligenceTab';
import PolicyFederationTab from './PolicyFederationTab';
import ComplianceAuditTab from './ComplianceAuditTab';

type GovernanceTab = 'boards' | 'specmap' | 'cost' | 'policy' | 'compliance';

interface GovernanceViewProps {
    lastResult: QueryResponse | null;
    sessionId?: string;
}

const TABS: { id: GovernanceTab; label: string; icon: string }[] = [
    { id: 'boards', label: 'Boards', icon: 'B' },
    { id: 'specmap', label: 'Spec Map', icon: 'M' },
    { id: 'cost', label: 'Cost Intelligence', icon: '$' },
    { id: 'policy', label: 'Policy Federation', icon: 'P' },
    { id: 'compliance', label: 'Compliance Audit', icon: 'C' },
];

const GovernanceView: React.FC<GovernanceViewProps> = ({ lastResult, sessionId }) => {
    const [activeTab, setActiveTab] = useState<GovernanceTab>('boards');
    const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null);

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
            </div>
        </div>
    );
};

export default GovernanceView;
