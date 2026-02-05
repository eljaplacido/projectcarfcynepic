import React, { useCallback } from 'react';
import ReactFlow, {
    MiniMap,
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    addEdge,
    type Connection,
    type Edge,
    type Node,
    MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

/**
 * SemanticGraphView Component
 * 
 * Visualizes the causal semantic graph (Knowledge Graph) stored in Neo4j.
 * Uses React Flow to render nodes (entities) and edges (relationships).
 * 
 * Features:
 * - Color-coded nodes by type (Treatment, Outcome, Confounder)
 * - Weighted edges based on causal strength
 * - Interactive zooming and panning
 */

interface GraphNode extends Node {
    data: { label: string; type: string; value?: string | number };
}

interface SemanticGraphViewProps {
    className?: string;
}

// Initial mock data simulating a Neo4j query result for Scope 3
const initialNodes: GraphNode[] = [
    {
        id: 'treatment',
        type: 'input',
        position: { x: 250, y: 50 },
        data: { label: 'Supplier Program', type: 'treatment' },
        style: { background: '#dbeafe', border: '2px solid #3b82f6', borderRadius: '8px', padding: '10px', width: 150 }
    },
    {
        id: 'outcome',
        position: { x: 250, y: 300 },
        data: { label: 'Scope 3 Emissions', type: 'outcome' },
        style: { background: '#dcfce7', border: '2px solid #22c55e', borderRadius: '8px', padding: '10px', width: 150 }
    },
    {
        id: 'confounder1',
        position: { x: 50, y: 150 },
        data: { label: 'Supplier Size', type: 'confounder' },
        style: { background: '#fef3c7', border: '1px dashed #f59e0b', borderRadius: '50%', padding: '15px', width: 100, height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', textAlign: 'center' }
    },
    {
        id: 'confounder2',
        position: { x: 450, y: 150 },
        data: { label: 'Region (EU)', type: 'modifier' }, // Effect modifier
        style: { background: '#f3e8ff', border: '1px dashed #a855f7', borderRadius: '8px', padding: '10px', width: 120 }
    },
    {
        id: 'mediator',
        position: { x: 250, y: 180 },
        data: { label: 'Energy Efficiency', type: 'mediator' },
        style: { background: '#f3f4f6', border: '1px solid #9ca3af', borderRadius: '8px', padding: '8px', width: 140, fontSize: '11px' }
    },
];

const initialEdges: Edge[] = [
    {
        id: 'e1-2',
        source: 'treatment',
        target: 'mediator',
        animated: true,
        label: '+ Efficiency',
        style: { stroke: '#3b82f6' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' }
    },
    {
        id: 'e2-3',
        source: 'mediator',
        target: 'outcome',
        label: '- Emissions',
        style: { stroke: '#22c55e', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#22c55e' }
    },
    {
        id: 'e3-1',
        source: 'confounder1',
        target: 'treatment',
        label: 'Adoption Rate',
        style: { stroke: '#f59e0b', strokeDasharray: '5,5' },
        markerEnd: { type: MarkerType.ArrowClosed }
    },
    {
        id: 'e3-2',
        source: 'confounder1',
        target: 'outcome',
        style: { stroke: '#f59e0b', strokeDasharray: '5,5' },
        markerEnd: { type: MarkerType.ArrowClosed }
    },
    {
        id: 'e4-2',
        source: 'confounder2',
        target: 'outcome',
        label: 'Regulation',
        style: { stroke: '#a855f7' },
        markerEnd: { type: MarkerType.ArrowClosed }
    },
];

const SemanticGraphView: React.FC<SemanticGraphViewProps> = ({ className = '' }) => {
    const [nodes, , onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    // In a real implementation, we would fetch graph data based on context.id
    // useEffect(() => { ... fetch from /api/neo4j/graph ... }, [context]);

    const onConnect = useCallback((params: Connection) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

    return (
        <div className={`h-full flex flex-col ${className}`}>
            <div className="flex justify-between items-center mb-2 px-2">
                <div className="flex items-center gap-2">
                    <span className="text-purple-600">🕸️</span>
                    <h3 className="text-xs font-semibold text-gray-800">Causal Knowledge Graph (Neo4j)</h3>
                </div>
                <div className="flex gap-1">
                    <button className="p-1 hover:bg-gray-100 rounded text-gray-500" title="Fit View">
                        <span className="text-xs">⛶</span>
                    </button>
                </div>
            </div>

            <div className="flex-1 border border-gray-200 rounded-lg overflow-hidden bg-white shadow-inner relative">
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    fitView
                    attributionPosition="bottom-right"
                >
                    <Background color="#ccc" gap={20} />
                    <Controls showInteractive={false} className="scale-75 origin-bottom-left" />
                    <MiniMap
                        nodeStrokeColor={(n) => {
                            if (n.type === 'input') return '#0041d0';
                            if (n.type === 'output') return '#ff0072';
                            if (n.type === 'default') return '#1a192b';
                            return '#eee';
                        }}
                        nodeColor={(n) => {
                            if (n.style?.background) return n.style.background as string;
                            return '#fff';
                        }}
                        nodeBorderRadius={2}
                        className="scale-75 origin-bottom-right"
                    />
                </ReactFlow>

                {/* Graph Legend Overlay */}
                <div className="absolute top-2 right-2 bg-white/90 p-2 rounded shadow border border-gray-100 text-[10px] space-y-1">
                    <div className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-blue-100 border border-blue-400 rounded-sm"></span>
                        <span>Treatment</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-green-100 border border-green-400 rounded-sm"></span>
                        <span>Outcome</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-yellow-100 border border-yellow-400 rounded-full"></span>
                        <span>Confounder</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SemanticGraphView;
