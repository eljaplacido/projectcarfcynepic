import React, { useState, useRef, useEffect } from 'react';

interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    confidence?: 'high' | 'medium' | 'low';
    linkedPanel?: string;
}

interface FloatingChatTabProps {
    messages: ChatMessage[];
    onSendMessage: (message: string) => void;
    onLinkClick?: (panelId: string) => void;
    isProcessing?: boolean;
}

const FloatingChatTab: React.FC<FloatingChatTabProps> = ({
    messages,
    onSendMessage,
    onLinkClick,
    isProcessing = false,
}) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (isExpanded && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isExpanded]);

    useEffect(() => {
        if (isExpanded && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isExpanded]);

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if (inputValue.trim() && !isProcessing) {
            onSendMessage(inputValue.trim());
            setInputValue('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const getConfidenceColor = (confidence?: string) => {
        switch (confidence) {
            case 'high': return 'bg-green-100 text-green-800';
            case 'medium': return 'bg-yellow-100 text-yellow-800';
            case 'low': return 'bg-red-100 text-red-800';
            default: return '';
        }
    };

    const handleExport = () => {
        const data = {
            exportedAt: new Date().toISOString(),
            messages: messages.map(m => ({
                ...m,
                timestamp: m.timestamp.toISOString(),
            })),
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `carf-chat-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    // Collapsed state - pill/tab
    if (!isExpanded) {
        return (
            <button
                onClick={() => setIsExpanded(true)}
                className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 bg-primary text-white rounded-full shadow-lg hover:bg-primary-light hover:shadow-xl transition-all group"
            >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="font-medium">Chat</span>
                {messages.length > 0 && (
                    <span className="w-5 h-5 bg-white text-primary text-xs font-bold rounded-full flex items-center justify-center">
                        {messages.length}
                    </span>
                )}
            </button>
        );
    }

    // Expanded state - chat panel
    return (
        <div className="fixed bottom-6 right-6 z-40 w-96 max-h-[500px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 bg-gradient-to-r from-primary to-accent text-white flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <span className="font-semibold">CARF Chat</span>
                </div>
                <div className="flex items-center gap-1">
                    <button
                        onClick={handleExport}
                        className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                        title="Export conversation"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                    </button>
                    <button
                        onClick={() => setIsExpanded(false)}
                        className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                        title="Minimize"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                        </svg>
                    </button>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-grow overflow-y-auto p-4 space-y-3">
                {messages.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                        <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <p className="text-sm">Start a conversation with CARF</p>
                        <p className="text-xs mt-1">Ask about your data or analysis</p>
                    </div>
                ) : (
                    messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[80%] rounded-2xl px-4 py-2 ${message.role === 'user'
                                        ? 'bg-primary text-white rounded-br-md'
                                        : 'bg-gray-100 text-gray-900 rounded-bl-md'
                                    }`}
                            >
                                <div className="text-sm">{message.content}</div>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className={`text-xs ${message.role === 'user' ? 'text-white/70' : 'text-gray-500'}`}>
                                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                    {message.confidence && (
                                        <span className={`text-xs px-1.5 py-0.5 rounded ${getConfidenceColor(message.confidence)}`}>
                                            {message.confidence}
                                        </span>
                                    )}
                                    {message.linkedPanel && onLinkClick && (
                                        <button
                                            onClick={() => onLinkClick(message.linkedPanel!)}
                                            className={`text-xs underline ${message.role === 'user' ? 'text-white/80' : 'text-primary'}`}
                                        >
                                            View →
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))
                )}
                {isProcessing && (
                    <div className="flex justify-start">
                        <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
                            <div className="flex items-center gap-1">
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="p-3 border-t border-gray-200 flex-shrink-0">
                <div className="flex items-end gap-2">
                    <textarea
                        ref={inputRef}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Type a follow-up question..."
                        disabled={isProcessing}
                        className="flex-grow px-3 py-2 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm disabled:bg-gray-50"
                        rows={1}
                        style={{ minHeight: '40px', maxHeight: '100px' }}
                    />
                    <button
                        type="submit"
                        disabled={!inputValue.trim() || isProcessing}
                        className="p-2 bg-primary text-white rounded-xl hover:bg-primary-light disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </div>
            </form>
        </div>
    );
};

export default FloatingChatTab;
