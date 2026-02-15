import React, { useState } from 'react';
import PolicyEditorModal from './PolicyEditorModal';
import type { GuardianDecision } from '../../types/carf';
import ExplainableWrapper from './ExplainableWrapper';

interface GuardianPanelProps {
    decision: GuardianDecision | null;
}

const GuardianPanel: React.FC<GuardianPanelProps> = ({ decision }) => {
    const [showPolicyEditor, setShowPolicyEditor] = useState(false);

    if (!decision) {
        return (
            <div className="text-sm text-gray-500 italic">
                Guardian policy check will appear here
            </div>
        );
    }

    const getVerdictBadge = (status: string) => {
        switch (status) {
            case 'pass':
                return <span className="badge bg-green-500 text-white">✓ APPROVED</span>;
            case 'fail':
                return <span className="badge bg-red-500 text-white">✗ REJECTED</span>;
            case 'pending':
                return <span className="badge bg-yellow-500 text-white">⚠ REQUIRES APPROVAL</span>;
            default:
                return <span className="badge bg-gray-500 text-white">UNKNOWN</span>;
        }
    };

    return (
        <div className="space-y-4">
            {/* Verdict */}
            <ExplainableWrapper
                component="guardian_verdict"
                context={{ status: decision.overallStatus, requiresApproval: decision.requiresHumanApproval }}
                title="Guardian Verdict"
            >
                <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-900">Guardian Verdict</span>
                    {getVerdictBadge(decision.overallStatus)}
                </div>
            </ExplainableWrapper>

            {/* 3-Point Context */}
            <div className="space-y-3">
                <ExplainableWrapper
                    component="guardian_action"
                    elementId="what"
                    context={{ action: decision.proposedAction }}
                    title="Proposed Action"
                >
                    <div className="p-3 bg-blue-50 border-l-4 border-blue-500 rounded">
                        <div className="text-xs font-semibold text-blue-900 mb-1">WHAT</div>
                        <div className="text-sm text-blue-800">
                            {decision.proposedAction.type.toUpperCase()}: {decision.proposedAction.target}
                            <div className="text-xs mt-1">
                                Amount: ${decision.proposedAction.amount.toLocaleString()} {decision.proposedAction.unit}
                            </div>
                        </div>
                    </div>
                </ExplainableWrapper>

                <ExplainableWrapper
                    component="guardian_action"
                    elementId="why"
                    context={{ expectedEffect: decision.proposedAction.expectedEffect }}
                    title="Expected Effect"
                >
                    <div className="p-3 bg-purple-50 border-l-4 border-purple-500 rounded">
                        <div className="text-xs font-semibold text-purple-900 mb-1">WHY</div>
                        <div className="text-sm text-purple-800">
                            Expected effect: {decision.proposedAction.expectedEffect}
                        </div>
                    </div>
                </ExplainableWrapper>

                <ExplainableWrapper
                    component="guardian_risk"
                    context={{ policiesPassed: decision.policies.every(p => p.status === 'passed'), policyCount: decision.policies.length }}
                    title="Risk Assessment"
                >
                    <div className={`p-3 border-l-4 rounded ${decision.policies.some(p => p.status === 'failed')
                        ? 'bg-red-50 border-red-500'
                        : 'bg-green-50 border-green-500'
                        }`}>
                        <div className={`text-xs font-semibold mb-1 ${decision.policies.some(p => p.status === 'failed') ? 'text-red-900' : 'text-green-900'
                            }`}>RISK</div>
                        <div className={`text-sm ${decision.policies.some(p => p.status === 'failed') ? 'text-red-800' : 'text-green-800'
                            }`}>
                            {decision.policies.every(p => p.status === 'passed')
                                ? 'All policy checks passed'
                                : 'Policy violations detected'}
                        </div>
                    </div>
                </ExplainableWrapper>
            </div>

            {/* Policy Checks */}
            <ExplainableWrapper
                component="guardian_policies"
                context={{ totalPolicies: decision.policies.length, passedPolicies: decision.policies.filter(p => p.status === 'passed').length }}
                title="Policy Checks"
            >
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <div className="text-sm font-semibold text-gray-900">Policy Checks</div>
                        <button
                            onClick={() => setShowPolicyEditor(true)}
                            className="text-xs text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1"
                            title="Edit validation rules"
                        >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            Configure
                        </button>
                    </div>
                    <p className="text-[10px] text-gray-500 mb-3 italic">
                        Policies define the safety boundaries for automated actions. Passing all checks enables autonomous execution.
                    </p>
                    <div className="space-y-2">
                        {decision.policies.map((policy, idx) => (
                            <ExplainableWrapper
                                key={idx}
                                component="guardian_policy"
                                elementId={policy.name}
                                context={{ policyName: policy.name, status: policy.status, details: policy.details }}
                                title={policy.name}
                            >
                                <div className="p-2 bg-gray-50 rounded hover:bg-gray-100 transition-colors">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <span className={`text-sm ${policy.status === 'passed' ? 'text-green-500' :
                                                policy.status === 'failed' ? 'text-red-500' :
                                                    'text-yellow-500'
                                                }`}>
                                                {policy.status === 'passed' ? '✓' : policy.status === 'failed' ? '✗' : '⚠'}
                                            </span>
                                            <span className="text-sm font-medium text-gray-900">{policy.name}</span>
                                        </div>
                                        <span className="text-xs text-gray-500">{policy.version}</span>
                                    </div>
                                    {policy.details && (
                                        <div className="text-xs text-gray-600 mt-1 ml-6">{policy.details}</div>
                                    )}
                                </div>
                            </ExplainableWrapper>
                        ))}
                    </div>
                </div>
            </ExplainableWrapper>

            {/* Human Approval Required */}
            {decision.requiresHumanApproval && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                    <div className="text-sm font-semibold text-yellow-900 mb-2">⚠️ Human Approval Required</div>
                    <div className="flex gap-2">
                        <button className="flex-1 px-3 py-2 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors">
                            ✓ Approve
                        </button>
                        <button className="flex-1 px-3 py-2 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
                            ✗ Reject
                        </button>
                    </div>
                </div>
            )}
            <PolicyEditorModal
                isOpen={showPolicyEditor}
                onClose={() => setShowPolicyEditor(false)}
            />
        </div>
    );
};

export default GuardianPanel;
