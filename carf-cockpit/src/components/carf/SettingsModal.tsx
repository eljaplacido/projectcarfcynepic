import React, { useState } from 'react';
import api from '../../services/apiService';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfigUpdated: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, onConfigUpdated }) => {
    const [provider, setProvider] = useState<string>('deepseek');
    const [apiKey, setApiKey] = useState<string>('');
    const [status, setStatus] = useState<'idle' | 'validating' | 'saving' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState<string>('');

    if (!isOpen) return null;

    const handleSave = async () => {
        setStatus('validating');
        setMessage('');

        try {
            // 1. Validate first
            const validation = await api.validateConfig(provider, apiKey);
            if (!validation.valid) {
                setStatus('error');
                setMessage(validation.message);
                return;
            }

            // 2. Save and Update
            setStatus('saving');
            await api.updateConfig(provider, apiKey);

            setStatus('success');
            setMessage('Configuration processed! switching to production mode...');

            setTimeout(() => {
                onConfigUpdated();
                onClose();
            }, 1000);

        } catch (error) {
            setStatus('error');
            setMessage(error instanceof Error ? error.message : 'Failed to update configuration');
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
                <div className="bg-gradient-to-r from-gray-50 to-white px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                    <h3 className="text-lg font-semibold text-gray-800">API Configuration</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-6 space-y-4">
                    <p className="text-sm text-gray-600">
                        Connect your own API key to enable production features. Your key is stored locally in your .env file.
                    </p>

                    <div className="space-y-3">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
                            <select
                                value={provider}
                                onChange={(e) => setProvider(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                            >
                                <option value="deepseek">DeepSeek (Recommended)</option>
                                <option value="openai">OpenAI (GPT-4)</option>
                                <option value="anthropic">Anthropic (Claude)</option>
                                <option value="local">Local (Ollama)</option>
                            </select>
                        </div>

                        {provider !== 'local' && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                                <input
                                    type="password"
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                    placeholder={`sk-${provider === 'anthropic' ? 'ant-' : ''}...`}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none font-mono"
                                />
                            </div>
                        )}
                    </div>

                    {message && (
                        <div className={`p-3 rounded-lg text-sm ${status === 'error' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
                            {message}
                        </div>
                    )}

                    <div className="flex gap-3 pt-2">
                        <button
                            onClick={onClose}
                            className="flex-1 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-medium transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={status === 'validating' || status === 'saving' || (provider !== 'local' && !apiKey)}
                            className="flex-1 px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {status === 'validating' ? 'Validating...' : status === 'saving' ? 'Saving...' : 'Connect API'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SettingsModal;
