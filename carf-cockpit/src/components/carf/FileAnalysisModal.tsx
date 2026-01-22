/**
 * File Analysis Modal
 *
 * Modal for uploading and analyzing files with the /analyze endpoint.
 * Supports drag & drop, file type detection, and preview before analysis.
 */

import React, { useState, useCallback, useRef } from 'react';
import { useFileAnalysis } from '../../hooks/useCarfApi';
import type { FileAnalysisResult } from '../../services/apiService';

interface FileAnalysisModalProps {
    isOpen: boolean;
    onClose: () => void;
    onAnalysisComplete: (result: FileAnalysisResult) => void;
    onRunQuery?: (query: string, context: Record<string, unknown>) => void;
}

const FileAnalysisModal: React.FC<FileAnalysisModalProps> = ({
    isOpen,
    onClose,
    onAnalysisComplete,
    onRunQuery,
}) => {
    const [dragActive, setDragActive] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [textContent, setTextContent] = useState('');
    const [mode, setMode] = useState<'file' | 'text'>('file');
    const [query, setQuery] = useState('');

    // Variable selection state
    const [selectedTreatment, setSelectedTreatment] = useState<string>('');
    const [selectedOutcome, setSelectedOutcome] = useState<string>('');
    const [selectedCovariates, setSelectedCovariates] = useState<string[]>([]);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const { result, loading, error, uploadProgress, analyzeFile, analyzeText, reset } = useFileAnalysis();

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setSelectedFile(e.dataTransfer.files[0]);
        }
    }, []);

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setSelectedFile(e.target.files[0]);
        }
    }, []);

    const handleAnalyze = useCallback(async () => {
        let analysisResult: FileAnalysisResult | null = null;

        if (mode === 'file' && selectedFile) {
            analysisResult = await analyzeFile(selectedFile);
        } else if (mode === 'text' && textContent.trim()) {
            analysisResult = await analyzeText(textContent, query);
        }

        if (analysisResult) {
            // Auto-select suggested variables
            if (analysisResult.suggested_treatment) {
                setSelectedTreatment(analysisResult.suggested_treatment);
            }
            if (analysisResult.suggested_outcome) {
                setSelectedOutcome(analysisResult.suggested_outcome);
            }
            if (analysisResult.suggested_covariates) {
                setSelectedCovariates(analysisResult.suggested_covariates);
            }
        }
    }, [mode, selectedFile, textContent, query, analyzeFile, analyzeText]);

    const handleRunAnalysis = useCallback(() => {
        if (!result || !selectedTreatment || !selectedOutcome) return;

        const context = {
            file_analysis: result,
            causal_estimation: {
                treatment: selectedTreatment,
                outcome: selectedOutcome,
                covariates: selectedCovariates,
            },
        };

        onAnalysisComplete(result);

        if (onRunQuery) {
            const defaultQuery = `What is the causal effect of ${selectedTreatment} on ${selectedOutcome}?`;
            onRunQuery(query || defaultQuery, context);
        }

        handleClose();
    }, [result, selectedTreatment, selectedOutcome, selectedCovariates, query, onAnalysisComplete, onRunQuery]);

    const handleClose = useCallback(() => {
        setSelectedFile(null);
        setTextContent('');
        setQuery('');
        setSelectedTreatment('');
        setSelectedOutcome('');
        setSelectedCovariates([]);
        reset();
        onClose();
    }, [reset, onClose]);

    const toggleCovariate = useCallback((column: string) => {
        setSelectedCovariates(prev =>
            prev.includes(column)
                ? prev.filter(c => c !== column)
                : [...prev, column]
        );
    }, []);

    if (!isOpen) return null;

    const getFileIcon = (type: string) => {
        if (type.includes('csv') || type.includes('excel') || type.includes('spreadsheet')) {
            return (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                </svg>
            );
        }
        if (type.includes('json')) {
            return (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
            );
        }
        if (type.includes('pdf')) {
            return (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
            );
        }
        return (
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
        );
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-primary/5 to-accent/5">
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900">Analyze Data</h2>
                        <p className="text-sm text-gray-500">Upload a file or paste content for causal analysis</p>
                    </div>
                    <button
                        onClick={handleClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="flex-grow overflow-y-auto p-6">
                    {/* Mode Toggle */}
                    <div className="flex gap-2 mb-6">
                        <button
                            onClick={() => setMode('file')}
                            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all ${mode === 'file'
                                ? 'bg-primary text-white'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                        >
                            Upload File
                        </button>
                        <button
                            onClick={() => setMode('text')}
                            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all ${mode === 'text'
                                ? 'bg-primary text-white'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                        >
                            Paste Content
                        </button>
                    </div>

                    {/* File Upload */}
                    {mode === 'file' && !result && (
                        <div
                            className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all ${dragActive
                                ? 'border-primary bg-primary/5'
                                : 'border-gray-300 hover:border-gray-400'
                                }`}
                            onDragEnter={handleDrag}
                            onDragLeave={handleDrag}
                            onDragOver={handleDrag}
                            onDrop={handleDrop}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                onChange={handleFileSelect}
                                accept=".csv,.json,.pdf,.txt,.md,.xlsx,.xls"
                                className="hidden"
                            />

                            {selectedFile ? (
                                <div className="flex flex-col items-center">
                                    <div className="text-primary mb-3">
                                        {getFileIcon(selectedFile.type || selectedFile.name)}
                                    </div>
                                    <p className="font-medium text-gray-900">{selectedFile.name}</p>
                                    <p className="text-sm text-gray-500">
                                        {(selectedFile.size / 1024).toFixed(1)} KB
                                    </p>
                                    <button
                                        onClick={() => setSelectedFile(null)}
                                        className="mt-3 text-sm text-red-600 hover:text-red-700"
                                    >
                                        Remove
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <svg className="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                    </svg>
                                    <p className="text-gray-600 mb-2">
                                        <button
                                            onClick={() => fileInputRef.current?.click()}
                                            className="text-primary font-medium hover:underline"
                                        >
                                            Click to upload
                                        </button>
                                        {' '}or drag and drop
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        CSV, JSON, PDF, TXT, MD, Excel (max 10MB)
                                    </p>
                                </>
                            )}
                        </div>
                    )}

                    {/* Text Input */}
                    {mode === 'text' && !result && (
                        <div>
                            <textarea
                                value={textContent}
                                onChange={(e) => setTextContent(e.target.value)}
                                placeholder="Paste your data here (CSV format, JSON, or plain text)..."
                                className="w-full h-48 px-4 py-3 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent font-mono text-sm"
                            />
                            <p className="text-xs text-gray-500 mt-2">
                                Tip: For tabular data, paste CSV format with headers in the first row
                            </p>
                        </div>
                    )}

                    {/* Loading State */}
                    {loading && (
                        <div className="mt-6 p-6 bg-gray-50 rounded-xl">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                                <span className="text-gray-700">Analyzing content...</span>
                            </div>
                            {uploadProgress > 0 && (
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                    <div
                                        className="bg-primary h-2 rounded-full transition-all duration-300"
                                        style={{ width: `${uploadProgress}%` }}
                                    />
                                </div>
                            )}
                        </div>
                    )}

                    {/* Error State */}
                    {error && (
                        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl">
                            <div className="flex items-center gap-2 text-red-700">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <span className="font-medium">Analysis failed</span>
                            </div>
                            <p className="text-sm text-red-600 mt-1">{error.message}</p>
                        </div>
                    )}

                    {/* Analysis Results */}
                    {result && !loading && (
                        <div className="mt-6 space-y-6">
                            {/* File Info */}
                            <div className="p-4 bg-green-50 border border-green-200 rounded-xl">
                                <div className="flex items-center gap-2 text-green-700 mb-2">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                    <span className="font-medium">File analyzed successfully</span>
                                </div>
                                <div className="grid grid-cols-3 gap-4 text-sm">
                                    <div>
                                        <span className="text-gray-500">Rows:</span>
                                        <span className="ml-2 font-medium">{result.row_count ?? 'N/A'}</span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Columns:</span>
                                        <span className="ml-2 font-medium">{result.column_count ?? 'N/A'}</span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Size:</span>
                                        <span className="ml-2 font-medium">{(result.file_size / 1024).toFixed(1)} KB</span>
                                    </div>
                                </div>
                            </div>

                            {/* Variable Selection */}
                            {result.columns && result.columns.length > 0 && (
                                <div className="space-y-4">
                                    <h3 className="font-semibold text-gray-900">Configure Variables</h3>

                                    {/* Treatment Variable */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Treatment Variable (what you can change)
                                            {result.suggested_treatment && (
                                                <span className="ml-2 text-xs text-green-600">
                                                    Suggested: {result.suggested_treatment}
                                                </span>
                                            )}
                                        </label>
                                        <select
                                            value={selectedTreatment}
                                            onChange={(e) => setSelectedTreatment(e.target.value)}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        >
                                            <option value="">Select treatment...</option>
                                            {result.columns.map((col) => (
                                                <option key={col} value={col}>{col}</option>
                                            ))}
                                        </select>
                                    </div>

                                    {/* Outcome Variable */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Outcome Variable (what you want to affect)
                                            {result.suggested_outcome && (
                                                <span className="ml-2 text-xs text-green-600">
                                                    Suggested: {result.suggested_outcome}
                                                </span>
                                            )}
                                        </label>
                                        <select
                                            value={selectedOutcome}
                                            onChange={(e) => setSelectedOutcome(e.target.value)}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        >
                                            <option value="">Select outcome...</option>
                                            {result.columns
                                                .filter(col => col !== selectedTreatment)
                                                .map((col) => (
                                                    <option key={col} value={col}>{col}</option>
                                                ))}
                                        </select>
                                    </div>

                                    {/* Covariates */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Covariates (control variables)
                                        </label>
                                        <div className="flex flex-wrap gap-2">
                                            {result.columns
                                                .filter(col => col !== selectedTreatment && col !== selectedOutcome)
                                                .map((col) => (
                                                    <button
                                                        key={col}
                                                        onClick={() => toggleCovariate(col)}
                                                        className={`px-3 py-1 text-sm rounded-full transition-all ${selectedCovariates.includes(col)
                                                            ? 'bg-primary text-white'
                                                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                                            }`}
                                                    >
                                                        {col}
                                                    </button>
                                                ))}
                                        </div>
                                    </div>

                                    {/* Query Input */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Analysis Query (optional)
                                        </label>
                                        <input
                                            type="text"
                                            value={query}
                                            onChange={(e) => setQuery(e.target.value)}
                                            placeholder={`e.g., What is the effect of ${selectedTreatment || 'treatment'} on ${selectedOutcome || 'outcome'}?`}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Data Preview */}
                            {result.data_preview && result.data_preview.length > 0 && (
                                <div>
                                    <h3 className="font-semibold text-gray-900 mb-3">Data Preview</h3>
                                    <div className="overflow-x-auto border border-gray-200 rounded-lg">
                                        <table className="min-w-full divide-y divide-gray-200">
                                            <thead className="bg-gray-50">
                                                <tr>
                                                    {result.columns?.map((col) => (
                                                        <th
                                                            key={col}
                                                            className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                                                        >
                                                            {col}
                                                        </th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white divide-y divide-gray-200">
                                                {result.data_preview.slice(0, 5).map((row, i) => (
                                                    <tr key={i}>
                                                        {result.columns?.map((col) => (
                                                            <td
                                                                key={col}
                                                                className="px-4 py-2 text-sm text-gray-900 whitespace-nowrap"
                                                            >
                                                                {String(row[col] ?? '')}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {/* Text Content Preview */}
                            {result.text_content && !result.data_preview && (
                                <div>
                                    <h3 className="font-semibold text-gray-900 mb-3">Content Preview</h3>
                                    <div className="p-4 bg-gray-50 rounded-lg max-h-48 overflow-y-auto">
                                        <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
                                            {result.text_content.slice(0, 1000)}
                                            {result.text_content.length > 1000 && '...'}
                                        </pre>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between bg-gray-50">
                    <button
                        onClick={handleClose}
                        className="px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
                    >
                        Cancel
                    </button>

                    <div className="flex gap-3">
                        {!result && (
                            <button
                                onClick={handleAnalyze}
                                disabled={loading || (mode === 'file' && !selectedFile) || (mode === 'text' && !textContent.trim())}
                                className="px-6 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                            >
                                {loading ? 'Analyzing...' : 'Analyze'}
                            </button>
                        )}

                        {result && result.analysis_ready && (
                            <button
                                onClick={handleRunAnalysis}
                                disabled={!selectedTreatment || !selectedOutcome}
                                className="px-6 py-2 bg-gradient-to-r from-primary to-accent text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                            >
                                Run Causal Analysis
                            </button>
                        )}

                        {result && !result.analysis_ready && (
                            <button
                                onClick={() => {
                                    onAnalysisComplete(result);
                                    handleClose();
                                }}
                                className="px-6 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-all"
                            >
                                Use in Chat
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FileAnalysisModal;
