import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AgentFlowChart, { type TraceStep } from '../components/carf/AgentFlowChart';

// Mock ReactFlow since it requires browser APIs not available in jsdom
vi.mock('reactflow', () => {
    const ReactFlow = ({ nodes, edges, onNodeClick, nodeTypes }: any) => {
        const AgentNode = nodeTypes?.agentNode;
        return (
            <div data-testid="react-flow-mock">
                {nodes?.map((node: any) => (
                    <div
                        key={node.id}
                        data-testid={`flow-node-${node.id}`}
                        onClick={(e) => onNodeClick?.(e, node)}
                    >
                        {AgentNode && <AgentNode id={node.id} data={node.data} type={node.type} />}
                    </div>
                ))}
                {edges?.map((edge: any) => (
                    <div key={edge.id} data-testid={`flow-edge-${edge.id}`} />
                ))}
            </div>
        );
    };

    const Handle = ({ type, position }: any) => (
        <div data-testid={`handle-${type}-${position}`} />
    );

    const ReactFlowProvider = ({ children }: any) => <div>{children}</div>;

    return {
        __esModule: true,
        default: ReactFlow,
        Handle,
        ReactFlowProvider,
        Position: { Top: 'top', Bottom: 'bottom', Left: 'left', Right: 'right' },
    };
});

const createStep = (overrides: Partial<TraceStep> = {}): TraceStep => ({
    node: 'test_agent',
    action: 'Process query',
    durationMs: 120,
    confidence: 'high',
    status: 'completed',
    inputSummary: 'User query about pricing',
    outputSummary: 'Analysis result with recommendations',
    ...overrides,
});

describe('AgentFlowChart', () => {
    it('renders empty state when no trace steps', () => {
        render(<AgentFlowChart traceSteps={[]} />);
        expect(screen.getByTestId('empty-flow')).toBeTruthy();
        expect(screen.getByText(/No agent trace steps available/)).toBeTruthy();
    });

    it('renders the flow chart container with steps', () => {
        const steps = [
            createStep({ node: 'router', action: 'Classify domain' }),
            createStep({ node: 'causal_agent', action: 'Run analysis' }),
        ];
        render(<AgentFlowChart traceSteps={steps} />);
        expect(screen.getByTestId('agent-flow-chart')).toBeTruthy();
    });

    it('renders nodes for each trace step', () => {
        const steps = [
            createStep({ node: 'router', durationMs: 50 }),
            createStep({ node: 'mesh', durationMs: 200 }),
            createStep({ node: 'guardian', durationMs: 30 }),
        ];
        render(<AgentFlowChart traceSteps={steps} />);

        expect(screen.getByTestId('agent-node-0')).toBeTruthy();
        expect(screen.getByTestId('agent-node-1')).toBeTruthy();
        expect(screen.getByTestId('agent-node-2')).toBeTruthy();
    });

    it('displays status badges with correct status text', () => {
        const steps = [
            createStep({ node: 'router', status: 'completed' }),
            createStep({ node: 'analyzer', status: 'failed' }),
            createStep({ node: 'guardian', status: 'in-progress' }),
        ];
        render(<AgentFlowChart traceSteps={steps} />);

        expect(screen.getByTestId('status-badge-0').textContent).toBe('completed');
        expect(screen.getByTestId('status-badge-1').textContent).toBe('failed');
        expect(screen.getByTestId('status-badge-2').textContent).toBe('in-progress');
    });

    it('shows duration in ms for each node', () => {
        const steps = [
            createStep({ durationMs: 42 }),
            createStep({ durationMs: 350 }),
        ];
        render(<AgentFlowChart traceSteps={steps} />);

        expect(screen.getByTestId('duration-0').textContent).toBe('42ms');
        expect(screen.getByTestId('duration-1').textContent).toBe('350ms');
    });

    it('renders edges between nodes', () => {
        const steps = [
            createStep({ node: 'step1' }),
            createStep({ node: 'step2' }),
            createStep({ node: 'step3' }),
        ];
        render(<AgentFlowChart traceSteps={steps} />);

        expect(screen.getByTestId('flow-edge-edge-0')).toBeTruthy();
        expect(screen.getByTestId('flow-edge-edge-1')).toBeTruthy();
    });

    it('shows detail panel when a node is clicked', () => {
        const steps = [
            createStep({
                node: 'router',
                action: 'Classify domain',
                inputSummary: 'Full input text for testing',
                outputSummary: 'Full output text for testing',
            }),
        ];
        render(<AgentFlowChart traceSteps={steps} />);

        // Detail panel should not be visible initially
        expect(screen.queryByTestId('detail-panel')).toBeNull();

        // Click the node
        fireEvent.click(screen.getByTestId('flow-node-step-0'));

        // Detail panel should now be visible
        expect(screen.getByTestId('detail-panel')).toBeTruthy();
        expect(screen.getByText('Full input text for testing')).toBeTruthy();
        expect(screen.getByText('Full output text for testing')).toBeTruthy();
    });

    it('hides detail panel when close button is clicked', () => {
        const steps = [createStep({ node: 'router' })];
        render(<AgentFlowChart traceSteps={steps} />);

        // Open detail panel
        fireEvent.click(screen.getByTestId('flow-node-step-0'));
        expect(screen.getByTestId('detail-panel')).toBeTruthy();

        // Close detail panel
        fireEvent.click(screen.getByLabelText('Close detail panel'));
        expect(screen.queryByTestId('detail-panel')).toBeNull();
    });

    it('toggles detail panel when same node is clicked twice', () => {
        const steps = [createStep({ node: 'router' })];
        render(<AgentFlowChart traceSteps={steps} />);

        // Open
        fireEvent.click(screen.getByTestId('flow-node-step-0'));
        expect(screen.getByTestId('detail-panel')).toBeTruthy();

        // Close by clicking same node
        fireEvent.click(screen.getByTestId('flow-node-step-0'));
        expect(screen.queryByTestId('detail-panel')).toBeNull();
    });

    it('shows "No input data" when inputSummary is undefined', () => {
        const steps = [createStep({ inputSummary: undefined, outputSummary: undefined })];
        render(<AgentFlowChart traceSteps={steps} />);

        // Click to expand
        fireEvent.click(screen.getByTestId('flow-node-step-0'));
        expect(screen.getByText('No input data')).toBeTruthy();
        expect(screen.getByText('No output data')).toBeTruthy();
    });
});
