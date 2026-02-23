/**
 * PolicyIngestionPanel — Extract governance rules from unstructured text.
 *
 * Textarea for pasting policy text, extraction via LLM, preview and accept extracted rules.
 */

import React, { useState, useRef } from 'react';
import type { GovernanceDomain } from '../../types/carf';
import {
    extractPoliciesFromText,
    createFederatedPolicy,
    getGovernanceDomains,
    uploadGovernanceDocument,
} from '../../services/apiService';

interface ExtractedRule {
    name: string;
    condition: Record<string, unknown>;
    constraint: Record<string, unknown>;
    message: string;
    severity: string;
    confidence: number;
    rationale: string;
    evidence: string[];
    accepted: boolean;
}

interface PolicyIngestionPanelProps {
    onRulesAdded?: () => void;
}

const SEVERITY_COLORS: Record<string, string> = {
    critical: '#EF4444',
    high: '#F97316',
    medium: '#F59E0B',
    low: '#10B981',
};

const PolicyIngestionPanel: React.FC<PolicyIngestionPanelProps> = ({ onRulesAdded }) => {
    const [text, setText] = useState('');
    const [sourceName, setSourceName] = useState('');
    const [targetDomain, setTargetDomain] = useState('');
    const [domains, setDomains] = useState<GovernanceDomain[]>([]);
    const [extractedRules, setExtractedRules] = useState<ExtractedRule[]>([]);
    const [extracting, setExtracting] = useState(false);
    const [adding, setAdding] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [domainsLoaded, setDomainsLoaded] = useState(false);
    const [extractionExplainability, setExtractionExplainability] = useState<{
        whyThis?: string;
        howConfident?: number;
        basedOn?: string[];
    } | null>(null);
    const [dragOver, setDragOver] = useState(false);
    const [uploadingFile, setUploadingFile] = useState(false);
    const [uploadResult, setUploadResult] = useState<{
        status: string;
        filename: string;
        chunks?: number;
        error?: string;
    } | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const SUPPORTED_EXTENSIONS = ['pdf', 'docx', 'doc', 'csv', 'json', 'txt', 'md', 'yaml', 'yml'];

    const handleFileDrop = async (files: FileList | null) => {
        if (!files || files.length === 0) return;
        const file = files[0];
        const ext = file.name.split('.').pop()?.toLowerCase() || '';
        if (!SUPPORTED_EXTENSIONS.includes(ext)) {
            setError(`Unsupported file type: .${ext}. Supported: ${SUPPORTED_EXTENSIONS.join(', ')}`);
            return;
        }
        setUploadingFile(true);
        setError(null);
        setUploadResult(null);
        try {
            const result = await uploadGovernanceDocument(
                file,
                targetDomain || undefined,
                sourceName || file.name
            );
            setUploadResult({
                status: result.status,
                filename: result.filename,
                chunks: result.chunks_ingested,
                error: result.error,
            });
            if (result.status === 'success') {
                onRulesAdded?.();
            }
        } catch (err) {
            setError(`File upload failed: ${err}`);
        } finally {
            setUploadingFile(false);
            setDragOver(false);
        }
    };

    const loadDomains = async () => {
        if (domainsLoaded) return;
        try {
            const d = await getGovernanceDomains();
            setDomains(d);
            setDomainsLoaded(true);
        } catch {
            // Governance may not be enabled
        }
    };

    const handleExtract = async () => {
        if (!text.trim()) return;
        setExtracting(true);
        setError(null);
        setExtractedRules([]);
        setExtractionExplainability(null);
        await loadDomains();

        try {
            const result = await extractPoliciesFromText(
                text,
                sourceName || 'pasted_text',
                targetDomain || undefined
            );
            if (result.error) {
                setError(result.error);
            }
            setExtractionExplainability({
                whyThis: result.explainability?.why_this,
                howConfident: result.explainability?.how_confident ?? result.extraction_confidence_avg,
                basedOn: result.explainability?.based_on,
            });
            setExtractedRules(
                result.rules.map(r => ({
                    ...r,
                    confidence: typeof r.confidence === 'number' ? r.confidence : 0.6,
                    rationale: r.rationale || '',
                    evidence: Array.isArray(r.evidence) ? r.evidence : [],
                    accepted: true,
                }))
            );
        } catch (err) {
            setError(String(err));
        } finally {
            setExtracting(false);
        }
    };

    const toggleRule = (index: number) => {
        setExtractedRules(prev =>
            prev.map((r, i) => i === index ? { ...r, accepted: !r.accepted } : r)
        );
    };

    const handleAddSelected = async () => {
        const accepted = extractedRules.filter(r => r.accepted);
        if (accepted.length === 0) return;

        setAdding(true);
        try {
            const domain = targetDomain || 'legal';
            const policyName = sourceName || 'Extracted Policy';
            const namespace = `${domain}.extracted_${Date.now()}`;

            await createFederatedPolicy({
                name: policyName,
                domain_id: domain,
                namespace,
                description: `Rules extracted from: ${sourceName || 'pasted text'}`,
                rules: accepted.map(r => ({
                    name: r.name,
                    condition: r.condition,
                    constraint: r.constraint,
                    message: r.message,
                    severity: r.severity,
                })),
                priority: 50,
                is_active: true,
            });

            setExtractedRules([]);
            setText('');
            setExtractionExplainability(null);
            onRulesAdded?.();
        } catch (err) {
            setError(String(err));
        } finally {
            setAdding(false);
        }
    };

    const acceptedCount = extractedRules.filter(r => r.accepted).length;

    return (
        <div style={{
            padding: '16px', backgroundColor: '#1F2937', borderRadius: '8px',
            border: '1px solid #374151',
        }}>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#D1D5DB', marginBottom: '12px' }}>
                Policy Text Extraction
            </div>

            {/* File Drop Zone */}
            <div
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={e => { e.preventDefault(); handleFileDrop(e.dataTransfer.files); }}
                onClick={() => fileInputRef.current?.click()}
                style={{
                    marginBottom: '12px', padding: '16px', borderRadius: '8px',
                    border: `2px dashed ${dragOver ? '#3B82F6' : '#374151'}`,
                    backgroundColor: dragOver ? '#3B82F622' : '#111827',
                    textAlign: 'center', cursor: 'pointer',
                    transition: 'all 0.2s ease',
                }}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept={SUPPORTED_EXTENSIONS.map(e => `.${e}`).join(',')}
                    style={{ display: 'none' }}
                    onChange={e => handleFileDrop(e.target.files)}
                />
                {uploadingFile ? (
                    <div style={{ color: '#3B82F6', fontSize: '13px' }}>Uploading and processing...</div>
                ) : (
                    <>
                        <div style={{ color: '#9CA3AF', fontSize: '13px', marginBottom: '4px' }}>
                            Drag &amp; drop a document here, or click to browse
                        </div>
                        <div style={{ color: '#6B7280', fontSize: '11px' }}>
                            Supported: PDF, DOCX, CSV, JSON, TXT, MD, YAML
                        </div>
                    </>
                )}
            </div>

            {uploadResult && (
                <div style={{
                    padding: '8px 12px', marginBottom: '12px', borderRadius: '6px',
                    backgroundColor: uploadResult.status === 'success' ? '#10B98122' : '#EF444422',
                    color: uploadResult.status === 'success' ? '#10B981' : '#EF4444',
                    fontSize: '12px',
                }}>
                    {uploadResult.status === 'success'
                        ? `Ingested "${uploadResult.filename}" — ${uploadResult.chunks ?? 0} chunks indexed`
                        : `Failed: ${uploadResult.error || 'Unknown error'}`}
                </div>
            )}

            {/* Input Area */}
            <div style={{ marginBottom: '12px' }}>
                <textarea
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder="Paste policy text, regulatory guidelines, or compliance requirements here..."
                    rows={6}
                    style={{
                        width: '100%', padding: '10px', borderRadius: '6px',
                        border: '1px solid #374151', backgroundColor: '#111827',
                        color: '#E5E7EB', fontSize: '13px', resize: 'vertical',
                        fontFamily: 'inherit',
                    }}
                />
            </div>

            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>
                        Source Name
                    </label>
                    <input
                        value={sourceName}
                        onChange={e => setSourceName(e.target.value)}
                        placeholder="e.g., EU AI Act Art.9"
                        style={{
                            width: '100%', padding: '8px', borderRadius: '6px',
                            border: '1px solid #374151', backgroundColor: '#111827',
                            color: '#E5E7EB', fontSize: '12px',
                        }}
                    />
                </div>
                <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>
                        Target Domain (optional)
                    </label>
                    <select
                        value={targetDomain}
                        onChange={e => setTargetDomain(e.target.value)}
                        onFocus={loadDomains}
                        style={{
                            width: '100%', padding: '8px', borderRadius: '6px',
                            border: '1px solid #374151', backgroundColor: '#111827',
                            color: '#E5E7EB', fontSize: '12px',
                        }}
                    >
                        <option value="">Auto-detect</option>
                        {domains.map(d => (
                            <option key={d.domain_id} value={d.domain_id}>{d.display_name}</option>
                        ))}
                    </select>
                </div>
                <button
                    onClick={handleExtract}
                    disabled={extracting || !text.trim()}
                    style={{
                        padding: '8px 20px', borderRadius: '6px', border: 'none',
                        backgroundColor: '#3B82F6', color: '#fff',
                        cursor: extracting || !text.trim() ? 'not-allowed' : 'pointer',
                        fontSize: '12px', fontWeight: 600, whiteSpace: 'nowrap',
                        opacity: extracting || !text.trim() ? 0.5 : 1,
                    }}
                >
                    {extracting ? 'Extracting...' : 'Extract Rules'}
                </button>
            </div>

            {error && (
                <div style={{
                    padding: '8px 12px', marginBottom: '12px', borderRadius: '6px',
                    backgroundColor: '#EF444422', color: '#EF4444', fontSize: '12px',
                }}>
                    {error}
                </div>
            )}

            {extractionExplainability && (
                <div style={{
                    padding: '10px',
                    marginBottom: '12px',
                    borderRadius: '6px',
                    backgroundColor: '#0F172A',
                    border: '1px solid #1E293B',
                }}>
                    <div style={{ fontSize: '11px', color: '#93C5FD', fontWeight: 600, marginBottom: '4px' }}>
                        Extraction Explainability
                    </div>
                    {extractionExplainability.whyThis && (
                        <div style={{ fontSize: '11px', color: '#CBD5E1', marginBottom: '2px' }}>
                            Why this: {extractionExplainability.whyThis}
                        </div>
                    )}
                    {typeof extractionExplainability.howConfident === 'number' && (
                        <div style={{ fontSize: '11px', color: '#CBD5E1', marginBottom: '2px' }}>
                            How confident: {(extractionExplainability.howConfident * 100).toFixed(1)}%
                        </div>
                    )}
                    {extractionExplainability.basedOn && extractionExplainability.basedOn.length > 0 && (
                        <div style={{ fontSize: '11px', color: '#94A3B8' }}>
                            Based on: {extractionExplainability.basedOn.join(', ')}
                        </div>
                    )}
                </div>
            )}

            {/* Extracted Rules Preview */}
            {extractedRules.length > 0 && (
                <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#D1D5DB', marginBottom: '8px' }}>
                        Extracted Rules ({extractedRules.length})
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
                        {extractedRules.map((rule, idx) => (
                            <div key={idx} style={{
                                padding: '10px', borderRadius: '6px',
                                backgroundColor: '#111827',
                                border: `1px solid ${rule.accepted ? '#374151' : '#37415155'}`,
                                opacity: rule.accepted ? 1 : 0.5,
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <button
                                            onClick={() => toggleRule(idx)}
                                            style={{
                                                width: '18px', height: '18px', borderRadius: '4px',
                                                border: `2px solid ${rule.accepted ? '#10B981' : '#6B7280'}`,
                                                backgroundColor: rule.accepted ? '#10B981' : 'transparent',
                                                cursor: 'pointer', display: 'flex',
                                                alignItems: 'center', justifyContent: 'center',
                                                color: '#fff', fontSize: '10px',
                                            }}
                                        >
                                            {rule.accepted ? 'v' : ''}
                                        </button>
                                        <span style={{ fontWeight: 600, color: '#E5E7EB', fontSize: '12px' }}>
                                            {rule.name}
                                        </span>
                                    </div>
                                    <span style={{
                                        fontSize: '10px', padding: '2px 6px', borderRadius: '3px',
                                        backgroundColor: `${SEVERITY_COLORS[rule.severity] || '#6B7280'}22`,
                                        color: SEVERITY_COLORS[rule.severity] || '#6B7280',
                                        fontWeight: 600,
                                    }}>
                                        {rule.severity}
                                    </span>
                                </div>
                                <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '4px' }}>
                                    {rule.message}
                                </div>
                                <div style={{ fontSize: '10px', color: '#93C5FD', marginTop: '4px' }}>
                                    Confidence: {(rule.confidence * 100).toFixed(0)}%
                                </div>
                                {rule.rationale && (
                                    <div style={{ fontSize: '10px', color: '#9CA3AF', marginTop: '4px' }}>
                                        Why this: {rule.rationale}
                                    </div>
                                )}
                                {rule.evidence.length > 0 && (
                                    <div style={{ fontSize: '10px', color: '#6B7280', marginTop: '4px' }}>
                                        Based on: {rule.evidence.join(' | ')}
                                    </div>
                                )}
                                {Object.keys(rule.condition).length > 0 && (
                                    <div style={{ fontSize: '10px', color: '#6B7280', marginTop: '4px' }}>
                                        Conditions: {JSON.stringify(rule.condition)}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                            onClick={handleAddSelected}
                            disabled={adding || acceptedCount === 0}
                            style={{
                                padding: '8px 16px', borderRadius: '6px', border: 'none',
                                backgroundColor: '#10B981', color: '#fff',
                                cursor: adding || acceptedCount === 0 ? 'not-allowed' : 'pointer',
                                fontSize: '12px', fontWeight: 600,
                                opacity: adding || acceptedCount === 0 ? 0.5 : 1,
                            }}
                        >
                            {adding ? 'Adding...' : `Add ${acceptedCount} Selected`}
                        </button>
                        <button
                            onClick={() => setExtractedRules([])}
                            style={{
                                padding: '8px 16px', borderRadius: '6px',
                                border: '1px solid #374151', backgroundColor: 'transparent',
                                color: '#9CA3AF', cursor: 'pointer', fontSize: '12px',
                            }}
                        >
                            Clear
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PolicyIngestionPanel;
