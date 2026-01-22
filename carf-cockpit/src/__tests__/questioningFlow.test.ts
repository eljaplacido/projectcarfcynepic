/**
 * Tests for the Socratic Questioning Flow Configuration
 */

import { describe, it, expect } from 'vitest';
import {
    QUESTIONING_FLOWS,
    getApplicableFlows,
    getNextStep,
    type HighlightTarget,
} from '../config/questioningFlow';

describe('Questioning Flow Configuration', () => {
    describe('QUESTIONING_FLOWS', () => {
        it('should have all required flows defined', () => {
            const flowIds = QUESTIONING_FLOWS.map(f => f.id);

            expect(flowIds).toContain('cynefin-orientation');
            expect(flowIds).toContain('causal-exploration');
            expect(flowIds).toContain('bayesian-reasoning');
            expect(flowIds).toContain('guardian-policies');
            expect(flowIds).toContain('synthesis-reflection');
        });

        it('should have valid structure for all flows', () => {
            QUESTIONING_FLOWS.forEach(flow => {
                expect(flow.id).toBeDefined();
                expect(flow.name).toBeDefined();
                expect(flow.description).toBeDefined();
                expect(flow.steps).toBeDefined();
                expect(flow.steps.length).toBeGreaterThan(0);
            });
        });

        it('should have valid steps with required fields', () => {
            QUESTIONING_FLOWS.forEach(flow => {
                flow.steps.forEach(step => {
                    expect(step.id).toBeDefined();
                    expect(step.phase).toMatch(/^(orientation|exploration|deepening|synthesis)$/);
                    expect(step.question).toBeDefined();
                    expect(step.highlightTargets).toBeDefined();
                    expect(Array.isArray(step.highlightTargets)).toBe(true);
                    expect(step.expectedTopics).toBeDefined();
                    expect(step.conceptExplanation).toBeDefined();
                    expect(step.relatedPanels).toBeDefined();
                });
            });
        });

        it('should have valid highlight targets', () => {
            const validTargets: HighlightTarget[] = [
                'cynefin-panel', 'causal-panel', 'bayesian-panel', 'guardian-panel',
                'dag-viewer', 'domain-badge', 'confidence-indicator',
                'effect-estimate', 'uncertainty-chart', 'policy-list'
            ];

            QUESTIONING_FLOWS.forEach(flow => {
                flow.steps.forEach(step => {
                    step.highlightTargets.forEach(target => {
                        expect(validTargets).toContain(target);
                    });
                });
            });
        });
    });

    describe('getApplicableFlows', () => {
        it('should return all flows when no conditions specified', () => {
            const flows = getApplicableFlows({});
            expect(flows.length).toBeGreaterThan(0);
        });

        it('should filter by causal analysis presence', () => {
            const flows = getApplicableFlows({ hasCausalAnalysis: true });

            // Should include causal-exploration flow
            const hasCausalFlow = flows.some(f => f.id === 'causal-exploration');
            expect(hasCausalFlow).toBe(true);
        });

        it('should filter by bayesian analysis presence', () => {
            const flows = getApplicableFlows({ hasBayesianAnalysis: true });

            // Should include bayesian-reasoning flow
            const hasBayesianFlow = flows.some(f => f.id === 'bayesian-reasoning');
            expect(hasBayesianFlow).toBe(true);
        });

        it('should filter flows requiring both causal and bayesian', () => {
            const flows = getApplicableFlows({
                hasCausalAnalysis: true,
                hasBayesianAnalysis: true,
            });

            // Should include synthesis-reflection which requires both
            const hasSynthesisFlow = flows.some(f => f.id === 'synthesis-reflection');
            expect(hasSynthesisFlow).toBe(true);
        });

        it('should exclude flows when conditions not met', () => {
            const flows = getApplicableFlows({
                hasCausalAnalysis: false,
                hasBayesianAnalysis: false,
            });

            // Should not include synthesis-reflection
            const hasSynthesisFlow = flows.some(f => f.id === 'synthesis-reflection');
            expect(hasSynthesisFlow).toBe(false);
        });
    });

    describe('getNextStep', () => {
        it('should return first step when no current step', () => {
            const flow = QUESTIONING_FLOWS.find(f => f.id === 'cynefin-orientation')!;
            const nextStep = getNextStep(flow);

            expect(nextStep).toBeDefined();
            expect(nextStep?.id).toBe(flow.steps[0].id);
        });

        it('should return next step after current', () => {
            const flow = QUESTIONING_FLOWS.find(f => f.id === 'cynefin-orientation')!;
            const firstStepId = flow.steps[0].id;
            const nextStep = getNextStep(flow, firstStepId);

            expect(nextStep).toBeDefined();
            expect(nextStep?.id).toBe(flow.steps[1].id);
        });

        it('should return null when at last step', () => {
            const flow = QUESTIONING_FLOWS.find(f => f.id === 'cynefin-orientation')!;
            const lastStepId = flow.steps[flow.steps.length - 1].id;
            const nextStep = getNextStep(flow, lastStepId);

            expect(nextStep).toBeNull();
        });

        it('should return null for invalid step id', () => {
            const flow = QUESTIONING_FLOWS.find(f => f.id === 'cynefin-orientation')!;
            const nextStep = getNextStep(flow, 'invalid-step-id');

            expect(nextStep).toBeNull();
        });
    });

    describe('Flow Content Quality', () => {
        it('should have meaningful questions (not empty or too short)', () => {
            QUESTIONING_FLOWS.forEach(flow => {
                flow.steps.forEach(step => {
                    expect(step.question.length).toBeGreaterThan(20);
                    expect(step.question).toMatch(/\?$/); // Should end with question mark
                });
            });
        });

        it('should have concept explanations', () => {
            QUESTIONING_FLOWS.forEach(flow => {
                flow.steps.forEach(step => {
                    expect(step.conceptExplanation.length).toBeGreaterThan(30);
                });
            });
        });

        it('should have follow-up questions defined', () => {
            let hasFollowUps = false;
            QUESTIONING_FLOWS.forEach(flow => {
                flow.steps.forEach(step => {
                    if (step.followUpQuestions && step.followUpQuestions.length > 0) {
                        hasFollowUps = true;
                    }
                });
            });
            expect(hasFollowUps).toBe(true);
        });
    });
});
