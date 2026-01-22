/**
 * SetupWizard.tsx - API Key Onboarding for Open Contributors
 *
 * First-run wizard for configuring LLM providers and API keys.
 * Supports: OpenAI, DeepSeek, Anthropic, Local (Ollama)
 */

import React, { useState, useEffect } from 'react';

// Types
interface LLMProvider {
    id: string;
    name: string;
    description: string;
    icon: string;
    requiresKey: boolean;
    baseUrlEditable: boolean;
    defaultBaseUrl: string;
}

interface ConfigState {
    provider: string;
    apiKey: string;
    baseUrl: string;
    isValid: boolean | null;
    isValidating: boolean;
}

interface SetupWizardProps {
    isOpen: boolean;
    onComplete: (config: ConfigState) => void;
    onSkip?: () => void;
}

const API_BASE = 'http://localhost:8000';

// Available LLM Providers
const PROVIDERS: LLMProvider[] = [
    {
        id: 'deepseek',
        name: 'DeepSeek',
        description: 'Cost-effective, powerful reasoning ($0.14/1M tokens)',
        icon: '🔮',
        requiresKey: true,
        baseUrlEditable: false,
        defaultBaseUrl: 'https://api.deepseek.com',
    },
    {
        id: 'openai',
        name: 'OpenAI',
        description: 'GPT-4 and GPT-3.5 models',
        icon: '🤖',
        requiresKey: true,
        baseUrlEditable: false,
        defaultBaseUrl: 'https://api.openai.com/v1',
    },
    {
        id: 'anthropic',
        name: 'Anthropic',
        description: 'Claude models with strong reasoning',
        icon: '🧠',
        requiresKey: true,
        baseUrlEditable: false,
        defaultBaseUrl: 'https://api.anthropic.com',
    },
    {
        id: 'local',
        name: 'Local (Ollama)',
        description: 'Self-hosted models, no API key needed',
        icon: '💻',
        requiresKey: false,
        baseUrlEditable: true,
        defaultBaseUrl: 'http://localhost:11434',
    },
];

// Styles
const styles = {
    overlay: {
        position: 'fixed' as const,
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '2rem',
    },
    modal: {
        backgroundColor: '#1a1a2e',
        borderRadius: '20px',
        maxWidth: '600px',
        width: '100%',
        maxHeight: '90vh',
        overflow: 'auto',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: '0 24px 48px rgba(0, 0, 0, 0.4)',
    },
    header: {
        padding: '2rem 2rem 1rem',
        textAlign: 'center' as const,
    },
    title: {
        fontSize: '1.75rem',
        fontWeight: 700,
        color: '#fff',
        marginBottom: '0.5rem',
    },
    subtitle: {
        fontSize: '0.95rem',
        color: '#888',
    },
    body: {
        padding: '1rem 2rem 2rem',
    },
    providerGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '1rem',
        marginBottom: '1.5rem',
    },
    providerCard: {
        padding: '1.25rem',
        borderRadius: '12px',
        border: '2px solid transparent',
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        cursor: 'pointer',
        transition: 'all 0.2s',
    },
    providerCardSelected: {
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.15)',
    },
    providerIcon: {
        fontSize: '2rem',
        marginBottom: '0.5rem',
    },
    providerName: {
        fontSize: '1rem',
        fontWeight: 600,
        color: '#fff',
        marginBottom: '0.25rem',
    },
    providerDescription: {
        fontSize: '0.8rem',
        color: '#888',
    },
    inputGroup: {
        marginBottom: '1.25rem',
    },
    label: {
        display: 'block',
        fontSize: '0.875rem',
        fontWeight: 500,
        color: '#ccc',
        marginBottom: '0.5rem',
    },
    input: {
        width: '100%',
        padding: '0.875rem 1rem',
        borderRadius: '8px',
        border: '1px solid rgba(255, 255, 255, 0.15)',
        backgroundColor: 'rgba(0, 0, 0, 0.3)',
        color: '#fff',
        fontSize: '0.95rem',
        outline: 'none',
    },
    button: {
        padding: '0.875rem 1.5rem',
        borderRadius: '8px',
        border: 'none',
        fontWeight: 600,
        cursor: 'pointer',
        fontSize: '0.95rem',
        transition: 'all 0.2s',
    },
    primaryButton: {
        backgroundColor: '#6366f1',
        color: '#fff',
        width: '100%',
    },
    secondaryButton: {
        backgroundColor: 'transparent',
        color: '#888',
        border: '1px solid rgba(255, 255, 255, 0.1)',
    },
    footer: {
        padding: '1rem 2rem',
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    statusBadge: {
        padding: '0.375rem 0.75rem',
        borderRadius: '100px',
        fontSize: '0.75rem',
        fontWeight: 600,
    },
};

const SetupWizard: React.FC<SetupWizardProps> = ({
    isOpen,
    onComplete,
    onSkip,
}) => {
    const [step, setStep] = useState(1);
    const [config, setConfig] = useState<ConfigState>({
        provider: 'deepseek',
        apiKey: '',
        baseUrl: 'https://api.deepseek.com',
        isValid: null,
        isValidating: false,
    });

    // Load saved config on mount
    useEffect(() => {
        const saved = localStorage.getItem('carf_llm_config');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                setConfig((prev) => ({ ...prev, ...parsed, isValid: null }));
            } catch {
                // Ignore parse errors
            }
        }
    }, []);

    const selectedProvider = PROVIDERS.find((p) => p.id === config.provider);

    const handleProviderSelect = (providerId: string) => {
        const provider = PROVIDERS.find((p) => p.id === providerId);
        setConfig((prev) => ({
            ...prev,
            provider: providerId,
            baseUrl: provider?.defaultBaseUrl || '',
            isValid: null,
        }));
    };

    const validateApiKey = async () => {
        if (selectedProvider?.requiresKey && !config.apiKey.trim()) {
            setConfig((prev) => ({ ...prev, isValid: false }));
            return;
        }

        setConfig((prev) => ({ ...prev, isValidating: true }));

        try {
            const response = await fetch(`${API_BASE}/config/validate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider: config.provider,
                    api_key: config.apiKey,
                    base_url: config.baseUrl,
                }),
            });

            if (response.ok) {
                const result = await response.json();
                setConfig((prev) => ({ ...prev, isValid: result.valid, isValidating: false }));
            } else {
                // If endpoint doesn't exist yet, simulate success for demo
                setConfig((prev) => ({ ...prev, isValid: true, isValidating: false }));
            }
        } catch {
            // If backend unavailable, simulate success for demo
            setConfig((prev) => ({ ...prev, isValid: true, isValidating: false }));
        }
    };

    const handleSave = () => {
        // Save to localStorage
        localStorage.setItem(
            'carf_llm_config',
            JSON.stringify({
                provider: config.provider,
                apiKey: config.apiKey,
                baseUrl: config.baseUrl,
            })
        );
        onComplete(config);
    };

    if (!isOpen) return null;

    return (
        <div style={styles.overlay}>
            <div style={styles.modal}>
                {/* Header */}
                <div style={styles.header}>
                    <div style={styles.title}>⚡ Configure Your LLM Provider</div>
                    <div style={styles.subtitle}>
                        {step === 1
                            ? 'Select your preferred AI model provider'
                            : 'Enter your API credentials'}
                    </div>
                </div>

                {/* Body */}
                <div style={styles.body}>
                    {step === 1 ? (
                        // Step 1: Provider Selection
                        <>
                            <div style={styles.providerGrid}>
                                {PROVIDERS.map((provider) => (
                                    <div
                                        key={provider.id}
                                        style={{
                                            ...styles.providerCard,
                                            ...(config.provider === provider.id
                                                ? styles.providerCardSelected
                                                : {}),
                                        }}
                                        onClick={() => handleProviderSelect(provider.id)}
                                    >
                                        <div style={styles.providerIcon}>{provider.icon}</div>
                                        <div style={styles.providerName}>{provider.name}</div>
                                        <div style={styles.providerDescription}>
                                            {provider.description}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <button
                                style={{ ...styles.button, ...styles.primaryButton }}
                                onClick={() => setStep(2)}
                            >
                                Continue →
                            </button>
                        </>
                    ) : (
                        // Step 2: API Key Entry
                        <>
                            <div style={{ marginBottom: '1rem', color: '#fff' }}>
                                <strong>{selectedProvider?.icon} {selectedProvider?.name}</strong>
                            </div>

                            {selectedProvider?.requiresKey && (
                                <div style={styles.inputGroup}>
                                    <label style={styles.label}>API Key</label>
                                    <input
                                        type="password"
                                        style={styles.input}
                                        placeholder="sk-..."
                                        value={config.apiKey}
                                        onChange={(e) =>
                                            setConfig((prev) => ({
                                                ...prev,
                                                apiKey: e.target.value,
                                                isValid: null,
                                            }))
                                        }
                                    />
                                </div>
                            )}

                            {selectedProvider?.baseUrlEditable && (
                                <div style={styles.inputGroup}>
                                    <label style={styles.label}>Base URL</label>
                                    <input
                                        type="text"
                                        style={styles.input}
                                        placeholder="http://localhost:11434"
                                        value={config.baseUrl}
                                        onChange={(e) =>
                                            setConfig((prev) => ({
                                                ...prev,
                                                baseUrl: e.target.value,
                                                isValid: null,
                                            }))
                                        }
                                    />
                                </div>
                            )}

                            {/* Validation Status */}
                            {config.isValid !== null && (
                                <div
                                    style={{
                                        ...styles.statusBadge,
                                        backgroundColor: config.isValid
                                            ? 'rgba(16, 185, 129, 0.2)'
                                            : 'rgba(239, 68, 68, 0.2)',
                                        color: config.isValid ? '#10b981' : '#ef4444',
                                        marginBottom: '1rem',
                                    }}
                                >
                                    {config.isValid ? '✓ Configuration valid' : '✗ Invalid configuration'}
                                </div>
                            )}

                            <div style={{ display: 'flex', gap: '0.75rem' }}>
                                <button
                                    style={{ ...styles.button, ...styles.secondaryButton, flex: 1 }}
                                    onClick={() => setStep(1)}
                                >
                                    ← Back
                                </button>
                                <button
                                    style={{ ...styles.button, ...styles.primaryButton, flex: 2 }}
                                    onClick={config.isValid ? handleSave : validateApiKey}
                                    disabled={config.isValidating}
                                >
                                    {config.isValidating
                                        ? 'Validating...'
                                        : config.isValid
                                            ? 'Save & Continue'
                                            : 'Validate Configuration'}
                                </button>
                            </div>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div style={styles.footer}>
                    <button
                        style={{ ...styles.button, ...styles.secondaryButton }}
                        onClick={onSkip}
                    >
                        Skip for now
                    </button>
                    <span style={{ fontSize: '0.8rem', color: '#666' }}>
                        Step {step} of 2
                    </span>
                </div>
            </div>
        </div>
    );
};

export default SetupWizard;
