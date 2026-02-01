import React, { useState, useCallback } from 'react';

interface ColumnInfo {
    name: string;
    type: 'numeric' | 'categorical' | 'binary' | 'text' | 'unknown';
    uniqueValues?: number;
    sampleValues?: string[];
}

interface DataPreview {
    fileName: string;
    rows: number;
    columns: ColumnInfo[];
    sampleData: Record<string, unknown>[];
}

interface SchemaDetectionColumn {
    name: string;
    dtype: string;
    sample_values: string[];
    suggested_role?: 'treatment' | 'outcome' | 'covariate' | 'id' | null;
}

interface SchemaDetectionResult {
    columns: SchemaDetectionColumn[];
    row_count: number;
    has_header: boolean;
}

type AnalysisType = 'causal' | 'bayesian' | 'auto';

interface DataOnboardingWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onComplete: (config: {
        dataPreview: DataPreview;
        analysisType: AnalysisType;
        treatment?: string;
        outcome?: string;
        covariates?: string[];
        query: string;
    }) => void;
}

const STEPS = [
    { id: 1, title: 'Upload', subtitle: 'Upload Your Data' },
    { id: 2, title: 'Preview', subtitle: 'Review Your Data' },
    { id: 3, title: 'Type', subtitle: 'Analysis Type' },
    { id: 4, title: 'Variables', subtitle: 'Configure Variables' },
    { id: 5, title: 'Question', subtitle: 'Compose Question' },
];

// Sample datasets for demo/learning
const SAMPLE_DATASETS = [
    {
        id: 'churn',
        name: 'Customer Churn',
        description: 'Telecom customer churn data with treatment (discount) and outcome (churn)',
        rows: 1000,
        suggestedTreatment: 'received_discount',
        suggestedOutcome: 'churned',
    },
    {
        id: 'healthcare',
        name: 'Healthcare Outcomes',
        description: 'Patient treatment data for causal analysis of intervention effectiveness',
        rows: 500,
        suggestedTreatment: 'treatment_type',
        suggestedOutcome: 'recovery_days',
    },
    {
        id: 'marketing',
        name: 'Marketing Campaign',
        description: 'A/B test data for marketing campaign effectiveness',
        rows: 2000,
        suggestedTreatment: 'campaign_variant',
        suggestedOutcome: 'conversion',
    },
];

// Variable suggestions logic moved to processFile heuristic for now

const DataOnboardingWizard: React.FC<DataOnboardingWizardProps> = ({
    isOpen,
    onClose,
    onComplete,
}) => {
    const [currentStep, setCurrentStep] = useState(1);
    const [dataPreview, setDataPreview] = useState<DataPreview | null>(null);
    const [analysisType, setAnalysisType] = useState<AnalysisType>('auto');
    const [treatment, setTreatment] = useState<string>('');
    const [outcome, setOutcome] = useState<string>('');
    const [covariates, setCovariates] = useState<string[]>([]);
    const [query, setQuery] = useState<string>('');
    const [isDragging, setIsDragging] = useState(false);
    const [showSampleData, setShowSampleData] = useState(false);
    const [suggestions, setSuggestions] = useState<{ treatment: string | null; outcome: string | null; covariates: string[] }>({
        treatment: null,
        outcome: null,
        covariates: [],
    });

    const detectColumnType = (values: unknown[]): ColumnInfo['type'] => {
        const nonNull = values.filter(v => v !== null && v !== undefined && v !== '');
        if (nonNull.length === 0) return 'unknown';

        const uniqueValues = new Set(nonNull);
        if (uniqueValues.size === 2) {
            const arr = Array.from(uniqueValues);
            if (arr.every(v => [0, 1, '0', '1', true, false, 'true', 'false', 'yes', 'no'].includes(v as string | number | boolean))) {
                return 'binary';
            }
        }

        if (nonNull.every(v => typeof v === 'number' || !isNaN(Number(v)))) {
            return 'numeric';
        }

        if (uniqueValues.size <= 20 && uniqueValues.size < nonNull.length * 0.5) {
            return 'categorical';
        }

        return 'text';
    };

    const parseCSV = (text: string): Record<string, unknown>[] => {
        const lines = text.trim().split('\n');
        if (lines.length < 2) return [];

        const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
        return lines.slice(1).map(line => {
            const values = line.split(',').map(v => v.trim().replace(/"/g, ''));
            const row: Record<string, unknown> = {};
            headers.forEach((header, i) => {
                const val = values[i];
                row[header] = val === '' ? null : isNaN(Number(val)) ? val : Number(val);
            });
            return row;
        });
    };

    const processFile = async (file: File) => {
        try {
            // Use Backend API for Intelligent Schema Detection
            const formData = new FormData();
            formData.append('file', file);

            let backendSuggestions: typeof suggestions | null = null;
            try {
                const res = await fetch('http://localhost:8000/data/detect-schema', { method: 'POST', body: formData });
                if (res.ok) {
                    const result: SchemaDetectionResult = await res.json();
                    backendSuggestions = buildSuggestionsFromSchema(result);
                } else {
                    console.warn('Schema detection failed with status:', res.status);
                }
            } catch (err) {
                console.warn('Schema detection request failed, falling back to local heuristics.', err);
            }

            // Local Fallback (mimicking backend logic for reliability in this demo environment)
            const text = await file.text();
            let data: Record<string, unknown>[];

            if (file.name.endsWith('.json')) {
                data = JSON.parse(text);
            } else if (file.name.endsWith('.csv')) {
                data = parseCSV(text);
            } else {
                throw new Error('Unsupported file type. Use CSV or JSON.');
            }

            if (data.length === 0) throw new Error('File contains no data');
            if (data.length > 5000) data = data.slice(0, 5000); // Front-end limiting

            const columnNames = Object.keys(data[0]);
            const columns: ColumnInfo[] = columnNames.map(name => {
                const values = data.map(row => row[name]);
                return {
                    name,
                    type: detectColumnType(values),
                    uniqueValues: new Set(values.filter(v => v !== null)).size,
                    sampleValues: Array.from(new Set(values.filter(v => v !== null))).slice(0, 5).map(String)
                };
            });

            const preview: DataPreview = {
                fileName: file.name,
                rows: data.length,
                columns,
                sampleData: data.slice(0, 5),
            };

            setDataPreview(preview);

            const fallbackSuggestions = buildSuggestionsFromColumns(columnNames, columns);
            setSuggestions(backendSuggestions ?? fallbackSuggestions);
            setCurrentStep(2);

        } catch (err) {
            console.error(err);
            alert('Failed to process file');
        }
    };

    // Load sample dataset
    const loadSampleDataset = (datasetId: string) => {
        const dataset = SAMPLE_DATASETS.find(d => d.id === datasetId);
        if (!dataset) return;

        // Generate mock data based on dataset type
        const mockColumns: ColumnInfo[] = [];
        const mockData: Record<string, unknown>[] = [];

        if (datasetId === 'churn') {
            mockColumns.push(
                { name: 'customer_id', type: 'text', uniqueValues: 1000, sampleValues: ['C001', 'C002', 'C003'] },
                { name: 'tenure', type: 'numeric', uniqueValues: 72, sampleValues: ['12', '24', '36', '48'] },
                { name: 'received_discount', type: 'binary', uniqueValues: 2, sampleValues: ['0', '1'] },
                { name: 'churned', type: 'binary', uniqueValues: 2, sampleValues: ['0', '1'] },
                { name: 'monthly_charges', type: 'numeric', uniqueValues: 500, sampleValues: ['29.99', '49.99', '79.99'] },
                { name: 'age', type: 'numeric', uniqueValues: 50, sampleValues: ['25', '35', '45', '55'] },
            );
            for (let i = 0; i < 5; i++) {
                mockData.push({
                    customer_id: `C00${i + 1}`,
                    tenure: Math.floor(Math.random() * 72) + 1,
                    received_discount: Math.random() > 0.5 ? 1 : 0,
                    churned: Math.random() > 0.7 ? 1 : 0,
                    monthly_charges: Math.round((Math.random() * 80 + 20) * 100) / 100,
                    age: Math.floor(Math.random() * 40) + 20,
                });
            }
        } else if (datasetId === 'marketing') {
            mockColumns.push(
                { name: 'user_id', type: 'text', uniqueValues: 2000, sampleValues: ['U001', 'U002', 'U003'] },
                { name: 'campaign_variant', type: 'categorical', uniqueValues: 3, sampleValues: ['control', 'variant_a', 'variant_b'] },
                { name: 'conversion', type: 'binary', uniqueValues: 2, sampleValues: ['0', '1'] },
                { name: 'time_on_site', type: 'numeric', uniqueValues: 500, sampleValues: ['30', '120', '300'] },
                { name: 'previous_purchases', type: 'numeric', uniqueValues: 10, sampleValues: ['0', '1', '2', '5'] },
            );
            for (let i = 0; i < 5; i++) {
                mockData.push({
                    user_id: `U00${i + 1}`,
                    campaign_variant: ['control', 'variant_a', 'variant_b'][Math.floor(Math.random() * 3)],
                    conversion: Math.random() > 0.85 ? 1 : 0,
                    time_on_site: Math.floor(Math.random() * 300) + 30,
                    previous_purchases: Math.floor(Math.random() * 5),
                });
            }
        } else {
            mockColumns.push(
                { name: 'patient_id', type: 'text', uniqueValues: 500, sampleValues: ['P001', 'P002', 'P003'] },
                { name: 'treatment_type', type: 'categorical', uniqueValues: 2, sampleValues: ['standard', 'experimental'] },
                { name: 'recovery_days', type: 'numeric', uniqueValues: 30, sampleValues: ['7', '14', '21', '28'] },
                { name: 'age', type: 'numeric', uniqueValues: 50, sampleValues: ['30', '45', '60'] },
                { name: 'severity', type: 'categorical', uniqueValues: 3, sampleValues: ['mild', 'moderate', 'severe'] },
            );
            for (let i = 0; i < 5; i++) {
                mockData.push({
                    patient_id: `P00${i + 1}`,
                    treatment_type: Math.random() > 0.5 ? 'experimental' : 'standard',
                    recovery_days: Math.floor(Math.random() * 21) + 7,
                    age: Math.floor(Math.random() * 40) + 30,
                    severity: ['mild', 'moderate', 'severe'][Math.floor(Math.random() * 3)],
                });
            }
        }

        const preview: DataPreview = {
            fileName: `${dataset.name} (Sample)`,
            rows: dataset.rows,
            columns: mockColumns,
            sampleData: mockData,
        };

        setDataPreview(preview);
        setSuggestions({
            treatment: dataset.suggestedTreatment,
            outcome: dataset.suggestedOutcome,
            covariates: [],
        });
        setShowSampleData(false);
        setCurrentStep(2);
    };

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const file = e.dataTransfer.files[0];
        if (file) {
            processFile(file);
        }
    }, []);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            processFile(file);
        }
    };

    const handleCovariateToggle = (column: string) => {
        setCovariates(prev =>
            prev.includes(column)
                ? prev.filter(c => c !== column)
                : [...prev, column]
        );
    };

    const buildSuggestionsFromSchema = (schema: SchemaDetectionResult): typeof suggestions => {
        const newSuggestions: typeof suggestions = { treatment: null, outcome: null, covariates: [] };
        schema.columns.forEach((column) => {
            switch (column.suggested_role) {
                case 'treatment':
                    if (!newSuggestions.treatment) newSuggestions.treatment = column.name;
                    break;
                case 'outcome':
                    if (!newSuggestions.outcome) newSuggestions.outcome = column.name;
                    break;
                case 'covariate':
                    if (!newSuggestions.covariates.includes(column.name)) {
                        newSuggestions.covariates.push(column.name);
                    }
                    break;
                default:
                    break;
            }
        });
        return newSuggestions;
    };

    const buildSuggestionsFromColumns = (columnNames: string[], columns: ColumnInfo[]): typeof suggestions => {
        const newSuggestions: typeof suggestions = { treatment: null, outcome: null, covariates: [] };

        columnNames.forEach(col => {
            const lower = col.toLowerCase();
            if (['treatment', 'intervention', 'variant', 'group'].some(k => lower.includes(k))) {
                if (!newSuggestions.treatment) newSuggestions.treatment = col;
            }
            if (['outcome', 'result', 'converted', 'conversion', 'revenue', 'sales', 'churn', 'score', 'cost'].some(k => lower.includes(k))) {
                if (!newSuggestions.outcome) newSuggestions.outcome = col;
            }
            if (!lower.includes('id') && !lower.includes('uuid')) {
                const colInfo = columns.find(c => c.name === col);
                if (colInfo?.type !== 'text') {
                    newSuggestions.covariates.push(col);
                }
            }
        });

        return newSuggestions;
    };

    const generateQuery = () => {
        if (analysisType === 'causal' && treatment && outcome) {
            return `What is the causal effect of ${treatment} on ${outcome}?`;
        }
        if (analysisType === 'bayesian') {
            return `What is the probability distribution of ${outcome || 'the target variable'}?`;
        }
        return '';
    };

    const handleComplete = () => {
        if (dataPreview) {
            onComplete({
                dataPreview,
                analysisType,
                treatment: treatment || undefined,
                outcome: outcome || undefined,
                covariates: covariates.length > 0 ? covariates : undefined,
                query: query || generateQuery(),
            });
        }
    };

    if (!isOpen) return null;

    const getTypeIcon = (type: ColumnInfo['type']) => {
        switch (type) {
            case 'numeric': return '🔢';
            case 'categorical': return '📋';
            case 'binary': return '⚡';
            case 'text': return '📝';
            default: return '❓';
        }
    };

    const getTypeLabel = (type: ColumnInfo['type']) => {
        switch (type) {
            case 'numeric': return 'Numeric';
            case 'categorical': return 'Categorical';
            case 'binary': return 'Binary';
            case 'text': return 'Text';
            default: return 'Unknown';
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header with Steps */}
                <div className="p-6 border-b border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-bold text-gray-900">Data Onboarding</h2>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Step Progress */}
                    <div className="flex items-center justify-between">
                        {STEPS.map((step, idx) => (
                            <React.Fragment key={step.id}>
                                <div className="flex items-center gap-2">
                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${currentStep >= step.id
                                        ? 'bg-primary text-white'
                                        : 'bg-gray-200 text-gray-500'
                                        }`}>
                                        {currentStep > step.id ? '✓' : step.id}
                                    </div>
                                    <div className="hidden sm:block">
                                        <div className={`text-sm font-medium ${currentStep >= step.id ? 'text-gray-900' : 'text-gray-500'}`}>
                                            {step.title}
                                        </div>
                                    </div>
                                </div>
                                {idx < STEPS.length - 1 && (
                                    <div className={`flex-grow h-0.5 mx-2 ${currentStep > step.id ? 'bg-primary' : 'bg-gray-200'}`} />
                                )}
                            </React.Fragment>
                        ))}
                    </div>
                </div>

                {/* Content */}
                <div className="flex-grow overflow-y-auto p-6">
                    {/* Step 1: Upload */}
                    {currentStep === 1 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-gray-900">Upload Your Data</h3>
                            <p className="text-sm text-gray-600">
                                Upload a CSV or JSON file with your analysis data. Maximum 5,000 rows recommended.
                            </p>

                            <div
                                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${isDragging ? 'border-primary bg-primary/5' : 'border-gray-300 hover:border-primary/50'
                                    }`}
                                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                                onDragLeave={() => setIsDragging(false)}
                                onDrop={handleDrop}
                            >
                                <svg className="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                </svg>
                                <p className="text-gray-600 mb-2">Drop CSV or JSON file here</p>
                                <p className="text-sm text-gray-500 mb-4">or</p>
                                <label className="inline-block px-4 py-2 bg-primary text-white rounded-lg cursor-pointer hover:bg-primary-light transition-colors">
                                    Browse Files
                                    <input
                                        type="file"
                                        accept=".csv,.json"
                                        onChange={handleFileSelect}
                                        className="hidden"
                                    />
                                </label>
                            </div>

                            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                <div className="text-sm font-semibold text-blue-900 mb-1">💡 Tip</div>
                                <div className="text-sm text-blue-700">
                                    CYNEPIC works best with 100-5,000 rows of tabular data with clear treatment/outcome variables.
                                    Avoid uploading sensitive personal data.
                                </div>
                            </div>

                            {/* Sample Data Section */}
                            <div className="border-t border-gray-200 pt-4">
                                <button
                                    onClick={() => setShowSampleData(!showSampleData)}
                                    className="flex items-center gap-2 text-sm text-primary hover:text-primary/80"
                                >
                                    <span>{showSampleData ? '▼' : '▶'}</span>
                                    New here? Try a sample dataset
                                </button>

                                {showSampleData && (
                                    <div className="mt-4 grid grid-cols-1 gap-3">
                                        {SAMPLE_DATASETS.map(dataset => (
                                            <button
                                                key={dataset.id}
                                                onClick={() => loadSampleDataset(dataset.id)}
                                                className="text-left p-4 border border-gray-200 rounded-lg hover:border-primary hover:bg-primary/5 transition-colors"
                                            >
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="font-medium text-gray-900">{dataset.name}</span>
                                                    <span className="text-xs text-gray-500">{dataset.rows.toLocaleString()} rows</span>
                                                </div>
                                                <p className="text-sm text-gray-600">{dataset.description}</p>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Preview */}
                    {currentStep === 2 && dataPreview && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-gray-900">Review Your Data</h3>
                            <div className="flex items-center gap-2 text-sm text-gray-600">
                                <span>📊</span>
                                <span className="font-medium">{dataPreview.fileName}</span>
                                <span>—</span>
                                <span>{dataPreview.rows.toLocaleString()} rows × {dataPreview.columns.length} columns</span>
                            </div>

                            {/* Sample Data Table */}
                            <div className="border border-gray-200 rounded-lg overflow-hidden">
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                {dataPreview.columns.map(col => (
                                                    <th key={col.name} className="px-3 py-2 text-left font-medium text-gray-700 border-b">
                                                        {col.name}
                                                    </th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {dataPreview.sampleData.map((row, idx) => (
                                                <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                                    {dataPreview.columns.map(col => (
                                                        <td key={col.name} className="px-3 py-2 border-b border-gray-100">
                                                            {String(row[col.name] ?? '')}
                                                        </td>
                                                    ))}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Column Types */}
                            <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-2">Column Types Detected:</h4>
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                                    {dataPreview.columns.map(col => (
                                        <div key={col.name} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg text-sm">
                                            <span>{getTypeIcon(col.type)}</span>
                                            <span className="font-medium text-gray-900 truncate">{col.name}</span>
                                            <span className="text-xs text-gray-500">({getTypeLabel(col.type)})</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Variable Relationship Graph */}
                            <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
                                    <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                                    </svg>
                                    Detected Variable Relationships
                                </h4>
                                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                                    {/* Simple Relationship Network View */}
                                    <div className="flex flex-wrap gap-3 items-center justify-center min-h-[120px]">
                                        {dataPreview.columns.filter(c => c.type === 'numeric').map((col) => (
                                            <div
                                                key={col.name}
                                                className="flex flex-col items-center gap-1"
                                            >
                                                <div className={`w-12 h-12 rounded-full ${treatment === col.name ? 'bg-blue-500' :
                                                    outcome === col.name ? 'bg-green-500' :
                                                        covariates.includes(col.name) ? 'bg-purple-400' :
                                                            'bg-gray-300'
                                                    } flex items-center justify-center text-white text-[10px] font-semibold cursor-pointer hover:scale-110 transition-transform`}
                                                    title={`${col.name}: Click to view details`}
                                                >
                                                    {col.name.slice(0, 3).toUpperCase()}
                                                </div>
                                                <span className="text-[10px] text-gray-600 truncate max-w-[70px]">{col.name}</span>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Legend */}
                                    <div className="mt-4 flex flex-wrap justify-center gap-4 text-xs">
                                        <div className="flex items-center gap-1">
                                            <span className="w-3 h-3 rounded-full bg-blue-500" />
                                            <span className="text-gray-600">Treatment</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <span className="w-3 h-3 rounded-full bg-green-500" />
                                            <span className="text-gray-600">Outcome</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <span className="w-3 h-3 rounded-full bg-purple-400" />
                                            <span className="text-gray-600">Covariate</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <span className="w-3 h-3 rounded-full bg-gray-300" />
                                            <span className="text-gray-600">Unassigned</span>
                                        </div>
                                    </div>

                                    {/* Tip */}
                                    <p className="text-[10px] text-gray-500 text-center mt-3">
                                        💡 Assign variable roles in Step 4 to see relationships
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 3: Analysis Type */}
                    {currentStep === 3 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-gray-900">What type of analysis?</h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <button
                                    onClick={() => setAnalysisType('causal')}
                                    className={`text-left p-5 rounded-xl border-2 transition-all ${analysisType === 'causal'
                                        ? 'border-primary bg-primary/5'
                                        : 'border-gray-200 hover:border-gray-300'
                                        }`}
                                >
                                    <div className="text-3xl mb-3">📈</div>
                                    <div className="font-semibold text-gray-900 mb-1">Causal Analysis</div>
                                    <div className="text-sm text-gray-600 mb-3">
                                        "What is the effect of X on Y?"
                                    </div>
                                    <div className="text-xs text-gray-500">
                                        Best for: A/B tests, interventions, policy evaluation
                                    </div>
                                </button>

                                <button
                                    onClick={() => setAnalysisType('bayesian')}
                                    className={`text-left p-5 rounded-xl border-2 transition-all ${analysisType === 'bayesian'
                                        ? 'border-primary bg-primary/5'
                                        : 'border-gray-200 hover:border-gray-300'
                                        }`}
                                >
                                    <div className="text-3xl mb-3">🎲</div>
                                    <div className="font-semibold text-gray-900 mb-1">Bayesian Inference</div>
                                    <div className="text-sm text-gray-600 mb-3">
                                        "What is my belief about parameter?"
                                    </div>
                                    <div className="text-xs text-gray-500">
                                        Best for: rates, proportions, uncertainty quantification
                                    </div>
                                </button>
                            </div>

                            <div className="text-center">
                                <button
                                    onClick={() => setAnalysisType('auto')}
                                    className={`text-sm ${analysisType === 'auto' ? 'text-primary font-medium' : 'text-gray-500 hover:text-gray-700'}`}
                                >
                                    🤔 Not sure? Let CARF decide based on my question
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Step 4: Variables */}
                    {currentStep === 4 && dataPreview && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-gray-900">
                                {analysisType === 'causal' ? 'Define Causal Question' : 'Configure Analysis'}
                            </h3>

                            {/* Suggestions Panel */}
                            {(suggestions.treatment || suggestions.outcome || suggestions.covariates.length > 0) && (
                                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                                    <div className="flex items-center gap-2 mb-2">
                                        <span className="text-green-600">✨</span>
                                        <span className="text-sm font-semibold text-green-900">Auto-Detected Suggestions</span>
                                    </div>
                                    <div className="text-sm text-green-800 space-y-1">
                                        {suggestions.treatment && (
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-green-600">Treatment:</span>
                                                <button
                                                    onClick={() => setTreatment(suggestions.treatment!)}
                                                    className={`px-2 py-0.5 rounded text-xs font-medium ${treatment === suggestions.treatment
                                                        ? 'bg-green-600 text-white'
                                                        : 'bg-green-100 text-green-800 hover:bg-green-200'
                                                        }`}
                                                >
                                                    {suggestions.treatment} {treatment === suggestions.treatment && '✓'}
                                                </button>
                                            </div>
                                        )}
                                        {suggestions.outcome && (
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-green-600">Outcome:</span>
                                                <button
                                                    onClick={() => setOutcome(suggestions.outcome!)}
                                                    className={`px-2 py-0.5 rounded text-xs font-medium ${outcome === suggestions.outcome
                                                        ? 'bg-green-600 text-white'
                                                        : 'bg-green-100 text-green-800 hover:bg-green-200'
                                                        }`}
                                                >
                                                    {suggestions.outcome} {outcome === suggestions.outcome && '✓'}
                                                </button>
                                            </div>
                                        )}
                                        {suggestions.covariates.length > 0 && (
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="text-xs text-green-600">Covariates:</span>
                                                {suggestions.covariates.map(cov => (
                                                    <button
                                                        key={cov}
                                                        onClick={() => handleCovariateToggle(cov)}
                                                        className={`px-2 py-0.5 rounded text-xs font-medium ${covariates.includes(cov)
                                                            ? 'bg-green-600 text-white'
                                                            : 'bg-green-100 text-green-800 hover:bg-green-200'
                                                            }`}
                                                    >
                                                        {cov} {covariates.includes(cov) && '✓'}
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                    <button
                                        onClick={() => {
                                            if (suggestions.treatment) setTreatment(suggestions.treatment);
                                            if (suggestions.outcome) setOutcome(suggestions.outcome);
                                            if (suggestions.covariates.length > 0) setCovariates(suggestions.covariates);
                                        }}
                                        className="mt-3 text-xs text-green-700 hover:text-green-900 font-medium"
                                    >
                                        Apply all suggestions →
                                    </button>
                                </div>
                            )}

                            {analysisType === 'causal' && (
                                <>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Treatment (what you want to test)
                                        </label>
                                        <select
                                            value={treatment}
                                            onChange={(e) => setTreatment(e.target.value)}
                                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        >
                                            <option value="">Select treatment variable...</option>
                                            {dataPreview.columns.map(col => (
                                                <option key={col.name} value={col.name}>
                                                    {col.name} ({getTypeLabel(col.type)})
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Outcome (what you want to measure)
                                        </label>
                                        <select
                                            value={outcome}
                                            onChange={(e) => setOutcome(e.target.value)}
                                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        >
                                            <option value="">Select outcome variable...</option>
                                            {dataPreview.columns.filter(c => c.name !== treatment).map(col => (
                                                <option key={col.name} value={col.name}>
                                                    {col.name} ({getTypeLabel(col.type)})
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Covariates (potential confounders to control for)
                                        </label>
                                        <div className="flex flex-wrap gap-2">
                                            {dataPreview.columns
                                                .filter(c => c.name !== treatment && c.name !== outcome)
                                                .map(col => (
                                                    <button
                                                        key={col.name}
                                                        onClick={() => handleCovariateToggle(col.name)}
                                                        className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${covariates.includes(col.name)
                                                            ? 'bg-primary text-white border-primary'
                                                            : 'bg-white text-gray-700 border-gray-300 hover:border-primary'
                                                            }`}
                                                    >
                                                        {covariates.includes(col.name) ? '✓ ' : ''}{col.name}
                                                    </button>
                                                ))}
                                        </div>
                                        <p className="text-xs text-gray-500 mt-2">
                                            💡 Recommended: variables correlated with both treatment and outcome
                                        </p>
                                    </div>
                                </>
                            )}

                            {analysisType === 'bayesian' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Target Variable
                                    </label>
                                    <select
                                        value={outcome}
                                        onChange={(e) => setOutcome(e.target.value)}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    >
                                        <option value="">Select target variable...</option>
                                        {dataPreview.columns.map(col => (
                                            <option key={col.name} value={col.name}>
                                                {col.name} ({getTypeLabel(col.type)})
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {treatment && outcome && analysisType === 'causal' && (
                                <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
                                    <div className="text-sm text-gray-700">
                                        Your question: <span className="font-medium">"What is the causal effect of {treatment} on {outcome}?"</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 5: Question */}
                    {currentStep === 5 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-gray-900">Compose Your Question</h3>
                            <p className="text-sm text-gray-600">
                                Write your analysis question in natural language. CARF will route it to the appropriate solver.
                            </p>

                            <textarea
                                value={query || generateQuery()}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="e.g., What is the causal effect of discount on churn?"
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                                rows={4}
                            />

                            {/* AI Starter Questions */}
                            <div>
                                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                                    AI Suggested Questions
                                </h4>
                                <div className="flex flex-wrap gap-2">
                                    {(treatment && outcome) && (
                                        <button
                                            onClick={() => setQuery(`What is the causal effect of ${treatment} on ${outcome}?`)}
                                            className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full text-sm font-medium hover:bg-blue-100 transition-colors text-left border border-blue-100"
                                        >
                                            ✨ Causal Effect: {treatment} → {outcome}
                                        </button>
                                    )}
                                    {outcome && (
                                        <button
                                            onClick={() => setQuery(`What are the key drivers of ${outcome}?`)}
                                            className="px-3 py-1.5 bg-purple-50 text-purple-700 rounded-full text-sm font-medium hover:bg-purple-100 transition-colors text-left border border-purple-100"
                                        >
                                            🕵️ Key Drivers of {outcome}
                                        </button>
                                    )}
                                    {treatment && (
                                        <button
                                            onClick={() => setQuery(`How does ${treatment} vary across different groups?`)}
                                            className="px-3 py-1.5 bg-green-50 text-green-700 rounded-full text-sm font-medium hover:bg-green-100 transition-colors text-left border border-green-100"
                                        >
                                            📊 Distribution of {treatment}
                                        </button>
                                    )}
                                    <button
                                        onClick={() => setQuery(`Analyze the impact of ${treatment || 'intervention'} on ${outcome || 'outcome'} considering ${covariates.slice(0, 2).join(', ') || 'key factors'}`)}
                                        className="px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full text-sm font-medium hover:bg-indigo-100 transition-colors text-left border border-indigo-100"
                                    >
                                        🧠 Detailed Analysis (Advanced)
                                    </button>
                                </div>
                            </div>

                            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                                <div className="text-sm font-semibold text-green-900 mb-2">✅ Ready to Analyze</div>
                                <div className="text-sm text-green-700 space-y-1">
                                    <div>📊 Data: {dataPreview?.fileName} ({dataPreview?.rows} rows)</div>
                                    <div>🔬 Analysis: {analysisType === 'causal' ? 'Causal' : analysisType === 'bayesian' ? 'Bayesian' : 'Auto-detect'}</div>
                                    {treatment && <div>💊 Treatment: {treatment}</div>}
                                    {outcome && <div>🎯 Outcome: {outcome}</div>}
                                    {covariates.length > 0 && <div>🔧 Covariates: {covariates.join(', ')}</div>}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 bg-gray-50 border-t border-gray-100 flex justify-between">
                    <button
                        onClick={() => currentStep === 1 ? onClose() : setCurrentStep(s => s - 1)}
                        className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
                    >
                        {currentStep === 1 ? 'Cancel' : '← Back'}
                    </button>
                    <button
                        onClick={() => currentStep === 5 ? handleComplete() : setCurrentStep(s => s + 1)}
                        disabled={currentStep === 2 && !dataPreview}
                        className="px-6 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary-light disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {currentStep === 5 ? 'Run Analysis' : 'Next →'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DataOnboardingWizard;
