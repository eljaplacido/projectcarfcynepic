import { useState, useEffect } from 'react';
// Replaced lucide-react with emojis/SVGs to match project dependencies
import SemanticGraphView from './SemanticGraphView';

/**
 * DataLayerInspector Component
 * 
 * Provides transparent access to the underlying data layers of the CARF architecture:
 * 1. Structured Data (CSV/SQL) - Raw dataset inspection
 * 2. Semantic Graph (Neo4j) - Causal relationships and ontology
 * 3. Operational Data (Kafka/Logs) - Audit trail and lineage
 * 
 * Part of Week 2: Developer Transparency Window
 */

interface DatasetPreview {
    dataset_id: string;
    rows: Record<string, any>[];
    columns: string[];
    total_rows: number;
}

interface DataLayerInspectorProps {
    className?: string;
    context?: any; // Current analysis context to auto-filter data
}

const DataLayerInspector: React.FC<DataLayerInspectorProps> = ({ className = '', context }) => {
    const [activeTab, setActiveTab] = useState<'structured' | 'semantic' | 'operational'>('structured');
    const [isLoading, setIsLoading] = useState(false);
    const [datasets, setDatasets] = useState<any[]>([]);
    const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
    const [previewData, setPreviewData] = useState<DatasetPreview | null>(null);

    // Mock initial load (replace with API calls later)
    useEffect(() => {
        // In a real implementation, this would fetch from /api/datasets
        setDatasets([
            { id: 'scope3_emissions', name: 'Scope 3 Emissions (Gold Standard)', type: 'csv', rows: 2000, lastUpdated: '2026-01-30' },
            { id: 'supplier_risk', name: 'Supplier Risk Profile', type: 'sql', rows: 540, lastUpdated: '2026-01-28' },
            { id: 'grid_stability', name: 'Energy Grid Telemetry', type: 'timeseries', rows: 15000, lastUpdated: 'Live' },
        ]);
        setSelectedDataset('scope3_emissions');
    }, []);

    // Load dataset preview when selected
    useEffect(() => {
        if (!selectedDataset) return;

        setIsLoading(true);
        // Simulate API delay
        setTimeout(() => {
            // Mock data for Scope 3 - mirroring the generated CSV structure
            if (selectedDataset === 'scope3_emissions') {
                setPreviewData({
                    dataset_id: 'scope3_emissions',
                    columns: ['supplier_id', 'timestamp', 'category', 'supplier_program', 'scope3_emissions', 'region', 'confidence_score'],
                    total_rows: 2000,
                    rows: Array.from({ length: 15 }).map((_, i) => ({
                        supplier_id: `SUP-${1000 + i}`,
                        timestamp: new Date(Date.now() - i * 86400000).toISOString().split('T')[0],
                        category: ['Cat1_Purchased_Goods', 'Cat4_Transport', 'Cat6_Business_Travel'][i % 3],
                        supplier_program: Math.random() > 0.5 ? 1 : 0,
                        scope3_emissions: (150 - Math.random() * 50).toFixed(2),
                        region: ['EU', 'NA', 'APAC'][i % 3],
                        confidence_score: (0.8 + Math.random() * 0.19).toFixed(2)
                    }))
                });
            } else {
                setPreviewData(null);
            }
            setIsLoading(false);
        }, 600);
    }, [selectedDataset]);

    const renderStructuredView = () => (
        <div className="space-y-4 h-full flex flex-col">
            {/* Dataset Selector */}
            <div className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg border border-gray-200">
                <span className="text-gray-500">🗄️</span>
                <span className="text-xs font-medium text-gray-700">Active Dataset:</span>
                <select
                    value={selectedDataset || ''}
                    onChange={(e) => setSelectedDataset(e.target.value)}
                    className="flex-1 text-xs border-none bg-transparent focus:ring-0 text-gray-900 font-medium"
                >
                    {datasets.map(d => (
                        <option key={d.id} value={d.id}>{d.name} ({d.rows} rows)</option>
                    ))}
                </select>
                <div className="flex gap-1">
                    <button className="p-1 hover:bg-gray-200 rounded" title="Filter">
                        <span className="text-gray-500 text-xs">🌪️</span>
                    </button>
                    <button className="p-1 hover:bg-gray-200 rounded" title="Export">
                        <span className="text-gray-500 text-xs">⬇️</span>
                    </button>
                    <button className="p-1 hover:bg-gray-200 rounded" title="Query SQL">
                        <span className="text-gray-500 text-xs">🔍</span>
                    </button>
                </div>
            </div>

            {/* Data Table */}
            <div className="flex-1 border border-gray-200 rounded-lg overflow-hidden bg-white relative">
                {isLoading && (
                    <div className="absolute inset-0 bg-white/50 flex items-center justify-center z-10">
                        <div className="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full" />
                    </div>
                )}

                {previewData ? (
                    <div className="h-full overflow-auto">
                        <table className="w-full text-xs text-left">
                            <thead className="bg-gray-50 sticky top-0 z-0">
                                <tr>
                                    {previewData.columns.map(col => (
                                        <th key={col} className="px-3 py-2 font-medium text-gray-600 border-b border-gray-200 whitespace-nowrap">
                                            {col}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {previewData.rows.map((row, idx) => (
                                    <tr key={idx} className="hover:bg-blue-50/30 font-mono text-gray-600">
                                        {previewData.columns.map(col => (
                                            <td key={col} className="px-3 py-1.5 whitespace-nowrap">
                                                {row[col]}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-gray-400">
                        <span className="text-4xl mb-2 opacity-50">🗄️</span>
                        <span className="text-xs">Select a dataset to inspect</span>
                    </div>
                )}
            </div>

            {/* Pagination / Stats */}
            <div className="flex justify-between items-center text-[10px] text-gray-500">
                <span>Showing 1-{previewData?.rows.length || 0} of {previewData?.total_rows || 0} records</span>
                <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                    Live Connection
                </span>
            </div>
        </div>
    );

    const renderSemanticView = () => (
        <div className="h-full">
            <SemanticGraphView context={context} />
        </div>
    );

    const renderOperationalView = () => (
        <div className="h-full flex flex-col">
            <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-700">Audit Trail (Kafka)</span>
                <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded">Connected</span>
            </div>
            <div className="flex-1 bg-gray-900 rounded-lg p-3 font-mono text-xs overflow-y-auto space-y-1">
                <div className="text-gray-500 border-l-2 border-gray-700 pl-2">
                    <span className="text-blue-400">10:42:15.003</span> [INGEST] Dataset upload 'scope3_emissions.csv'
                </div>
                <div className="text-gray-500 border-l-2 border-gray-700 pl-2">
                    <span className="text-blue-400">10:42:15.240</span> [ROUTER] Classified session 5a2... as 'Complicated'
                </div>
                <div className="text-gray-400 border-l-2 border-yellow-600 pl-2 bg-yellow-900/10">
                    <span className="text-blue-400">10:42:16.112</span> [GUARDIAN] Policy check: APPROVED (Risk: Low)
                </div>
                <div className="text-gray-500 border-l-2 border-gray-700 pl-2">
                    <span className="text-blue-400">10:42:16.450</span> [OUTPUT] Generated response with 3 recommendations
                </div>
            </div>
        </div>
    );

    return (
        <div className={`flex flex-col h-full bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
            {/* Header / Tabs */}
            <div className="flex border-b border-gray-200">
                <button
                    onClick={() => setActiveTab('structured')}
                    className={`flex-1 py-2 text-xs font-medium flex items-center justify-center gap-1.5 border-b-2 transition-colors ${activeTab === 'structured' ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                >
                    <span className="text-xs">🗄️</span>
                    Structured
                </button>
                <button
                    onClick={() => setActiveTab('semantic')}
                    className={`flex-1 py-2 text-xs font-medium flex items-center justify-center gap-1.5 border-b-2 transition-colors ${activeTab === 'semantic' ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                >
                    <span className="text-xs">🕸️</span>
                    Semantic Graph
                </button>
                <button
                    onClick={() => setActiveTab('operational')}
                    className={`flex-1 py-2 text-xs font-medium flex items-center justify-center gap-1.5 border-b-2 transition-colors ${activeTab === 'operational' ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                >
                    <span className="text-xs">⚙️</span>
                    Operational
                </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 p-3 overflow-hidden">
                {activeTab === 'structured' && renderStructuredView()}
                {activeTab === 'semantic' && renderSemanticView()}
                {activeTab === 'operational' && renderOperationalView()}
            </div>
        </div>
    );
};

export default DataLayerInspector;
